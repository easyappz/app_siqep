from django.utils import timezone
from rest_framework import serializers

from .models import Member, ReferralEvent, ReferralReward, ReferralRelation, RankRule
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


class MemberSerializer(serializers.ModelSerializer):
    """Serializer for public member profile data with ranked referral fields."""

    referred_by = MemberReferrerSerializer(read_only=True)
    direct_referrals_count = serializers.SerializerMethodField()
    active_direct_referrals_count = serializers.SerializerMethodField()
    current_rank_rule = serializers.SerializerMethodField()

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
            "direct_referrals_count",
            "active_direct_referrals_count",
            "current_rank_rule",
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
            "direct_referrals_count",
            "active_direct_referrals_count",
            "current_rank_rule",
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
