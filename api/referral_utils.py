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
)


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

            if relation.level == 1:
                # Direct referrer bonus
                if is_influencer:
                    bonus_amount = INFLUENCER_DIRECT_REFERRAL_BONUS_CASH
                    ancestor.cash_balance = (ancestor.cash_balance or Decimal("0.00")) + bonus_amount
                    ancestor.save(update_fields=["cash_balance"])
                else:
                    bonus_amount = PLAYER_DIRECT_REFERRAL_BONUS_VCOINS
                    ancestor.v_coins_balance = (ancestor.v_coins_balance or Decimal("0.00")) + bonus_amount
                    ancestor.save(update_fields=["v_coins_balance"])

                direct_ancestor_ids.add(ancestor.pk)
            else:
                # Deep cashback (levels 2..MAX_REFERRAL_DEPTH)
                if is_influencer:
                    base_bonus = INFLUENCER_DEPTH_BASE_BONUS_CASH
                    multiplier = get_rank_multiplier(ancestor.rank, USER_TYPE_INFLUENCER)
                    bonus_amount = (base_bonus * multiplier).quantize(Decimal("0.01"))
                    ancestor.cash_balance = (ancestor.cash_balance or Decimal("0.00")) + bonus_amount
                    ancestor.save(update_fields=["cash_balance"])
                else:
                    base_bonus = PLAYER_DEPTH_BASE_BONUS_VCOINS
                    multiplier = get_rank_multiplier(ancestor.rank, USER_TYPE_PLAYER)
                    bonus_amount = (base_bonus * multiplier).quantize(Decimal("0.01"))
                    ancestor.v_coins_balance = (ancestor.v_coins_balance or Decimal("0.00")) + bonus_amount
                    ancestor.save(update_fields=["v_coins_balance"])

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

    commission = (deposit_amount * INFLUENCER_DEPOSIT_PERCENT).quantize(Decimal("0.01"))
    if commission <= 0:
        return

    referrer.cash_balance = (referrer.cash_balance or Decimal("0.00")) + commission
    referrer.save(update_fields=["cash_balance"])


def process_member_deposit(member: Member, deposit_amount: Decimal, created_at=None) -> ReferralEvent | None:
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
