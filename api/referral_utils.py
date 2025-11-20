from __future__ import annotations

from decimal import Decimal
from typing import List, Tuple

from .models import Member, ReferralReward


def get_referral_ancestors(member: Member) -> list[tuple[Member, int]]:
    """Return a list of (ancestor, depth) for the given member.

    Depth starts at 1 for direct referrer, 2 for the next level, and so on.
    A simple cycle protection is included via the visited_ids set.
    """
    ancestors: list[tuple[Member, int]] = []
    visited_ids = set()
    current = member.referred_by
    depth = 1

    while current is not None and current.id not in visited_ids:
        ancestors.append((current, depth))
        visited_ids.add(current.id)
        current = current.referred_by
        depth += 1

    return ancestors


def _is_influencer_active_for_event(member: Member, event_time) -> bool:
    """Return True if member is influencer and active for the given event time."""
    if not member.is_influencer:
        return False
    if member.influencer_since is None:
        # Backward compatibility: influencer existed before influencer_since field.
        return True
    return member.influencer_since <= event_time


def create_player_stack_rewards_for_new_member(member: Member) -> None:
    """Create PLAYER_STACK rewards (1 stack) for all ancestors of a new member.

    Each ancestor (on any depth) receives one free starting stack.
    Member.total_bonus_points is updated accordingly.
    """
    ancestors = get_referral_ancestors(member)
    for ancestor, depth in ancestors:
        ReferralReward.objects.create(
            member=ancestor,
            source_member=member,
            reward_type=ReferralReward.RewardType.PLAYER_STACK,
            amount_rub=Decimal("0.00"),
            stack_count=1,
            depth=depth,
        )
        ancestor.total_bonus_points += 1
        ancestor.save(update_fields=["total_bonus_points"])


def create_influencer_deposit_rewards(
    source_member: Member,
    deposit_amount: int,
    event_time,
) -> None:
    """Create influencer rewards for a deposit event.

    Business rules:
    - For the first tournament (first reward of type INFLUENCER_FIRST_TOURNAMENT
      for this source_member), every influencer ancestor active at event_time
      receives 1000 RUB.
    - For all further deposits of this source_member, every active influencer
      ancestor receives 10% of deposit_amount as INFLUENCER_DEPOSIT_PERCENT.
    - influencer_since is taken into account so that rewards are generated only
      for events that happen after a member becomes an influencer.
    """
    ancestors = get_referral_ancestors(source_member)
    if not ancestors:
        return

    has_first_tournament_reward = ReferralReward.objects.filter(
        source_member=source_member,
        reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
    ).exists()

    for ancestor, depth in ancestors:
        if not _is_influencer_active_for_event(ancestor, event_time):
            continue

        if not has_first_tournament_reward:
            reward = ReferralReward.objects.create(
                member=ancestor,
                source_member=source_member,
                reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
                amount_rub=Decimal("1000.00"),
                stack_count=0,
                depth=depth,
            )
            ancestor.total_money_earned += int(reward.amount_rub)
            ancestor.save(update_fields=["total_money_earned"])
        else:
            reward_amount = (Decimal(deposit_amount) * Decimal("0.10")).quantize(
                Decimal("0.01")
            )
            reward = ReferralReward.objects.create(
                member=ancestor,
                source_member=source_member,
                reward_type=ReferralReward.RewardType.INFLUENCER_DEPOSIT_PERCENT,
                amount_rub=reward_amount,
                stack_count=0,
                depth=depth,
            )
            ancestor.total_money_earned += int(reward.amount_rub)
            ancestor.save(update_fields=["total_money_earned"])

        # Once at least one influencer ancestor received FIRST_TOURNAMENT reward,
        # subsequent deposits for this source_member will be treated as
        # "further deposits" and only generate DEPOSIT_PERCENT rewards.
        if not has_first_tournament_reward:
            has_first_tournament_reward = True
