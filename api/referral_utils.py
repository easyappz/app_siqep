from __future__ import annotations

import random
from collections import defaultdict
from decimal import Decimal
from typing import Iterable, List, Tuple

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Member,
    ReferralRelation,
    RankRule,
    MAX_REFERRAL_DEPTH,
    PLAYER_DIRECT_REFERRAL_BONUS_VCOINS,
    PLAYER_DEPTH_BASE_BONUS_VCOINS,
    INFLUENCER_DIRECT_REFERRAL_BONUS_CASH,
    INFLUENCER_DEPTH_BASE_BONUS_CASH,
    INFLUENCER_DEPOSIT_PERCENT,
    USER_TYPE_PLAYER,
    USER_TYPE_INFLUENCER,
    ReferralEvent,
    ReferralReward,
    WalletTransaction,
)

RewardType = ReferralReward.RewardType

BUSINESS_INFLUENCER_DEFINITIONS = [
    {"first_name": "Инфлюенсер", "last_name": "Альфа", "phone": "+79996110001"},
    {"first_name": "Инфлюенсер", "last_name": "Браво", "phone": "+79996110002"},
    {"first_name": "Инфлюенсер", "last_name": "Чарли", "phone": "+79996110003"},
]
BUSINESS_PLAYER_TEMPLATE = "+79997000{index:03d}"
BUSINESS_PLAYER_TOTAL = 100
BUSINESS_SCENARIO_TAG = "business_model_v1"
BUSINESS_INFLUENCER_PASSWORD = "influencerSim123"
BUSINESS_PLAYER_PASSWORD = "playerSim123"


def get_rank_multiplier(rank: str, user_type: str) -> Decimal:
    """Return depth bonus multiplier for the given rank and user_type.

    If the rule or concrete multiplier is missing, 1.00 is returned.
    """

    default_multiplier = Decimal("1.00")

    if not rank:
        return default_multiplier

    try:
        rule = RankRule.objects.get(pk=rank)
    except RankRule.DoesNotExist:
        return default_multiplier

    if user_type == USER_TYPE_PLAYER:
        value = rule.player_depth_bonus_multiplier
    elif user_type == USER_TYPE_INFLUENCER:
        value = rule.influencer_depth_bonus_multiplier
    else:
        return default_multiplier

    if value is None:
        return default_multiplier

    return Decimal(value)


# ... existing functions remain unchanged ...


def simulate_demo_deposits_for_amir_alfira(amount: int | Decimal = 2000) -> dict:
    """Simulate demo deposits for players 'Амир' and 'Альфира' linked to Timur.

    This helper:
    - Locates Timur by canonical phone number (89031221111).
    - Locates or creates Members for Амир and Альфира with fixed test phones.
    - Ensures they are linked to Timur as direct referrals (referrer/referred_by).
    - For each player, creates (or reuses) a ReferralEvent deposit for the
      specified amount using the standard `process_member_deposit` flow.
    - Returns a structured summary including Timur's cash balance before and
      after the operation and the delta.

    Idempotency notes:
    - If a ReferralEvent already exists for (Timur -> player, deposit_amount == amount),
      it is reused and no additional deposit is created. This makes the helper
      safe to call multiple times in a test environment without artificially
      увеличивать доход Тимура.
    """

    # Normalize amount to Decimal and validate
    if not isinstance(amount, Decimal):
        amount_decimal = Decimal(str(amount))
    else:
        amount_decimal = amount

    if amount_decimal <= 0:
        raise ValueError("Сумма депозита должна быть положительным числом.")

    # Locate Timur by canonical phone, consistent with migration 0005.
    timur = Member.objects.filter(phone="89031221111").first()
    if timur is None:
        raise ValueError(
            "Не удалось найти пользователя Тимур с телефоном 89031221111. "
            "Создайте такого пользователя перед запуском тестовой симуляции."
        )

    timur_cash_before = timur.cash_balance or Decimal("0.00")

    players_def = [
        {
            "first_name": "Амир",
            "last_name": "Тестов",
            "phone": "+79990000001",
        },
        {
            "first_name": "Альфира",
            "last_name": "Тестова",
            "phone": "+79990000002",
        },
    ]

    players_summary: list[dict] = []

    for item in players_def:
        phone = item["phone"]
        member = Member.objects.filter(phone=phone).first()

        if member is None:
            member = Member(
                first_name=item["first_name"],
                last_name=item["last_name"],
                phone=phone,
                email=None,
                is_influencer=False,
                is_admin=False,
                user_type=USER_TYPE_PLAYER,
                referrer=timur,
                referred_by=timur,
            )
            member.set_password("test1234")
            member.save()
            on_new_user_registered(member)
        else:
            update_fields: list[str] = []
            if member.referrer_id != timur.id:
                member.referrer = timur
                update_fields.append("referrer")
            if member.referred_by_id != timur.id:
                member.referred_by = timur
                update_fields.append("referred_by")
            if member.user_type != USER_TYPE_PLAYER:
                member.user_type = USER_TYPE_PLAYER
                update_fields.append("user_type")

            if update_fields:
                member.save(update_fields=update_fields)
                on_new_user_registered(member)

        existing_event = (
            ReferralEvent.objects.filter(
                referrer=timur,
                referred=member,
                deposit_amount=int(amount_decimal),
            )
            .order_by("created_at")
            .first()
        )

        if existing_event is None:
            event = process_member_deposit(member, amount_decimal)
        else:
            event = existing_event

        deposits_summary: list[dict] = []
        if event is not None:
            deposits_summary.append(
                {
                    "id": event.id,
                    "amount": event.deposit_amount,
                    "created_at": event.created_at,
                }
            )

        players_summary.append(
            {
                "member_id": member.id,
                "name": f"{member.first_name} {member.last_name}".strip(),
                "phone": member.phone,
                "deposits": deposits_summary,
            }
        )

    timur.refresh_from_db()
    timur_cash_after = timur.cash_balance or Decimal("0.00")
    earnings_delta = (timur_cash_after - timur_cash_before).quantize(
        Decimal("0.01")
    )

    return {
        "players": players_summary,
        "timur": {
            "member_id": timur.id,
            "name": f"{timur.first_name} {timур.last_name}".strip(),
            "phone": timур.phone,
            "cash_balance_before": timур_cash_before,
            "cash_balance_after": timур_cash_after,
            "earnings_delta": earnings_delta,
        },
    }


def _ensure_simulation_influencer(definition: dict) -> tuple[Member, bool]:
    member = Member.objects.filter(phone=definition["phone"]).first()
    created = False
    if member is None:
        member = Member(
            first_name=definition["first_name"],
            last_name=definition["last_name"],
            phone=definition["phone"],
            email=None,
            is_influencer=True,
            is_admin=False,
            user_type=USER_TYPE_INFLUENCER,
        )
        member.set_password(BUSINESS_INFLUENCER_PASSWORD)
        member.save()
        created = True
    updates: list[str] = []
    if not member.is_influencer:
        member.is_influencer = True
        updates.append("is_influencer")
    if member.user_type != USER_TYPE_INFLUENCER:
        member.user_type = USER_TYPE_INFLUENCER
        updates.append("user_type")
    if updates:
        member.save(update_fields=updates)
    return member, created


def _build_simulation_player_definition(index: int) -> dict:
    return {
        "first_name": f"Игрок {index + 1}",
        "last_name": "Симуляция",
        "phone": BUSINESS_PLAYER_TEMPLATE.format(index=index),
    }


def _ensure_simulation_player(definition: dict, influencer: Member) -> tuple[Member, bool, bool]:
    member = Member.objects.filter(phone=definition["phone"]).first()
    created = False
    referrer_changed = False
    if member is None:
        member = Member(
            first_name=definition["first_name"],
            last_name=definition["last_name"],
            phone=definition["phone"],
            email=None,
            is_influencer=False,
            is_admin=False,
            user_type=USER_TYPE_PLAYER,
            referrer=influencer,
            referred_by=influencer,
        )
        member.set_password(BUSINESS_PLAYER_PASSWORD)
        member.save()
        created = True
    updates: list[str] = []
    if member.is_influencer:
        member.is_influencer = False
        updates.append("is_influencer")
    if member.user_type != USER_TYPE_PLAYER:
        member.user_type = USER_TYPE_PLAYER
        updates.append("user_type")
    if member.referrer_id != influencer.id:
        member.referrer = influencer
        updates.append("referrer")
        referrer_changed = True
    if member.referred_by_id != influencer.id:
        member.referred_by = influencer
        updates.append("referred_by")
        referrer_changed = True
    if updates:
        member.save(update_fields=updates)
    if created or referrer_changed:
        ReferralRelation.objects.filter(descendant=member).delete()
        on_new_user_registered(member)
    return member, created, referrer_changed


def _generate_simulation_deposit_amount(rng: random.Random) -> Decimal:
    whole = rng.randint(1500, 6000)
    cents = rng.randint(0, 99)
    amount = Decimal(whole) + (Decimal(cents) / Decimal(100))
    return amount.quantize(Decimal("0.01"))


def _generate_simulation_spend_amount(rng: random.Random, deposit_amount: Decimal) -> Decimal:
    if deposit_amount <= Decimal("0.00"):
        return Decimal("0.00")
    percent = rng.randint(35, 90)
    amount = (deposit_amount * Decimal(percent) / Decimal(100)).quantize(
        Decimal("0.01")
    )
    if amount <= Decimal("0.00"):
        amount = Decimal("0.01")
    if amount > deposit_amount:
        return deposit_amount
    return amount


def _ensure_referral_deposit(player: Member, deposit_amount: Decimal) -> bool:
    referrer = player.referrer or player.referred_by
    if referrer is None:
        return False
    existing_event = (
        ReferralEvent.objects.filter(referrer=referrer, referred=player)
        .order_by("created_at")
        .first()
    )
    if existing_event is not None:
        return False
    event = process_member_deposit(player, deposit_amount)
    return event is not None


def _scenario_wallet_transaction_exists(member: Member, scenario: str, tx_type: str) -> bool:
    return WalletTransaction.objects.filter(
        member=member,
        meta__scenario=scenario,
        meta__type=tx_type,
    ).exists()


def _ensure_wallet_deposit(player: Member, amount: Decimal, scenario: str, index: int) -> bool:
    if amount <= Decimal("0.00"):
        return False
    if _scenario_wallet_transaction_exists(player, scenario, "deposit"):
        return False
    player.deposit(
        amount,
        description="Симуляция бизнес-модели: пополнение",
        meta={
            "scenario": scenario,
            "type": "deposit",
            "player_index": index,
            "amount": str(amount),
        },
    )
    return True


def _ensure_wallet_spend(player: Member, amount: Decimal, scenario: str, index: int) -> bool:
    if amount <= Decimal("0.00"):
        return False
    if _scenario_wallet_transaction_exists(player, scenario, "spend"):
        return False
    try:
        player.spend(
            amount,
            description="Симуляция бизнес-модели: трата",
            meta={
                "scenario": scenario,
                "type": "spend",
                "player_index": index,
                "amount": str(amount),
            },
        )
    except ValueError:
        return False
    return True


def _get_wallet_amount(member: Member, scenario: str, tx_type: str) -> Decimal:
    tx = (
        WalletTransaction.objects.filter(
            member=member,
            meta__scenario=scenario,
            meta__type=tx_type,
        )
        .order_by("id")
        .first()
    )
    if tx is None:
        return Decimal("0.00")
    return tx.amount or Decimal("0.00")


def simulate_business_model(seed: int = 2024) -> dict:
    """Simulate three influencers bringing one hundred players with deposits and spends."""

    rng = random.Random(seed)
    scenario_tag = BUSINESS_SCENARIO_TAG
    with transaction.atomic():
        influencers: list[Member] = []
        created_influencers = 0
        for definition in BUSINESS_INFLUENCER_DEFINITIONS:
            influencer, was_created = _ensure_simulation_influencer(definition)
            influencers.append(influencer)
            if was_created:
                created_influencers += 1
        players: list[Member] = []
        player_assignments: list[tuple[Member, Member, int]] = []
        created_players = 0
        for index in range(BUSINESS_PLAYER_TOTAL):
            definition = _build_simulation_player_definition(index)
            influencer = influencers[index % len(influencers)]
            player, was_created, _ = _ensure_simulation_player(definition, influencer)
            players.append(player)
            player_assignments.append((player, influencer, index))
            if was_created:
                created_players += 1
        new_events = 0
        new_deposits = 0
        new_spends = 0
        for player, _influencer, idx in player_assignments:
            deposit_amount = _generate_simulation_deposit_amount(rng)
            spend_amount = _generate_simulation_spend_amount(rng, deposit_amount)
            if _ensure_referral_deposit(player, deposit_amount):
                new_events += 1
            if _ensure_wallet_deposit(player, deposit_amount, scenario_tag, idx):
                new_deposits += 1
            if _ensure_wallet_spend(player, spend_amount, scenario_tag, idx):
                new_spends += 1
            player.refresh_from_db()
        for influencer in influencers:
            influencer.refresh_from_db()
        players_data: list[dict] = []
        players_by_influencer: defaultdict[int, list[dict]] = defaultdict(list)
        total_deposit_volume = Decimal("0.00")
        total_spend_volume = Decimal("0.00")
        total_referral_rewards = Decimal("0.00")
        total_active_referrals = 0
        for player, influencer, _idx in player_assignments:
            deposit_value = _get_wallet_amount(player, scenario_tag, "deposit")
            spend_value = _get_wallet_amount(player, scenario_tag, "spend")
            entry = {
                "member_id": player.id,
                "phone": player.phone,
                "influencer_id": influencer.id,
                "deposit_amount": deposit_value,
                "spend_amount": spend_value,
                "wallet_balance": player.wallet_balance,
            }
            players_data.append(entry)
            players_by_influencer[influencer.id].append(entry)
            total_deposit_volume += deposit_value
            total_spend_volume += spend_value
        influencers_data: list[dict] = []
        for influencer in influencers:
            assigned_players = players_by_influencer[influencer.id]
            player_ids = [p["member_id"] for p in assigned_players]
            deposit_sum = sum((p["deposit_amount"] for p in assigned_players), Decimal("0.00"))
            spend_sum = sum((p["spend_amount"] for p in assigned_players), Decimal("0.00"))
            rewards_sum = (
                ReferralReward.objects.filter(
                    member=influencer,
                    source_member_id__in=player_ids,
                ).aggregate(total=Sum("amount_rub"))["total"]
                or Decimal("0.00")
            )
            active_referrals = ReferralRelation.objects.filter(
                ancestor=influencer,
                descendant_id__in=player_ids,
                has_paid_first_bonus=True,
            ).count()
            total_referral_rewards += rewards_sum
            total_active_referrals += active_referrals
            influencers_data.append(
                {
                    "member_id": influencer.id,
                    "name": f"{influencer.first_name} {influencer.last_name}".strip(),
                    "phone": influencer.phone,
                    "players_count": len(assigned_players),
                    "active_players": active_referrals,
                    "total_deposit_volume": deposit_sum,
                    "total_spend_volume": spend_sum,
                    "referral_reward_volume": rewards_sum,
                    "wallet_balance": influencer.wallet_balance,
                }
            )
        global_metrics = {
            "total_influencers": len(influencers),
            "total_players": len(players_data),
            "total_deposit_volume": total_deposit_volume,
            "total_spend_volume": total_spend_volume,
            "total_referral_rewards": total_referral_rewards,
            "total_active_referrals": total_active_referrals,
        }
        counters = {
            "new_influencers": created_influencers,
            "new_players": created_players,
            "new_referral_events": new_events,
            "new_wallet_deposits": new_deposits,
            "new_wallet_spends": new_spends,
        }
    return {
        "scenario_tag": scenario_tag,
        "influencers": influencers_data,
        "players": players_data,
        "global_metrics": global_metrics,
        "counters": counters,
    }
