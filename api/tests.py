from decimal import Decimal

from django.test import TestCase

from .models import (
    Member,
    ReferralRelation,
    RankRule,
    USER_TYPE_PLAYER,
    USER_TYPE_INFLUENCER,
    RANK_STANDARD,
    RANK_SILVER,
    RANK_GOLD,
    RANK_PLATINUM,
    PLAYER_DIRECT_REFERRAL_BONUS_VCOINS,
    PLAYER_DEPTH_BASE_BONUS_VCOINS,
    INFLUENCER_DIRECT_REFERRAL_BONUS_CASH,
    INFLUENCER_DEPTH_BASE_BONUS_CASH,
    INFLUENCER_DEPOSIT_PERCENT,
)
from .referral_utils import (
    get_rank_multiplier,
    check_for_rank_up,
    on_new_user_registered,
    on_user_first_tournament_completed,
    on_member_deposit,
)


class RankedReferralLogicTests(TestCase):
    def _create_member(
        self,
        first_name: str,
        user_type: str = USER_TYPE_PLAYER,
        rank: str = RANK_STANDARD,
        referrer: Member | None = None,
    ) -> Member:
        index = Member.objects.count() + 1
        member = Member(
            first_name=first_name,
            last_name="Test",
            phone=f"+700000000{index}",
            email=None,
            is_influencer=(user_type == USER_TYPE_INFLUENCER),
            is_admin=False,
            user_type=user_type,
            rank=rank,
            referrer=referrer,
            referred_by=referrer,
        )
        member.set_password("password123")
        member.save()
        return member

    def test_get_rank_multiplier_values(self):
        """Rank multipliers should match the configured RankRule values."""
        # Migration 0004 pre-populates these, but we assert them anyway.
        expected = {
            RANK_STANDARD: Decimal("1.00"),
            RANK_SILVER: Decimal("1.50"),
            RANK_GOLD: Decimal("2.00"),
            RANK_PLATINUM: Decimal("2.50"),
        }

        for rank, multiplier in expected.items():
            player_mult = get_rank_multiplier(rank, USER_TYPE_PLAYER)
            infl_mult = get_rank_multiplier(rank, USER_TYPE_INFLUENCER)
            self.assertEqual(player_mult, multiplier)
            self.assertEqual(infl_mult, multiplier)

        # Unknown rank or type should fall back to 1.00
        self.assertEqual(get_rank_multiplier("unknown", USER_TYPE_PLAYER), Decimal("1.00"))
        self.assertEqual(get_rank_multiplier(RANK_STANDARD, "unknown"), Decimal("1.00"))

    def test_chain_example_rewards(self):
        """Example chain: Influencer A -> Player B -> Player C -> New Player D.

        According to the spec, when D completes first tournament:
        - C (standard player, level 1) gets 1000 V-Coins.
        - B (silver player, level 2) gets 100 * 1.5 = 150 V-Coins.
        - A (platinum influencer, level 3) gets 50 * 2.5 = 125 ₽.
        """

        # Build members with desired ranks and types.
        a = self._create_member(
            "InfluencerA",
            user_type=USER_TYPE_INFLUENCER,
            rank=RANK_PLATINUM,
        )
        b = self._create_member(
            "PlayerB",
            user_type=USER_TYPE_PLAYER,
            rank=RANK_SILVER,
            referrer=a,
        )
        on_new_user_registered(b)

        c = self._create_member(
            "PlayerC",
            user_type=USER_TYPE_PLAYER,
            rank=RANK_STANDARD,
            referrer=b,
        )
        on_new_user_registered(c)

        d = self._create_member(
            "PlayerD",
            user_type=USER_TYPE_PLAYER,
            rank=RANK_STANDARD,
            referrer=c,
        )
        on_new_user_registered(d)

        # Sanity-check referral relations for D
        relations_d = ReferralRelation.objects.filter(descendant=d).order_by("level")
        self.assertEqual(relations_d.count(), 3)
        self.assertEqual(relations_d[0].ancestor, c)
        self.assertEqual(relations_d[0].level, 1)
        self.assertEqual(relations_d[1].ancestor, b)
        self.assertEqual(relations_d[1].level, 2)
        self.assertEqual(relations_d[2].ancestor, a)
        self.assertEqual(relations_d[2].level, 3)

        # First tournament for D
        on_user_first_tournament_completed(d)

        a.refresh_from_db()
        b.refresh_from_db()
        c.refresh_from_db()

        # C: direct referrer, standard player
        self.assertEqual(c.v_coins_balance, PLAYER_DIRECT_REFERRAL_BONUS_VCOINS)

        # B: silver player, depth bonus
        expected_b = (PLAYER_DEPTH_BASE_BONUS_VCOINS * Decimal("1.50")).quantize(
            Decimal("0.01")
        )
        self.assertEqual(b.v_coins_balance, expected_b)

        # A: platinum influencer, depth bonus
        expected_a = (INFLUENCER_DEPTH_BASE_BONUS_CASH * Decimal("2.50")).quantize(
            Decimal("0.01")
        )
        self.assertEqual(a.cash_balance, expected_a)

        # Ensure flags are set so repeated calls are idempotent
        for rel in ReferralRelation.objects.filter(descendant=d):
            self.assertTrue(rel.has_paid_first_bonus)

        # Second call should not change balances
        on_user_first_tournament_completed(d)
        a.refresh_from_db()
        b.refresh_from_db()
        c.refresh_from_db()
        self.assertEqual(c.v_coins_balance, PLAYER_DIRECT_REFERRAL_BONUS_VCOINS)
        self.assertEqual(b.v_coins_balance, expected_b)
        self.assertEqual(a.cash_balance, expected_a)

    def test_has_paid_first_bonus_prevents_double_payment(self):
        """First-tournament rewards must be paid only once per ancestor/descendant pair."""
        parent = self._create_member("Parent", user_type=USER_TYPE_PLAYER)
        child = self._create_member("Child", user_type=USER_TYPE_PLAYER, referrer=parent)
        on_new_user_registered(child)

        # First tournament
        on_user_first_tournament_completed(child)
        parent.refresh_from_db()
        self.assertEqual(parent.v_coins_balance, PLAYER_DIRECT_REFERRAL_BONUS_VCOINS)

        # Second tournament should not change anything
        on_user_first_tournament_completed(child)
        parent.refresh_from_db()
        self.assertEqual(parent.v_coins_balance, PLAYER_DIRECT_REFERRAL_BONUS_VCOINS)

    def test_rank_up_when_active_level1_referrals_increase(self):
        """Ranks upgrade at thresholds 5/20/50 of active level-1 referrals."""
        root = self._create_member("Root", user_type=USER_TYPE_PLAYER, rank=RANK_STANDARD)

        for i in range(1, 51):
            child = self._create_member(
                f"Child{i}",
                user_type=USER_TYPE_PLAYER,
                rank=RANK_STANDARD,
                referrer=root,
            )
            on_new_user_registered(child)
            on_user_first_tournament_completed(child)
            root.refresh_from_db()

            if i == 4:
                self.assertEqual(root.rank, RANK_STANDARD)
            if i == 5:
                self.assertEqual(root.rank, RANK_SILVER)
            if i == 19:
                self.assertEqual(root.rank, RANK_SILVER)
            if i == 20:
                self.assertEqual(root.rank, RANK_GOLD)
            if i == 49:
                self.assertEqual(root.rank, RANK_GOLD)
            if i == 50:
                self.assertEqual(root.rank, RANK_PLATINUM)

    def test_on_member_deposit_direct_influencer_only(self):
        """10% deposit commission is paid only to the direct influencer referrer."""
        influencer = self._create_member(
            "Influencer",
            user_type=USER_TYPE_INFLUENCER,
            rank=RANK_STANDARD,
        )
        player = self._create_member(
            "Player",
            user_type=USER_TYPE_PLAYER,
            rank=RANK_STANDARD,
            referrer=influencer,
        )
        on_new_user_registered(player)

        # First deposit by the direct referral
        deposit_amount = Decimal("1000")
        on_member_deposit(player, deposit_amount)
        influencer.refresh_from_db()
        expected_commission = (deposit_amount * INFLUENCER_DEPOSIT_PERCENT).quantize(
            Decimal("0.01")
        )
        self.assertEqual(influencer.cash_balance, expected_commission)

        # Second deposit by the same referral doubles the commission
        on_member_deposit(player, deposit_amount)
        influencer.refresh_from_db()
        self.assertEqual(influencer.cash_balance, expected_commission * 2)

        # A deeper descendant should not give any commission to the top influencer
        child = self._create_member(
            "Child",
            user_type=USER_TYPE_PLAYER,
            rank=RANK_STANDARD,
            referrer=player,
        )
        on_new_user_registered(child)
        on_member_deposit(child, deposit_amount)
        influencer.refresh_from_db()
        # Still only two direct-deposit commissions from `player`
        self.assertEqual(influencer.cash_balance, expected_commission * 2)

    def test_check_for_rank_up_uses_active_level1_referrals_only(self):
        """Only referrals with has_paid_first_bonus=True on level 1 should count for rank."""
        member = self._create_member("Root", user_type=USER_TYPE_PLAYER, rank=RANK_STANDARD)

        # Two level-1 referrals: one active, one not
        active_ref = self._create_member(
            "ActiveRef",
            user_type=USER_TYPE_PLAYER,
            referrer=member,
        )
        on_new_user_registered(active_ref)
        on_user_first_tournament_completed(active_ref)

        inactive_ref = self._create_member(
            "InactiveRef",
            user_type=USER_TYPE_PLAYER,
            referrer=member,
        )
        on_new_user_registered(inactive_ref)
        # No first tournament call for inactive_ref

        check_for_rank_up(member)
        member.refresh_from_db()

        # With only 1 active referral, rank must still be standard
        self.assertEqual(member.rank, RANK_STANDARD)
