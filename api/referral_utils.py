from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List, Tuple

from django.db import transaction
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
    ReferralBonus,
)

RewardType = ReferralReward.RewardType


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


def check_for_rank_up(member: Member) -> None:
    """Recalculate and update member.rank based on active level-1 referrals.

    Active referrals are defined as level-1 ReferralRelation rows for which
    has_paid_first_bonus == True. This corresponds to referrals that have
    completed their first paid tournament / qualifying deposit.
    """

    if member.pk is None:
        return

    active_count = (
        ReferralRelation.objects.filter(
            ancestor=member,
            level=1,
            has_paid_first_bonus=True,
        )
        .values("descendant_id")
        .distinct()
        .count()
    )

    rules: List[RankRule] = list(RankRule.objects.all().order_by("required_referrals"))
    if not rules:
        return

    target_rank = member.rank
    for rule in rules:
        if active_count >= rule.required_referrals:
            target_rank = rule.rank

    if target_rank and target_rank != member.rank:
        member.rank = target_rank
        member.save(update_fields=["rank"])


def on_new_user_registered(new_member: Member) -> None:
    """Create ReferralRelation entries for a newly registered member.

    This should be called once, right after a Member is created and its
    direct referrer is set in `new_member.referrer`.

    The function walks up the referrer chain and creates one
    ReferralRelation per ancestor with a level starting from 1.

    Note: we intentionally DO NOT recalculate ranks here. Ranks depend on
    *active* referrals, which are those that have completed their first
    paid tournament / qualifying deposit. Rank recalculation is triggered
    in `on_user_first_tournament_completed` after the first-bonus flags
    are set.
    """

    if new_member.pk is None:
        return

    direct_referrer = new_member.referrer
    if direct_referrer is None:
        return

    current_ancestor: Member | None = direct_referrer
    level = 1
    visited_ids = set()

    while current_ancestor is not None and level <= MAX_REFERRAL_DEPTH:
        if current_ancestor.pk is None:
            break
        if current_ancestor.pk in visited_ids:
            # Basic cycle protection
            break

        visited_ids.add(current_ancestor.pk)

        # Use get_or_create to avoid duplicating relations if this function
        # is accidentally called more than once for the same member.
        ReferralRelation.objects.get_or_create(
            ancestor=current_ancestor,
            descendant=new_member,
            defaults={
                "level": level,
                "has_paid_first_bonus": False,
            },
        )

        current_ancestor = current_ancestor.referrer
        level += 1


def on_user_first_tournament_completed(member: Member) -> None:
    """Handle the first paid tournament / first qualifying deposit of a member.

    For each ancestor recorded in ReferralRelation with has_paid_first_bonus=False,
    this function:
    - Calculates the appropriate bonus (direct or deep) in the correct currency
      (V-Coins for players, ₽ for influencers), taking rank multipliers into
      account for deep levels.
    - Updates the ancestor's v_coins_balance or cash_balance.
    - Creates a ReferralReward entry describing the payout.
    - Updates aggregated counters on Member (total_bonus_points / total_money_earned).
    - Marks has_paid_first_bonus=True for that ancestor/descendant pair.

    After processing, rank recalculation is triggered for all direct referrers
    (level == 1), because they have just gained one additional *active* referral.
    """

    if member.pk is None:
        return

    with transaction.atomic():
        relations = (
            ReferralRelation.objects.select_for_update()
            .select_related("ancestor")
            .filter(descendant=member, has_paid_first_bonus=False)
            .order_by("level")
        )

        if not relations:
            return

        direct_ancestor_ids: set[int] = set()

        for relation in relations:
            ancestor = relation.ancestor
            if ancestor is None or ancestor.pk is None:
                continue

            is_influencer = ancestor.user_type == USER_TYPE_INFLUENCER
            level = relation.level

            bonus_amount: Decimal
            update_fields: list[str] = []
            stack_count_for_member = 0
            money_increment_int = 0

            if level == 1:
                # Direct referrer bonus
                if is_influencer:
                    bonus_amount = INFLUENCER_DIRECT_REFERRAL_BONUS_CASH
                    ancestor.cash_balance = (
                        ancestor.cash_balance or Decimal("0.00")
                    ) + bonus_amount
                    update_fields.append("cash_balance")

                    ReferralReward.objects.create(
                        member=ancestor,
                        source_member=member,
                        reward_type=RewardType.INFLUENCER_FIRST_TOURNAMENT,
                        amount_rub=bonus_amount,
                        stack_count=0,
                        depth=level,
                    )

                    money_increment_int = int(bonus_amount)
                else:
                    bonus_amount = PLAYER_DIRECT_REFERRAL_BONUS_VCOINS
                    ancestor.v_coins_balance = (
                        ancestor.v_coins_balance or Decimal("0.00")
                    ) + bonus_amount
                    update_fields.append("v_coins_balance")

                    stack_count_for_member = 1
                    ReferralReward.objects.create(
                        member=ancestor,
                        source_member=member,
                        reward_type=RewardType.PLAYER_STACK,
                        amount_rub=Decimal("0.00"),
                        stack_count=stack_count_for_member,
                        depth=level,
                    )

                direct_ancestor_ids.add(ancestor.pk)
            else:
                # Deep cashback (levels 2..MAX_REFERRAL_DEPTH)
                if is_influencer:
                    base_bonus = INFLUENCER_DEPTH_BASE_BONUS_CASH
                    multiplier = get_rank_multiplier(
                        ancestor.rank,
                        USER_TYPE_INFLUENCER,
                    )
                    bonus_amount = (base_bonus * multiplier).quantize(
                        Decimal("0.01")
                    )
                    ancestor.cash_balance = (
                        ancestor.cash_balance or Decimal("0.00")
                    ) + bonus_amount
                    update_fields.append("cash_balance")

                    ReferralReward.objects.create(
                        member=ancestor,
                        source_member=member,
                        reward_type=RewardType.INFLUENCER_FIRST_TOURNAMENT,
                        amount_rub=bonus_amount,
                        stack_count=0,
                        depth=level,
                    )

                    money_increment_int = int(bonus_amount)
                else:
                    base_bonus = PLAYER_DEPTH_BASE_BONUS_VCOINS
                    multiplier = get_rank_multiplier(
                        ancestor.rank,
                        USER_TYPE_PLAYER,
                    )
                    bonus_amount = (base_bonus * multiplier).quantize(
                        Decimal("0.01")
                    )
                    ancestor.v_coins_balance = (
                        ancestor.v_coins_balance or Decimal("0.00")
                    ) + bonus_amount
                    update_fields.append("v_coins_balance")

                    # Convert V-Coins into integer stack count using direct bonus size
                    stack_count_for_member = int(
                        bonus_amount // PLAYER_DIRECT_REFERRAL_BONUS_VCOINS
                    )

                    ReferralReward.objects.create(
                        member=ancestor,
                        source_member=member,
                        reward_type=RewardType.PLAYER_STACK,
                        amount_rub=Decimal("0.00"),
                        stack_count=stack_count_for_member,
                        depth=level,
                    )

            if is_influencer and money_increment_int > 0:
                ancestor.total_money_earned = (
                    ancestor.total_money_earned or 0
                ) + money_increment_int
                update_fields.append("total_money_earned")
            elif not is_influencer and stack_count_for_member > 0:
                ancestor.total_bonus_points = (
                    ancestor.total_bonus_points or 0
                ) + stack_count_for_member
                update_fields.append("total_bonus_points")

            if update_fields:
                # Preserve field order but ensure uniqueness
                unique_update_fields = list(dict.fromkeys(update_fields))
                ancestor.save(update_fields=unique_update_fields)

            # Mark this ancestor/descendant pair as processed for first bonus
            relation.has_paid_first_bonus = True
            relation.save(update_fields=["has_paid_first_bonus"])

    # Recalculate ranks for all direct referrers outside of the atomic block.
    for ancestor_id in direct_ancestor_ids:
        try:
            ancestor_obj = Member.objects.get(pk=ancestor_id)
        except Member.DoesNotExist:
            continue
        check_for_rank_up(ancestor_obj)


def on_member_deposit(member: Member, deposit_amount: Decimal) -> None:
    """Apply lifetime 10% influencer commission for a member's deposit.

    The commission is paid only to the direct referrer when that referrer is an
    influencer (user_type == 'influencer'). The commission does not depend on
    ranks and is applied for every qualifying deposit.
    """

    if member.pk is None:
        return

    if not isinstance(deposit_amount, Decimal):
        deposit_amount = Decimal(str(deposit_amount))

    referrer: Member | None = member.referrer or member.referred_by
    if referrer is None:
        return

    if referrer.user_type != USER_TYPE_INFLUENCER:
        return

    commission = (deposit_amount * INFLUENCER_DEPOSIT_PERCENT).quantize(
        Decimal("0.01")
    )
    if commission <= 0:
        return

    referrer.cash_balance = (referrer.cash_balance or Decimal("0.00")) + commission

    update_fields: list[str] = ["cash_balance"]

    ReferralReward.objects.create(
        member=referrer,
        source_member=member,
        reward_type=RewardType.INFLUENCER_DEPOSIT_PERCENT,
        amount_rub=commission,
        stack_count=0,
        depth=1,
    )

    money_increment_int = int(commission)
    if money_increment_int > 0:
        referrer.total_money_earned = (
            referrer.total_money_earned or 0
        ) + money_increment_int
        update_fields.append("total_money_earned")

    referrer.save(update_fields=update_fields)


def process_member_deposit(
    member: Member,
    deposit_amount: Decimal,
    created_at=None,
) -> ReferralEvent | None:
    """Canonical helper to process a member deposit.

    This function encapsulates the full business flow that should happen when a
    member makes a deposit:
    - Creates a `ReferralEvent` for analytics (if a referrer is known).
    - If this is the first qualifying tournament/deposit for the member, calls
      `on_user_first_tournament_completed` to distribute deep one-time bonuses.
    - Calls `on_member_deposit` to apply the lifetime 10% influencer commission
      for the direct referrer (if applicable).

    Returns the created `ReferralEvent` instance, or ``None`` if no referrer is
    configured for the member and no event is created.
    """

    if member.pk is None:
        return None

    if not isinstance(deposit_amount, Decimal):
        deposit_amount = Decimal(str(deposit_amount))

    if deposit_amount <= 0:
        return None

    if created_at is None:
        created_at = timezone.now()

    referrer: Member | None = member.referrer or member.referred_by
    if referrer is None:
        # Without a referrer there is no referral event or commission.
        return None

    with transaction.atomic():
        event = ReferralEvent.objects.create(
            referrer=referrer,
            referred=member,
            bonus_amount=0,
            money_amount=0,
            deposit_amount=int(deposit_amount),
            created_at=created_at,
        )

        has_any_first_bonus = ReferralRelation.objects.filter(
            descendant=member,
            has_paid_first_bonus=True,
        ).exists()

        if not has_any_first_bonus:
            on_user_first_tournament_completed(member)

        on_member_deposit(member, deposit_amount)

    return event


def apply_influencer_commission_for_deposit(deposit: "Deposit") -> None:
    """Apply only the influencer 10% commission for a given Deposit instance.

    This is a thin wrapper around :func:`on_member_deposit` that operates
    directly on a Deposit model.
    """

    on_member_deposit(deposit.member, deposit.amount)


def process_deposit_for_referrals(deposit: "Deposit") -> ReferralEvent | None:
    """Process a Deposit instance through the full referral pipeline.

    - Creates a `ReferralEvent` for analytics.
    - Triggers first-tournament bonuses if needed.
    - Applies influencer 10% commission.
    """

    return process_member_deposit(
        deposit.member,
        deposit.amount,
        created_at=deposit.created_at,
    )


def create_spend_referral_bonus(
    spend_tx: "WalletTransaction",
) -> ReferralBonus | None:
    """Create and credit a referral bonus for a wallet SPEND transaction.

    The bonus is paid only to the direct referrer when that referrer is an
    influencer (user_type == 'influencer'). The bonus amount equals
    INFLUENCER_DEPOSIT_PERCENT of the spend amount. Idempotent per
    spend transaction.
    """

    if spend_tx is None or spend_tx.pk is None:
        return None

    if spend_tx.type != WalletTransaction.Type.SPEND:
        return None

    member = spend_tx.member
    if member is None or member.pk is None:
        return None

    referrer: Member | None = member.referrer or member.referred_by
    if referrer is None:
        return None

    if referrer.user_type != USER_TYPE_INFLUENCER:
        return None

    # Fast-path idempotency check
    existing = ReferralBonus.objects.filter(spend_transaction=spend_tx).first()
    if existing is not None:
        return existing

    amount = (spend_tx.amount * INFLUENCER_DEPOSIT_PERCENT).quantize(
        Decimal("0.01")
    )
    if amount <= 0:
        return None

    with transaction.atomic():
        # Double-check under lock for idempotency
        existing = (
            ReferralBonus.objects.select_for_update()
            .filter(spend_transaction=spend_tx)
            .first()
        )
        if existing is not None:
            return existing

        # Credit referrer's wallet using a dedicated BONUS transaction
        referrer._apply_wallet_change(
            delta=amount,
            tx_type=WalletTransaction.Type.BONUS,
            description=(
                f"Referral bonus from spend transaction #{spend_tx.id} "
                f"of member {member.id}"
            ),
            meta={
                "source_member_id": member.id,
                "spend_transaction_id": spend_tx.id,
            },
        )

        bonus = ReferralBonus.objects.create(
            referrer=referrer,
            referred_member=member,
            spend_transaction=spend_tx,
            amount=amount,
            description=(
                f"Referral bonus from spend transaction #{spend_tx.id} "
                f"of member {member.id}"
            ),
        )

        money_increment_int = int(amount)
        if money_increment_int > 0:
            referrer.total_money_earned = (
                referrer.total_money_earned or 0
            ) + money_increment_int
            referrer.save(update_fields=["total_money_earned"])

        return bonus


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
            # Create a new test member linked to Timur as direct referrer.
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
            # Ensure the existing member is linked to Timur as direct referrer.
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
                # Rebuild referral relations for the new referrer chain.
                on_new_user_registered(member)

        # Idempotency: if there is already a ReferralEvent for this
        # Timur -> member pair with the given amount, reuse it instead of
        # creating a new one. This keeps demo deposits stable across multiple
        # calls.
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
            "name": f"{timur.first_name} {timur.last_name}".strip(),
            "phone": timur.phone,
            "cash_balance_before": timur_cash_before,
            "cash_balance_after": timur_cash_after,
            "earnings_delta": earnings_delta,
        },
    }
