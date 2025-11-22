from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

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
    MemberAuthToken,
    PasswordResetCode,
    ReferralEvent,
    WalletTransaction,
)
from .referral_utils import (
    get_rank_multiplier,
    check_for_rank_up,
    on_new_user_registered,
    on_user_first_tournament_completed,
    on_member_deposit,
    simulate_business_model,
)

# ... existing test classes remain unchanged ...

class TestSimulateDemoDepositsAPITests(TestCase):
    # existing tests
    ...


class BusinessModelSimulationHelperTests(TestCase):
    """Tests for the deterministic business model simulation helper."""

    def test_helper_creates_entities_and_wallet_links(self):
        result = simulate_business_model()
        self.assertEqual(result["global_metrics"]["total_players"], 100)
        self.assertEqual(len(result["influencers"]), 3)
        scenario_tag = result["scenario_tag"]
        first_player = result["players"][0]
        player_member = Member.objects.get(pk=first_player["member_id"])
        self.assertTrue(
            WalletTransaction.objects.filter(
                member=player_member,
                meta__scenario=scenario_tag,
                meta__type="deposit",
            ).exists()
        )
        self.assertTrue(
            WalletTransaction.objects.filter(
                member=player_member,
                meta__scenario=scenario_tag,
                meta__type="spend",
            ).exists()
        )
        self.assertTrue(
            ReferralEvent.objects.filter(
                referrer_id=first_player["influencer_id"],
                referred=player_member,
            ).exists()
        )
        self.assertGreater(
            result["global_metrics"]["total_referral_rewards"],
            Decimal("0.00"),
        )

    def test_helper_is_idempotent(self):
        first = simulate_business_model()
        second = simulate_business_model()
        self.assertGreater(first["counters"]["new_wallet_deposits"], 0)
        self.assertEqual(second["counters"]["new_wallet_deposits"], 0)
        self.assertEqual(second["counters"]["new_wallet_spends"], 0)
        self.assertEqual(second["counters"]["new_referral_events"], 0)


class BusinessModelSimulationAPITests(TestCase):
    """Tests for the business model simulation API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.admin = Member(
            first_name="Admin",
            last_name="Business",
            phone="+79990006600",
            email=None,
            is_influencer=False,
            is_admin=True,
        )
        self.admin.set_password("adminpass123")
        self.admin.save()
        token = MemberAuthToken.create_for_member(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = "/api/test/simulate-business-model/"

    def test_simulation_endpoint_returns_metrics_and_is_idempotent(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["global_metrics"]["total_players"], 100)
        self.assertEqual(len(data["players"]), 100)
        self.assertEqual(len(data["influencers"]), 3)
        self.assertGreater(
            Decimal(data["global_metrics"]["total_deposit_volume"]),
            Decimal("0.00"),
        )
        scenario_tag = data["scenario_tag"]
        sample_player = data["players"][0]
        member = Member.objects.get(pk=sample_player["member_id"])
        self.assertTrue(
            WalletTransaction.objects.filter(
                member=member,
                meta__scenario=scenario_tag,
                meta__type="deposit",
            ).exists()
        )
        self.assertTrue(
            ReferralEvent.objects.filter(
                referrer_id=sample_player["influencer_id"],
                referred=member,
            ).exists()
        )
        second_response = self.client.post(self.url, {}, format="json")
        self.assertEqual(second_response.status_code, 200)
        second_data = second_response.json()
        self.assertEqual(second_data["counters"]["new_wallet_deposits"], 0)
        self.assertEqual(second_data["counters"]["new_wallet_spends"], 0)
        self.assertEqual(second_data["counters"]["new_referral_events"], 0)
