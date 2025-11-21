diff --git a/api/tests.py b/api/tests.py
index 36cd008..1f82157 100644
--- a/api/tests.py
+++ b/api/tests.py
@@ -24,6 +24,7 @@ from .models import (
     ReferralEvent,
     WalletTransaction,
     ReferralBonus,
+    ReferralReward,
     Deposit,
 )
 from .referral_utils import (
@@ -568,6 +569,146 @@ class ReferralDepositsAndBonusesAPITests(TestCase):
         self.assertEqual(resp_deposits.status_code, 401)
         self.assertEqual(resp_bonuses.status_code, 401)
 
 
+class ReferralActivationOnWalletDepositTests(TestCase):
+    """Ensure wallet deposits trigger referral activation and rewards."""
+
+    def setUp(self):
+        self.player_referrer = Member(
+            first_name="PlayerRef",
+            last_name="User",
+            phone="+79990200000",
+            email=None,
+            is_influencer=False,
+            is_admin=False,
+            user_type=USER_TYPE_PLAYER,
+        )
+        self.player_referrer.set_password("playerref123")
+        self.player_referrer.save()
+
+        self.referred_player = Member(
+            first_name="Referred",
+            last_name="Player",
+            phone="+79990200001",
+            email=None,
+            is_influencer=False,
+            is_admin=False,
+            user_type=USER_TYPE_PLAYER,
+            referrer=self.player_referrer,
+            referred_by=self.player_referrer,
+        )
+        self.referred_player.set_password("referred123")
+        self.referred_player.save()
+        on_new_user_registered(self.referred_player)
+
+        token = MemberAuthToken.create_for_member(self.referred_player)
+        self.client = APIClient()
+        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
+        self.deposit_url = "/api/wallet/deposit/"
+
+    def test_player_referrer_gets_first_bonus_on_wallet_deposit(self):
+        payload = {"amount": "1000.00", "description": "First wallet top-up"}
+        response = self.client.post(self.deposit_url, payload, format="json")
+        self.assertEqual(response.status_code, 201)
+
+        relation = ReferralRelation.objects.get(
+            ancestor=self.player_referrer,
+            descendant=self.referred_player,
+        )
+        self.assertTrue(relation.has_paid_first_bonus)
+
+        self.player_referrer.refresh_from_db()
+        self.assertEqual(
+            self.player_referrer.v_coins_balance,
+            PLAYER_DIRECT_REFERRAL_BONUS_VCOINS,
+        )
+
+        rewards = ReferralReward.objects.filter(
+            member=self.player_referrer,
+            source_member=self.referred_player,
+        )
+        self.assertEqual(rewards.count(), 1)
+        self.assertEqual(
+            rewards.first().reward_type,
+            ReferralReward.RewardType.PLAYER_STACK,
+        )
+
+        # Second deposit should not issue another first bonus
+        response_second = self.client.post(
+            self.deposit_url,
+            {"amount": "500.00", "description": "Second top-up"},
+            format="json",
+        )
+        self.assertEqual(response_second.status_code, 201)
+
+        self.player_referrer.refresh_from_db()
+        self.assertEqual(
+            self.player_referrer.v_coins_balance,
+            PLAYER_DIRECT_REFERRAL_BONUS_VCOINS,
+        )
+        self.assertEqual(
+            ReferralReward.objects.filter(
+                member=self.player_referrer,
+                source_member=self.referred_player,
+            ).count(),
+            1,
+        )
+
+    def test_influencer_referrer_gets_first_bonus_and_commission(self):
+        influencer = Member(
+            first_name="Influencer",
+            last_name="Ref",
+            phone="+79990200002",
+            email=None,
+            is_influencer=True,
+            is_admin=False,
+            user_type=USER_TYPE_INFLUENCER,
+        )
+        influencer.set_password("inflpass123")
+        influencer.save()
+
+        referred = Member(
+            first_name="Referred",
+            last_name="Influencer",
+            phone="+79990200003",
+            email=None,
+            is_influencer=False,
+            is_admin=False,
+            user_type=USER_TYPE_PLAYER,
+            referrer=influencer,
+            referred_by=influencer,
+        )
+        referred.set_password("referredinfl123")
+        referred.save()
+        on_new_user_registered(referred)
+
+        token = MemberAuthToken.create_for_member(referred)
+        client = APIClient()
+        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
+
+        first_amount = Decimal("2000.00")
+        resp = client.post(
+            self.deposit_url,
+            {"amount": str(first_amount), "description": "Influencer first"},
+            format="json",
+        )
+        self.assertEqual(resp.status_code, 201)
+
+        relation = ReferralRelation.objects.get(ancestor=influencer, descendant=referred)
+        self.assertTrue(relation.has_paid_first_bonus)
+
+        influencer.refresh_from_db()
+        expected_first_commission = (
+            first_amount * INFLUENCER_DEPOSIT_PERCENT
+        ).quantize(Decimal("0.01"))
+        expected_cash_after_first = (
+            INFLUENCER_DIRECT_REFERRAL_BONUS_CASH + expected_first_commission
+        )
+        self.assertEqual(influencer.cash_balance, expected_cash_after_first)
+
+        rewards = ReferralReward.objects.filter(member=influencer, source_member=referred)
+        self.assertEqual(rewards.count(), 1)
+        reward = rewards.first()
+        self.assertEqual(
+            reward.reward_type,
+            ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
+        )
+        self.assertEqual(reward.amount_rub, INFLUENCER_DIRECT_REFERRAL_BONUS_CASH)
+
+        second_amount = Decimal("500.00")
+        resp_second = client.post(
+            self.deposit_url,
+            {"amount": str(second_amount), "description": "Influencer second"},
+            format="json",
+        )
+        self.assertEqual(resp_second.status_code, 201)
+
+        influencer.refresh_from_db()
+        expected_second_commission = (
+            second_amount * INFLUENCER_DEPOSIT_PERCENT
+        ).quantize(Decimal("0.01"))
+        self.assertEqual(
+            influencer.cash_balance,
+            expected_cash_after_first + expected_second_commission,
+        )
+        self.assertEqual(
+            ReferralReward.objects.filter(member=influencer, source_member=referred).count(),
+            1,
+        )
+
+
 class RankedReferralLogicTests(TestCase):
     def _create_member(
         self,
