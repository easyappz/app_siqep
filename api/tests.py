diff --git a/api/tests.py b/api/tests.py
index 37c3f3f..b4bd9f4 100644
--- a/api/tests.py
+++ b/api/tests.py
@@
 class ReferralDepositsAndBonusesAPITests(TestCase):
     """Tests for referral deposits and bonuses API endpoints and profile stats aggregates."""
@@
         self.assertEqual(resp_bonuses.status_code, 401)
 
 
+class ReferralActivationOnWalletDepositTests(TestCase):
+    """Ensure wallet deposits trigger referral activation and payouts."""
+
+    def setUp(self):
+        self.deposit_url = "/api/wallet/deposit/"
+
+    def _create_referrer(self, *, phone: str, influencer: bool) -> Member:
+        referrer = Member(
+            first_name="Referrer",
+            last_name="Wallet",
+            phone=phone,
+            email=None,
+            is_influencer=influencer,
+            is_admin=False,
+            user_type=USER_TYPE_INFLUENCER if influencer else USER_TYPE_PLAYER,
+        )
+        referrer.set_password("referrerpass123")
+        referrer.save()
+        return referrer
+
+    def _create_referred(self, referrer: Member, *, phone: str) -> Member:
+        referred = Member(
+            first_name="Referred",
+            last_name="Wallet",
+            phone=phone,
+            email=None,
+            is_influencer=False,
+            is_admin=False,
+            user_type=USER_TYPE_PLAYER,
+            referrer=referrer,
+            referred_by=referrer,
+        )
+        referred.set_password("referredpass123")
+        referred.save()
+        on_new_user_registered(referred)
+        return referred
+
+    def _auth_client(self, member: Member) -> APIClient:
+        token = MemberAuthToken.create_for_member(member)
+        client = APIClient()
+        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
+        return client
+
+    def test_player_referrer_becomes_active_after_wallet_deposit(self):
+        referrer = self._create_referrer(phone="+79990500001", influencer=False)
+        referred = self._create_referred(referrer, phone="+79990500002")
+
+        client = self._auth_client(referred)
+        response = client.post(
+            self.deposit_url,
+            {"amount": "500.00", "description": "First wallet deposit"},
+            format="json",
+        )
+        self.assertEqual(response.status_code, 201)
+
+        relation = ReferralRelation.objects.get(
+            ancestor=referrer,
+            descendant=referred,
+            level=1,
+        )
+        self.assertTrue(relation.has_paid_first_bonus)
+
+        referrer.refresh_from_db()
+        self.assertEqual(referrer.v_coins_balance, PLAYER_DIRECT_REFERRAL_BONUS_VCOINS)
+
+        self.assertEqual(
+            ReferralEvent.objects.filter(referrer=referrer, referred=referred).count(),
+            1,
+        )
+
+    def test_influencer_referrer_gets_first_bonus_and_commission(self):
+        referrer = self._create_referrer(phone="+79990500003", influencer=True)
+        referred = self._create_referred(referrer, phone="+79990500004")
+
+        client = self._auth_client(referred)
+        first_amount = Decimal("1200.00")
+        response = client.post(
+            self.deposit_url,
+            {"amount": str(first_amount)},
+            format="json",
+        )
+        self.assertEqual(response.status_code, 201)
+
+        relation = ReferralRelation.objects.get(
+            ancestor=referrer,
+            descendant=referred,
+            level=1,
+        )
+        self.assertTrue(relation.has_paid_first_bonus)
+
+        percent_first = (first_amount * INFLUENCER_DEPOSIT_PERCENT).quantize(Decimal("0.01"))
+        expected_after_first = INFLUENCER_DIRECT_REFERRAL_BONUS_CASH + percent_first
+
+        referrer.refresh_from_db()
+        self.assertEqual(referrer.cash_balance, expected_after_first)
+
+        self.assertEqual(
+            ReferralReward.objects.filter(
+                member=referrer,
+                source_member=referred,
+                reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
+            ).count(),
+            1,
+        )
+
+        second_amount = Decimal("800.00")
+        response_second = client.post(
+            self.deposit_url,
+            {"amount": str(second_amount)},
+            format="json",
+        )
+        self.assertEqual(response_second.status_code, 201)
+
+        percent_second = (second_amount * INFLUENCER_DEPOSIT_PERCENT).quantize(Decimal("0.01"))
+        referrer.refresh_from_db()
+        self.assertEqual(referrer.cash_balance, expected_after_first + percent_second)
+
+        self.assertEqual(
+            ReferralReward.objects.filter(
+                member=referrer,
+                source_member=referred,
+                reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
+            ).count(),
+            1,
+        )
+
+        self.assertEqual(
+            ReferralEvent.objects.filter(referrer=referrer, referred=referred).count(),
+            2,
+        )
+
+
 class RankedReferralLogicTests(TestCase):
     def _create_member(
         self,
