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
        If the code is invalid or no longer exists, registration proceeds
        without linking to a referrer.
        """
        referral_code = attrs.get("referral_code") or ""
        if referral_code:
            try:
                referrer = Member.objects.get(referral_code=referral_code)
            except Member.DoesNotExist:
                # Invalid or outdated codes are ignored to avoid blocking
                # registration. The member will simply be created without
                # a referrer.
                return attrs
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

    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        if not phone or not password:
            raise serializers.ValidationError(
                "Необходимо указать номер телефона и пароль."
            )

        try:
            member = Member.objects.get(phone=phone)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                "Неверный номер телефона или пароль."
            )

        if not member.check_password(password):
            raise serializers.ValidationError(
                "Неверный номер телефона или пароль."
            )

        attrs["member"] = member
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing the current member password."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value: str) -> str:
        request = self.context.get("request")
        member = getattr(request, "user", None) if request is not None else None

        if not isinstance(member, Member):
            raise serializers.ValidationError(
                "Не удалось определить текущего пользователя."
            )

        if not member.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")

        return value

    def validate_new_password(self, value: str) -> str:
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset code by email or phone.""" 

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    phone = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        email_is_empty = not email or (isinstance(email, str) and email.strip() == "")
        phone_is_empty = not phone or (isinstance(phone, str) and phone.strip() == "")

        if email_is_empty and phone_is_empty:
            raise serializers.ValidationError(
                {"non_field_errors": ["Необходимо указать email или номер телефона."]}
            )

        member = None
        if not email_is_empty:
            member = Member.objects.filter(email=email).first()

        if member is None and not phone_is_empty:
            member = Member.objects.filter(phone=phone).first()

        if member is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Пользователь с таким email/телефоном не найден."]}
            )

        attrs["member"] = member
        return attrs

    def create(self, validated_data):
        member: Member = validated_data["member"]

        # Mark all previous unused codes for this member as used to prevent reuse.
        PasswordResetCode.objects.filter(
            member=member,
            is_used=False,
        ).update(is_used=True)

        code_length = 6
        digits = []
        for _ in range(code_length):
            digit = secrets.randbelow(10)
            digits.append(str(digit))
        code = "".join(digits)

        expires_at = timezone.now() + timedelta(minutes=15)

        reset_code = PasswordResetCode.objects.create(
            member=member,
            code=code,
            expires_at=expires_at,
        )
        return reset_code


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a reset code and setting a new password."""

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    phone = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        code = attrs.get("code")

        email_is_empty = not email or (isinstance(email, str) and email.strip() == "")
        phone_is_empty = not phone or (isinstance(phone, str) and phone.strip() == "")

        if email_is_empty and phone_is_empty:
            raise serializers.ValidationError(
                {"non_field_errors": ["Необходимо указать email или номер телефона."]}
            )

        member = None
        if not email_is_empty:
            member = Member.objects.filter(email=email).first()

        if member is None and not phone_is_empty:
            member = Member.objects.filter(phone=phone).first()

        if member is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Пользователь с таким email/телефоном не найден."]}
            )

        reset_code = (
            PasswordResetCode.objects.filter(
                member=member,
                code=code,
                is_used=False,
                expires_at__gte=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if reset_code is None:
            raise serializers.ValidationError(
                {"code": ["Неверный или просроченный код."]}
            )

        attrs["member"] = member
        attrs["reset_code"] = reset_code
        return attrs

    def validate_new_password(self, value: str) -> str:
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value


class MeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating the current member's profile and payout details."""

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "withdrawal_bank_details",
            "withdrawal_crypto_wallet",
        ]

    def validate_email(self, value: str) -> str:
        if not value:
            return value
        member = self.instance
        qs = Member.objects.filter(email=value)
        if member is not None:
            qs = qs.exclude(pk=member.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Пользователь с такой электронной почтой уже существует."
            )
        return value


class ReferralHistoryItemSerializer(serializers.Serializer):
    """Single item for referral history list."""

    date = serializers.DateField()
    referred_name = serializers.CharField()
    bonus_amount = serializers.IntegerField()
    money_amount = serializers.IntegerField()


class RegistrationsChartPointSerializer(serializers.Serializer):
    """Chart point: registrations per day."""

    date = serializers.DateField()
    count = serializers.IntegerField()


class PlayerDepositHistoryItemSerializer(serializers.Serializer):
    """Single item for a player's own deposit history.""" 

    date = serializers.DateField()
    amount = serializers.IntegerField()


class ProfileStatsSerializer(serializers.Serializer):
    """Aggregated profile statistics for a member.

    active_referrals is defined as referrals created within the last 30 days.
    """

    total_referrals = serializers.IntegerField()
    active_referrals = serializers.IntegerField()
    total_bonus_points = serializers.IntegerField()
    total_money_earned = serializers.IntegerField()
    history = ReferralHistoryItemSerializer(many=True)
    registrations_chart = RegistrationsChartPointSerializer(many=True)
    my_deposits_total_amount = serializers.IntegerField()
    my_deposits_count = serializers.IntegerField()
    my_deposits = PlayerDepositHistoryItemSerializer(many=True)


class ReferralNodeSerializer(serializers.Serializer):
    """Serializer for a single descendant in the ranked referral tree.

    Based on ReferralRelation entries for a given ancestor.
    """

    descendant_id = serializers.IntegerField()
    level = serializers.IntegerField()
    has_paid_first_bonus = serializers.BooleanField()
    username = serializers.CharField()
    user_type = serializers.CharField()
    rank = serializers.CharField()
    is_active_referral = serializers.BooleanField()


class ReferralRewardSerializer(serializers.ModelSerializer):
    """Serializer for individual referral rewards."""

    source_member_name = serializers.CharField(
        source="source_member.phone",
        read_only=True,
    )

    class Meta:
        model = ReferralReward
        fields = [
            "id",
            "reward_type",
            "amount_rub",
            "stack_count",
            "depth",
            "created_at",
            "source_member",
            "source_member_name",
        ]


class ReferralRewardsSummarySerializer(serializers.Serializer):
    """Aggregated summary for referral rewards of a member."""

    total_stack_count = serializers.IntegerField()
    total_influencer_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_first_tournament_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_deposit_percent_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


# ============================
# Admin-facing serializers
# ============================


class AdminMemberSerializer(serializers.ModelSerializer):
    """Serializer for listing and managing members in the admin panel."""

    referred_by = MemberReferrerSerializer(read_only=True)
    total_referrals = serializers.SerializerMethodField()
    total_bonus_points = serializers.IntegerField(read_only=True)
    total_money_earned = serializers.IntegerField(read_only=True)

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
            "total_referrals",
            "total_bonus_points",
            "total_money_earned",
        ]
        read_only_fields = [
            "id",
            "referral_code",
            "referred_by",
            "created_at",
            "total_referrals",
            "total_bonus_points",
            "total_money_earned",
        ]

    def get_total_referrals(self, obj: Member) -> int:
        return ReferralEvent.objects.filter(referrer=obj).count()


class AdminCreateMemberSerializer(serializers.ModelSerializer):
    """Serializer for creating members (including influencers/admins) via admin panel."""

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Member
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "password",
            "is_influencer",
            "is_admin",
        ]
        read_only_fields = ["id"]

    def validate_phone(self, value: str) -> str:
        if Member.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким номером телефона уже существует."
            )
        return value

    def validate_email(self, value: str) -> str:
        if not value:
            return value
        if Member.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с такой электронной почтой уже существует."
            )
        return value

    def create(self, validated_data: dict) -> Member:
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
            is_influencer=validated_data.get("is_influencer", False),
            is_admin=validated_data.get("is_admin", False),
        )
        member.set_password(raw_password)
        member.save()
        return member


class AdminResetMemberPasswordSerializer(serializers.Serializer):
    """Serializer for admin-initiated member password reset.

    new_password is optional; if not provided or empty, a random password
    will be generated by the view.
    """

    new_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate_new_password(self, value: str) -> str:
        if value is None or value == "":
            return value
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value


class ReferralEventAdminSerializer(serializers.ModelSerializer):
    """Serializer for referral events listing in the admin panel."""

    referrer = serializers.SerializerMethodField()
    referred = serializers.SerializerMethodField()
    referrer_is_influencer = serializers.SerializerMethodField()

    class Meta:
        model = ReferralEvent
        fields = [
            "id",
            "referrer",
            "referred",
            "bonus_amount",
            "money_amount",
            "deposit_amount",
            "created_at",
            "referrer_is_influencer",
        ]

    def _member_to_dict(self, member: Member) -> dict:
        return {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "is_influencer": member.is_influencer,
        }

    def get_referrer(self, obj: ReferralEvent) -> dict:
        return self._member_to_dict(obj.referrer)

    def get_referred(self, obj: ReferralEvent) -> dict:
        return self._member_to_dict(obj.referred)

    def get_referrer_is_influencer(self, obj: ReferralEvent) -> bool:
        return bool(obj.referrer.is_influencer)


class AdminCreateReferralEventSerializer(serializers.Serializer):
    """Serializer for creating referral/deposit events from the admin panel.

    This serializer records a concrete deposit (stack/rebuy) for a referred member
    and applies business rules for the ranked referral system.

    - For the first qualifying tournament/deposit of a referred member,
      `on_user_first_tournament_completed` is called once to distribute deep
      one-time bonuses in V-Coins/₽ across the referral tree.
    - For every deposit, `on_member_deposit` is called to apply the lifetime
      10% commission to the direct influencer referrer (if any).
    """

    referred_id = serializers.IntegerField(help_text="ID приглашённого игрока (Member.id).")
    deposit_amount = serializers.IntegerField(
        min_value=1,
        help_text=(
            "Сумма депозита в рублях за конкретный стек/ребай. Типичный размер стека — 1000 ₽, "
            "но можно указать любую положительную сумму."
        ),
        error_messages={
            "min_value": (
                "Сумма депозита должна быть не менее 1 рубля. Типичный размер стека — 1000 ₽."
            ),
        },
    )
    created_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text=(
            "Необязательная дата и время события. Если не указано, будет использовано текущее время."
        ),
    )

    def validate(self, attrs):
        referred_id = attrs.get("referred_id")
        try:
            referred = Member.objects.get(pk=referred_id)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"referred_id": "Пользователь с указанным ID не найден."}
            )

        # For new logic we prefer the explicit `referrer` field, but for
        # backward compatibility we also accept legacy `referred_by`.
        referrer = referred.referrer or referred.referred_by
        if referrer is None:
            raise serializers.ValidationError(
                {
                    "referred_id": (
                        "Для этого пользователя не записан реферер, невозможно создать реферальное событие."
                    )
                }
            )

        attrs["referred"] = referred
        return attrs

    def create(self, validated_data):
        referred: Member = validated_data["referred"]
        deposit_amount: int = validated_data["deposit_amount"]
        created_at = validated_data.get("created_at") or timezone.now()

        event = process_member_deposit(referred, deposit_amount, created_at=created_at)
        return event


class AdminRegistrationsByDaySerializer(serializers.Serializer):
    """Single item for registrations by day on admin dashboard.""" 

    date = serializers.DateField()
    count = serializers.IntegerField()


class AdminTopReferrerSerializer(serializers.Serializer):
    """Top referrer item for admin dashboard.

    Aggregated by ReferralEvent.
    """

    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_influencer = serializers.BooleanField()
    total_referrals = serializers.IntegerField()
    total_bonus_points = serializers.IntegerField()
    total_money_earned = serializers.IntegerField()


class AdminIncomeBySourceSerializer(serializers.Serializer):
    """Income breakdown for admin dashboard."""

    total_income = serializers.IntegerField()
    income_from_influencers = serializers.IntegerField()
    income_from_regular_users = serializers.IntegerField()


class AdminStatsOverviewSerializer(serializers.Serializer):
    """Aggregated statistics for admin dashboard.

    Used by React-админка для отображения общей статистики:
    - регистрации по дням,
    - топ рефереров,
    - доход по источникам.
    """

    registrations_by_day = AdminRegistrationsByDaySerializer(many=True)
    top_referrers = AdminTopReferrerSerializer(many=True)
    income_by_source = AdminIncomeBySourceSerializer()


# ============================
# Test-only serializers
# ============================


class TestReferralChangeSerializer(serializers.Serializer):
    """Single activated ancestor/descendant relation after a simulated deposit.""" 

    ancestor_id = serializers.IntegerField()
    level = serializers.IntegerField()


class TestMemberDepositResultSerializer(serializers.Serializer):
    """Result of a simulated deposit for a single member."""

    member = MemberSerializer()
    amount = serializers.IntegerField()
    v_coins_balance_before = serializers.DecimalField(max_digits=12, decimal_places=2)
    cash_balance_before = serializers.DecimalField(max_digits=12, decimal_places=2)
    v_coins_balance_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    cash_balance_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    referral_changes = TestReferralChangeSerializer(many=True)


class TestSimulateDepositsResponseSerializer(serializers.Serializer):
    """Response schema for the test simulate-deposits endpoint."""

    status = serializers.CharField()
    deposits = TestMemberDepositResultSerializer(many=True)


class SimulateDemoDepositsRequestSerializer(serializers.Serializer):
    """Request payload for demo deposits simulation for Amir and Alfirа."""

    amount = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            "Сумма депозита в рублях для каждого игрока. По умолчанию 2000."
        ),
        error_messages={
            "min_value": "Сумма депозита должна быть положительным числом.",
        },
    )


class SimulateDemoDepositsPlayerDepositSerializer(serializers.Serializer):
    """Single deposit summary for a demo player."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class SimulateDemoDepositsPlayerSerializer(serializers.Serializer):
    """Player (Амир or Альфира) with associated demo deposits."""

    member_id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    deposits = SimulateDemoDepositsPlayerDepositSerializer(many=True)


class SimulateDemoDepositsTimurSerializer(serializers.Serializer):
    """Timur earnings summary for the demo deposits scenario."""

    member_id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    cash_balance_before = serializers.DecimalField(max_digits=12, decimal_places=2)
    cash_balance_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    earnings_delta = serializers.DecimalField(max_digits=12, decimal_places=2)


class SimulateDemoDepositsResponseSerializer(serializers.Serializer):
    """Response schema for the demo deposits simulation endpoint."""

    players = SimulateDemoDepositsPlayerSerializer(many=True)
    timur = SimulateDemoDepositsTimurSerializer()
