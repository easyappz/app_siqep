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
)


class WalletModelTests(TestCase):
    """Tests for core wallet operations on Member and WalletTransaction."""

    def setUp(self):
        self.member = Member(
            first_name="Wallet",
            last_name="User",
            phone="+79990006666",
            email=None,
            is_influencer=False,
            is_admin=False,
        )
        self.member.set_password("wallet123")
        self.member.save()

        self.influencer = Member(
            first_name="WalletInfluencer",
            last_name="User",
            phone="+79990007777",
            email=None,
            is_influencer=True,
            is_admin=False,
            user_type=USER_TYPE_INFLUENCER,
        )
        self.influencer.set_password("wallet123")
        self.influencer.save()

    def test_deposit_creates_transaction_and_increases_balance(self):
        amount = Decimal("100.50")

        tx = self.member.deposit(amount, description="Test deposit")

        self.member.refresh_from_db()
        self.assertEqual(self.member.cash_balance, amount)

        self.assertIsNotNone(tx)
        self.assertEqual(tx.member, self.member)
        self.assertEqual(tx.type, WalletTransaction.Type.DEPOSIT)
        self.assertEqual(tx.amount, amount)
        self.assertEqual(tx.balance_after, amount)

        self.assertEqual(
            WalletTransaction.objects.filter(member=self.member).count(),
            1,
        )

    def test_spend_more_than_balance_raises_error_and_creates_no_transaction(self):
        amount = Decimal("50.00")

        with self.assertRaises(ValueError):
            self.member.spend(amount, description="Should fail")

        self.assertEqual(
            WalletTransaction.objects.filter(member=self.member).count(),
            0,
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.cash_balance, Decimal("0.00"))

    def test_influencer_wallet_behaves_same_as_regular_member(self):
        deposit_amount = Decimal("200.00")
        spend_amount = Decimal("50.00")

        self.influencer.deposit(deposit_amount, description="Influencer deposit")
        self.influencer.spend(spend_amount, description="Influencer spend")

        self.influencer.refresh_from_db()
        expected_balance = deposit_amount - spend_amount
        self.assertEqual(self.influencer.cash_balance, expected_balance)

        tx_types = list(
            WalletTransaction.objects.filter(member=self.influencer)
            .order_by("created_at")
            .values_list("type", flat=True)
        )
        self.assertEqual(
            tx_types,
            [WalletTransaction.Type.DEPOSIT, WalletTransaction.Type.SPEND],
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


class TestSimulateDepositsAPITests(TestCase):
    """Tests for the test-only simulate-deposits endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/test/simulate-deposits/"

        self.admin = Member(
            first_name="Admin",
            last_name="User",
            phone="+79990009999",
            email=None,
            is_influencer=False,
            is_admin=True,
        )
        self.admin.set_password("adminpass123")
        self.admin.save()

        token = MemberAuthToken.create_for_member(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_simulate_deposits_creates_members_and_applies_deposit(self):
        Member.objects.filter(
            phone__in=["+79990000001", "+79990000002"],
        ).delete()

        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(len(data.get("deposits", [])), 2)

        phones_seen = set()
        for item in data["deposits"]:
            member_data = item["member"]
            phone = member_data["phone"]
            phones_seen.add(phone)
            self.assertIn(phone, ["+79990000001", "+79990000002"])
            self.assertEqual(item["amount"], 2000)

            # Balances fields must be present
            self.assertIn("v_coins_balance_after", item)
            self.assertIn("cash_balance_after", item)

        self.assertEqual(phones_seen, {"+79990000001", "+79990000002"})

    def test_simulate_deposits_requires_admin(self):
        # Unauthenticated request
        client = APIClient()
        response = client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 401)

        # Authenticated non-admin
        regular = Member(
            first_name="User",
            last_name="Regular",
            phone="+79990008888",
            email=None,
            is_influencer=False,
            is_admin=False,
        )
        regular.set_password("userpass123")
        regular.save()
        token = MemberAuthToken.create_for_member(regular)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 403)


class TestSimulateDemoDepositsAPITests(TestCase):
    """Tests for the demo simulate-deposits endpoint with Timur earnings."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/test/simulate_demo_deposits/"

        # Ensure test members for Amir and Alfirа are clean
        Member.objects.filter(
            phone__in=["+79990000001", "+79990000002"],
        ).delete()

        # Ensure Timur exists with canonical phone and influencer status
        self.timur, _ = Member.objects.get_or_create(
            phone="89031221111",
            defaults={
                "first_name": "Тимур",
                "last_name": "Комаров",
                "email": None,
                "is_influencer": True,
                "is_admin": False,
                "user_type": USER_TYPE_INFLUENCER,
            },
        )
        timur_updated_fields = []
        if not self.timur.is_influencer:
            self.timur.is_influencer = True
            timur_updated_fields.append("is_influencer")
        if self.timur.user_type != USER_TYPE_INFLUENCER:
            self.timur.user_type = USER_TYPE_INFLUENCER
            timur_updated_fields.append("user_type")
        if timur_updated_fields:
            self.timur.save(update_fields=timur_updated_fields)

        # Create admin and auth token
        self.admin, _ = Member.objects.get_or_create(
            phone="+79990009999",
            defaults={
                "first_name": "Admin",
                "last_name": "User",
                "email": None,
                "is_influencer": False,
                "is_admin": True,
            },
        )
        if not self.admin.is_admin:
            self.admin.is_admin = True
            self.admin.save(update_fields=["is_admin"])

        token = MemberAuthToken.create_for_member(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_simulate_demo_deposits_creates_deposits_and_updates_timur(self):
        timur_before = self.timur.cash_balance

        response = self.client.post(self.url, {"amount": 2000}, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("players", data)
        self.assertIn("timur", data)

        players = data["players"]
        self.assertEqual(len(players), 2)

        phones_seen = set()
        for player in players:
            phone = player["phone"]
            phones_seen.add(phone)
            self.assertIn(phone, ["+79990000001", "+79990000002"])

            deposits = player.get("deposits", [])
            self.assertEqual(len(deposits), 1)
            self.assertEqual(deposits[0]["amount"], 2000)
            self.assertIn("id", deposits[0])
            self.assertIn("created_at", deposits[0])

            member = Member.objects.get(phone=phone)
            # Ensure a ReferralEvent with deposit_amount=2000 exists for this member
            self.assertTrue(
                ReferralEvent.objects.filter(
                    referred=member,
                    deposit_amount=2000,
                ).exists()
            )

        self.assertEqual(phones_seen, {"+79990000001", "+79990000002"})

        self.timur.refresh_from_db()
        self.assertGreater(self.timur.cash_balance, timur_before)

        timur_data = data["timur"]
        self.assertEqual(timur_data["member_id"], self.timur.id)
        self.assertEqual(timur_data["phone"], "89031221111")

        earnings_delta = Decimal(str(timur_data["earnings_delta"]))
        self.assertGreater(earnings_delta, Decimal("0"))

    def test_simulate_demo_deposits_is_idempotent(self):
        # First call creates demo deposits
        response1 = self.client.post(self.url, {"amount": 2000}, format="json")
        self.assertEqual(response1.status_code, 200)

        # Capture ReferralEvent counts after first call
        players_phones = ["+79990000001", "+79990000002"]
        first_counts = {}
        for phone in players_phones:
            member = Member.objects.get(phone=phone)
            first_counts[phone] = ReferralEvent.objects.filter(
                referred=member,
                deposit_amount=2000,
            ).count()

        self.timur.refresh_from_db()
        timur_after_first = self.timur.cash_balance

        # Second call should not create additional deposits or change Timur balance
        response2 = self.client.post(self.url, {"amount": 2000}, format="json")
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()

        self.timur.refresh_from_db()
        timur_after_second = self.timur.cash_balance
        self.assertEqual(timur_after_second, timur_after_first)

        timur_data = data2["timur"]
        earnings_delta = Decimal(str(timur_data["earnings_delta"]))
        self.assertEqual(earnings_delta, Decimal("0.00"))

        for phone in players_phones:
            member = Member.objects.get(phone=phone)
            second_count = ReferralEvent.objects.filter(
                referred=member,
                deposit_amount=2000,
            ).count()
            self.assertEqual(second_count, first_counts[phone])


class ChangePasswordAPITests(TestCase):
    """Tests for authenticated password change endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.member = Member(
            first_name="User",
            last_name="Test",
            phone="+79990001111",
            email="user@example.com",
            is_influencer=False,
            is_admin=False,
        )
        self.member.set_password("oldpass123")
        self.member.save()

        token = MemberAuthToken.create_for_member(self.member)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_change_password_success(self):
        url = "/api/auth/change-password/"
        payload = {
            "old_password": "oldpass123",
            "new_password": "newpass456",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("detail"), "Пароль успешно изменён.")

        # Login with new password should succeed
        login_client = APIClient()
        login_response_new = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": "newpass456"},
            format="json",
        )
        self.assertEqual(login_response_new.status_code, 200)
        self.assertIn("token", login_response_new.json())

        # Login with old password should fail
        login_response_old = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": "oldpass123"},
            format="json",
        )
        self.assertEqual(login_response_old.status_code, 400)

    def test_change_password_wrong_old_password(self):
        url = "/api/auth/change-password/"
        payload = {
            "old_password": "wrongpass",
            "new_password": "newpass456",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("old_password", data)
        self.assertEqual(data["old_password"], ["Неверный текущий пароль."])

    def test_change_password_unauthorized(self):
        client = APIClient()
        response = client.post(
            "/api/auth/change-password/",
            {"old_password": "oldpass123", "new_password": "newpass456"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)


class PasswordResetAPITests(TestCase):
    """Tests for password reset via one-time code endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.member = Member(
            first_name="Reset",
            last_name="User",
            phone="+79990002222",
            email="reset@example.com",
            is_influencer=False,
            is_admin=False,
        )
        self.member.set_password("oldreset123")
        self.member.save()

    def test_password_reset_request_and_confirm_by_phone(self):
        # Request reset code by phone
        request_response = self.client.post(
            "/api/auth/password-reset/request/",
            {"phone": self.member.phone},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)
        data = request_response.json()
        self.assertEqual(data.get("detail"), "Код для смены пароля отправлен.")
        dev_code = data.get("dev_code")
        self.assertIsNotNone(dev_code)
        self.assertEqual(len(dev_code), 6)

        # Confirm reset with received code
        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "phone": self.member.phone,
                "code": dev_code,
                "new_password": "newreset123",
            },
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 200)
        confirm_data = confirm_response.json()
        self.assertEqual(confirm_data.get("detail"), "Пароль успешно сброшен.")

        # Code must be marked as used
        reset_code_obj = PasswordResetCode.objects.get(member=self.member, code=dev_code)
        self.assertTrue(reset_code_obj.is_used)

        # Login with new password should succeed
        login_client = APIClient()
        login_response_new = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": "newreset123"},
            format="json",
        )
        self.assertEqual(login_response_new.status_code, 200)

        # Old password should no longer work
        login_response_old = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": "oldreset123"},
            format="json",
        )
        self.assertEqual(login_response_old.status_code, 400)

    def test_password_reset_request_invalid_phone(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"phone": "+79990009900"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("non_field_errors", data)
        self.assertEqual(
            data["non_field_errors"],
            ["Пользователь с таким email/телефоном не найден."],
        )

    def test_password_reset_request_invalid_email(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "unknown@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("non_field_errors", data)
        self.assertEqual(
            data["non_field_errors"],
            ["Пользователь с таким email/телефоном не найден."],
        )

    def test_password_reset_confirm_invalid_code(self):
        # Create a valid code first
        request_response = self.client.post(
            "/api/auth/password-reset/request/",
            {"phone": self.member.phone},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)

        # Try to confirm with a wrong code
        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "phone": self.member.phone,
                "code": "000000",
                "new_password": "newreset123",
            },
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 400)
        data = confirm_response.json()
        self.assertIn("code", data)
        self.assertEqual(data["code"], ["Неверный или просроченный код."])

    def test_password_reset_confirm_expired_code(self):
        # Request a code
        request_response = self.client.post(
            "/api/auth/password-reset/request/",
            {"phone": self.member.phone},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)
        dev_code = request_response.json()["dev_code"]

        # Expire the code manually
        reset_code_obj = PasswordResetCode.objects.get(member=self.member, code=dev_code)
        reset_code_obj.expires_at = timezone.now() - timedelta(minutes=1)
        reset_code_obj.save(update_fields=["expires_at"])

        # Try to confirm with expired code
        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "phone": self.member.phone,
                "code": dev_code,
                "new_password": "newreset123",
            },
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 400)
        data = confirm_response.json()
        self.assertIn("code", data)
        self.assertEqual(data["code"], ["Неверный или просроченный код."])

    def test_password_reset_confirm_reuse_code_not_allowed(self):
        # Request a code
        request_response = self.client.post(
            "/api/auth/password-reset/request/",
            {"phone": self.member.phone},
            format="json",
        )
        self.assertEqual(request_response.status_code, 200)
        dev_code = request_response.json()["dev_code"]

        # First successful confirmation
        first_confirm = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "phone": self.member.phone,
                "code": dev_code,
                "new_password": "newreset123",
            },
            format="json",
        )
        self.assertEqual(first_confirm.status_code, 200)

        # Second attempt with the same code must fail
        second_confirm = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "phone": self.member.phone,
                "code": dev_code,
                "new_password": "anotherpass123",
            },
            format="json",
        )
        self.assertEqual(second_confirm.status_code, 400)
        data = second_confirm.json()
        self.assertIn("code", data)
        self.assertEqual(data["code"], ["Неверный или просроченный код."])


class AdminResetMemberPasswordAPITests(TestCase):
    """Tests for admin-only member password reset endpoint."""

    def setUp(self):
        self.client = APIClient()

        self.admin = Member(
            first_name="Admin",
            last_name="User",
            phone="+79990003333",
            email="admin@example.com",
            is_influencer=False,
            is_admin=True,
        )
        self.admin.set_password("adminpass123")
        self.admin.save()

        self.member = Member(
            first_name="Target",
            last_name="User",
            phone="+79990004444",
            email="target@example.com",
            is_influencer=False,
            is_admin=False,
        )
        self.member.set_password("userold123")
        self.member.save()

        token = MemberAuthToken.create_for_member(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_admin_reset_with_provided_password(self):
        url = f"/api/admin/members/{self.member.id}/reset-password/"
        new_password = "AdminNew123"

        response = self.client.post(
            url,
            {"new_password": new_password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data.get("detail"),
            "Пароль пользователя успешно сброшен администратором.",
        )
        self.assertEqual(data.get("generated_password"), new_password)

        # Login with new password should succeed
        login_client = APIClient()
        login_response_new = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": new_password},
            format="json",
        )
        self.assertEqual(login_response_new.status_code, 200)

        # Old password should fail
        login_response_old = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": "userold123"},
            format="json",
        )
        self.assertEqual(login_response_old.status_code, 400)

    def test_admin_reset_with_generated_password(self):
        url = f"/api/admin/members/{self.member.id}/reset-password/"

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        generated_password = data.get("generated_password")

        self.assertIsNotNone(generated_password)
        self.assertGreaterEqual(len(generated_password), 6)

        # Login with generated password should succeed
        login_client = APIClient()
        login_response = login_client.post(
            "/api/auth/login/",
            {"phone": self.member.phone, "password": generated_password},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

    def test_admin_reset_forbidden_for_non_admin(self):
        non_admin = Member(
            first_name="Regular",
            last_name="User",
            phone="+79990005555",
            email="regular@example.com",
            is_influencer=False,
            is_admin=False,
        )
        non_admin.set_password("regular123")
        non_admin.save()

        token = MemberAuthToken.create_for_member(non_admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = f"/api/admin/members/{self.member.id}/reset-password/"
        response = client.post(url, {"new_password": "SomePass123"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_reset_member_not_found(self):
        url = "/api/admin/members/999999/reset-password/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data.get("detail"), "Пользователь не найден.")
