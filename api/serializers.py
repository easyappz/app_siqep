from datetime import timedelta
import secrets

from django.utils import timezone
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    Member,
    ReferralEvent,
    ReferralReward,
    ReferralRelation,
    RankRule,
    Deposit,
    WithdrawalRequest,
    PasswordResetCode,
    WalletTransaction,
)
from .referral_utils import (
    on_new_user_registered,
    process_member_deposit,
)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200)
    timestamp = serializers.DateTimeField(read_only=True)


class MemberReferrerSerializer(serializers.ModelSerializer):
    """Minimal serializer for referrer information."""

    class Meta:
        model = Member
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "referral_code",
        ]


class DepositSerializer(serializers.ModelSerializer):
    """Serializer for individual deposits of a member."""

    class Meta:
        model = Deposit
        fields = [
            "id",
            "amount",
            "currency",
            "is_test",
            "created_at",
        ]
        read_only_fields = fields


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal requests of a member."""

    class Meta:
        model = WithdrawalRequest
        fields = [
            "id",
            "amount",
            "method",
            "destination",
            "status",
            "created_at",
            "processed_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "processed_at",
        ]

    def validate_amount(self, value):
        """Ensure amount is positive and does not exceed available balance."""

        if value <= 0:
            raise serializers.ValidationError(
                "Сумма вывода должна быть положительным числом."
            )

        request = self.context.get("request")
        member = getattr(request, "user", None)

        if isinstance(member, Member):
            available = member.available_for_withdrawal
            if value > available:
                raise serializers.ValidationError(
                    "Сумма вывода превышает доступный баланс для вывода."
                )

        return value


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for individual wallet transactions."""

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "type",
            "amount",
            "balance_after",
            "description",
            "meta",
            "created_at",
        ]
        read_only_fields = fields


class WalletSummarySerializer(serializers.Serializer):
    """Aggregated wallet summary for a member."""

    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deposited = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)


class WalletDepositRequestSerializer(serializers.Serializer):
    """Input serializer for wallet deposit operation."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Сумма пополнения должна быть положительным числом."
            )
        return value


class WalletSpendRequestSerializer(serializers.Serializer):
    """Input serializer for wallet spend operation.""" 

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Сумма списания должна быть положительным числом."
            )
        return value


class MemberSerializer(serializers.ModelSerializer):
    """Serializer for public member profile data with ranked referral fields."""

    referred_by = MemberReferrerSerializer(read_only=True)
    direct_referrals_count = serializers.SerializerMethodField()
    active_direct_referrals_count = serializers.SerializerMethodField()
    current_rank_rule = serializers.SerializerMethodField()
    total_deposits = serializers.SerializerMethodField()
    total_influencer_earnings = serializers.SerializerMethodField()
    deposits = DepositSerializer(many=True, read_only=True)
    referred_members_count = serializers.SerializerMethodField()
    available_for_withdrawal = serializers.SerializerMethodField()
    last_withdrawal_request = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()
    wallet_total_deposited = serializers.SerializerMethodField()
    wallet_total_spent = serializers.SerializerMethodField()
    # Ensure referral_code is always present and backfilled if missing
    referral_code = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "is_influencer",
            "is_admin",
            "referral_code",
            "referred_by",
            "created_at",
            # Ranked referral system fields
            "user_type",
            "rank",
            "v_coins_balance",
            "cash_balance",
            "wallet_balance",
            "wallet_total_deposited",
            "wallet_total_spent",
            "direct_referrals_count",
            "active_direct_referrals_count",
            "current_rank_rule",
            "withdrawal_bank_details",
            "withdrawal_crypto_wallet",
            # Deposit and earnings aggregates
            "total_deposits",
            "total_influencer_earnings",
            "deposits",
            "referred_members_count",
            "available_for_withdrawal",
            "last_withdrawal_request",
        ]
        read_only_fields = [
            "id",
            "is_influencer",
            "is_admin",
            "referral_code",
            "referred_by",
            "created_at",
            "user_type",
            "rank",
            "v_coins_balance",
            "cash_balance",
            "wallet_balance",
            "wallet_total_deposited",
            "wallet_total_spent",
            "direct_referrals_count",
            "active_direct_referrals_count",
            "current_rank_rule",
            "withdrawal_bank_details",
            "withdrawal_crypto_wallet",
            "total_deposits",
            "total_influencer_earnings",
            "deposits",
            "referred_members_count",
            "available_for_withdrawal",
            "last_withdrawal_request",
        ]

    def get_direct_referrals_count(self, obj: Member) -> int:
        """Number of unique level-1 referrals for the member in the ranked system."""
        return (
            ReferralRelation.objects.filter(ancestor=obj, level=1)
            .values("descendant_id")
            .distinct()
            .count()
        )

    def get_active_direct_referrals_count(self, obj: Member) -> int:
        """Number of active level-1 referrals (has_paid_first_bonus=True)."""
        return (
            ReferralRelation.objects.filter(
                ancestor=obj,
                level=1,
                has_paid_first_bonus=True,
            )
            .values("descendant_id")
            .distinct()
            .count()
        )

    def get_current_rank_rule(self, obj: Member):
        """Return the RankRule configuration for the member's current rank."""
        if not obj.rank:
            return None
        try:
            rule = RankRule.objects.get(rank=obj.rank)
        except RankRule.DoesNotExist:
            return None
        return {
            "required_referrals": rule.required_referrals,
            "player_depth_bonus_multiplier": rule.player_depth_bonus_multiplier,
            "influencer_depth_bonus_multiplier": rule.influencer_depth_bonus_multiplier,
        }

    def get_total_deposits(self, obj: Member):
        """Return the total deposits amount for the member as a decimal string."""
        total = getattr(obj, "total_deposits", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_total_influencer_earnings(self, obj: Member):
        """Return the total influencer earnings for the member as a decimal string."""
        total = getattr(obj, "total_influencer_earnings", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_referred_members_count(self, obj: Member) -> int:
        """Return count of direct referred members (level 1)."""
        return self.get_direct_referrals_count(obj)

    def get_available_for_withdrawal(self, obj: Member) -> str:
        """Return available influencer earnings for withdrawal as a decimal string."""
        available = getattr(obj, "available_for_withdrawal", None)
        if available is None:
            return "0.00"
        return str(available)

    def get_last_withdrawal_request(self, obj: Member):
        """Return the latest withdrawal request data for the member, if any."""
        request_obj = obj.withdrawal_requests.order_by("-created_at").first()
        if request_obj is None:
            return None
        return WithdrawalRequestSerializer(request_obj).data

    def get_wallet_balance(self, obj: Member) -> str:
        """Return current wallet balance (aliased to cash_balance) as string."""

        balance = getattr(obj, "wallet_balance", None)
        if balance is None:
            return "0.00"
        return str(balance)

    def get_wallet_total_deposited(self, obj: Member) -> str:
        """Total amount ever deposited into the member's wallet."""

        total = (
            obj.wallet_transactions.filter(
                type=WalletTransaction.Type.DEPOSIT,
            ).aggregate(total=Sum("amount"))["total"]
        )
        if total is None:
            return "0.00"
        return str(total)

    def get_wallet_total_spent(self, obj: Member) -> str:
        """Total amount ever spent or withdrawn from the member's wallet."""

        total = (
            obj.wallet_transactions.filter(
                type__in=[
                    WalletTransaction.Type.SPEND,
                    WalletTransaction.Type.WITHDRAW,
                ],
            ).aggregate(total=Sum("amount"))["total"]
        )
        if total is None:
            return "0.00"
        return str(total)

    def get_referral_code(self, obj: Member) -> str:
        """Return a stable, non-empty referral code for the member.

        If the stored referral_code is missing (for legacy records), a new code
        is generated using Member.generate_referral_code(), saved, and then
        returned. This guarantees that influencers always see a shareable
        referral code in their profile, and regular players also have a code
        available if needed.
        """

        code = getattr(obj, "referral_code", None)
        if code:
            return code

        # Backfill missing code safely for existing members.
        if not getattr(obj, "pk", None):
            return ""

        try:
            new_code = obj.generate_referral_code()
            obj.referral_code = new_code
            obj.save(update_fields=["referral_code"])
            return new_code or ""
        except Exception:
            # In case of an unexpected error (e.g. integrity issue), do not
            # break the whole profile response.
            return ""


class RegistrationSerializer(serializers.Serializer):
    """Serializer used for public registration endpoint.

    Creates a new Member and optionally links it to a referrer by referral_code.

    When a new member is successfully registered with a referrer, the following
    business logic is applied (new ranked referral system):
    - The direct referrer receives a ReferralEvent with a fixed deposit_amount
      (1000 ₽ – стартовый стек) for backward-compatible analytics.
    - The ranked referral tree (ReferralRelation) is built via
      `on_new_user_registered`, so that first-tournament logic can later
      distribute V-Coins/₽ rewards in depth.
    - Monetary and V-Coins rewards are *not* granted at registration time.
      They are granted when the new member completes their first paid
      tournament / qualifying deposit via `on_user_first_tournament_completed`.
    """

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value: str) -> str:
        """Ensure phone is unique with a Russian error message."""
        if Member.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким номером телефона уже существует."
            )
        return value

    def validate_email(self, value: str) -> str:
        """Ensure email is unique (if provided) with a Russian error message."""
        if not value:
            return value
        if Member.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с такой электронной почтой уже существует."
            )
        return value

    def validate_password(self, value: str) -> str:
        """Basic password validation without regular expressions."""
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value

    def validate(self, attrs):
        """Validate referral_code if provided and resolve referrer Member.

        Stores resolved referrer in attrs["referrer"] for later use in create().
        """
        referral_code = attrs.get("referral_code") or ""
        if referral_code:
            try:
                referrer = Member.objects.get(referral_code=referral_code)
            except Member.DoesNotExist:
                raise serializers.ValidationError(
                    {"referral_code": "Указанный реферальный код не найден."}
                )
            attrs["referrer"] = referrer
        return attrs

    def create(self, validated_data: dict) -> Member:
        """Create a new Member and apply referral business logic.

        - The direct referrer receives a ReferralEvent with deposit_amount = 1000
          (для статистики и обратной совместимости).
        - The deep referral tree is constructed via `on_new_user_registered`.
        - Финансовые бонусы (V-Coins/₽) начисляются позже, когда реферал
          завершает свой первый платный турнир/депозит.
        """

        referrer = validated_data.pop("referrer", None)
        # Remove non-model fields
        validated_data.pop("referral_code", None)
        raw_password = validated_data.pop("password")

        # Normalize empty email to None
        email = validated_data.get("email")
        if email == "":
            validated_data["email"] = None

        member = Member(
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
            email=validated_data.get("email"),
        )
        member.set_password(raw_password)
        member.save()

        if referrer is not None:
            # Safety check against hypothetical self-referral.
            if referrer.id == member.id:
                raise serializers.ValidationError(
                    "Пользователь не может использовать собственный реферальный код."
                )

            # Keep legacy field and new referrer field in sync.
            member.referred_by = referrer
            member.referrer = referrer
            member.save(update_fields=["referred_by", "referrer"])

            deposit_amount = 1000
            if referrer.is_influencer:
                bonus_amount = 0
                money_amount = deposit_amount
            else:
                bonus_amount = 1
                money_amount = 0

            # Keep ReferralEvent for analytics and backward-compatible admin views.
            ReferralEvent.objects.create(
                referrer=referrer,
                referred=member,
                bonus_amount=bonus_amount,
                money_amount=money_amount,
                deposit_amount=deposit_amount,
            )

            # New referral graph for ranked system.
            on_new_user_registered(member)

        return member


class LoginSerializer(serializers.Serializer):
    """Serializer used for login by phone and password."""


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer used for changing password of the authenticated Member."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        member = getattr(request, "user", None) if request is not None else None

        if not isinstance(member, Member):
            raise serializers.ValidationError(
                "Не удалось определить текущего пользователя."
            )

        old_password = attrs.get("old_password", "")
        new_password = attrs.get("new_password", "")

        if not member.check_password(old_password):
            raise serializers.ValidationError(
                {"old_password": "Текущий пароль указан неверно."}
            )

        if len(new_password) < 6:
            raise serializers.ValidationError(
                {"new_password": "Пароль должен содержать не менее 6 символов."}
            )

        if old_password == new_password:
            raise serializers.ValidationError(
                {"new_password": "Новый пароль не должен совпадать с текущим паролем."}
            )

        return attrs
