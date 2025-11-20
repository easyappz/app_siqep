from django.utils import timezone
from rest_framework import serializers

from .models import Member, ReferralEvent, ReferralReward
from .referral_utils import (
    create_player_stack_rewards_for_new_member,
    create_influencer_deposit_rewards,
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
    """Serializer for public member profile data."""

    referred_by = MemberReferrerSerializer(read_only=True)

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
        ]
        read_only_fields = [
            "id",
            "is_influencer",
            "is_admin",
            "referral_code",
            "referred_by",
            "created_at",
        ]


class RegistrationSerializer(serializers.Serializer):
    """Serializer used for public registration endpoint.

    Creates a new Member and optionally links it to a referrer by referral_code.

    When a new member is successfully registered with a referrer, the following
    business logic is applied:
    - The direct referrer receives a ReferralEvent with a fixed deposit_amount
      (1000 ₽ – стартовый стек) for backward-compatible analytics.
    - All ancestors in the referral chain (including the direct referrer) receive
      one free starting stack via ReferralReward with type PLAYER_STACK. This
      works for arbitrary depth of the referral tree.
    - Monetary rewards for influencers (1000 ₽ за первый турнир и 10% от
      дальнейших депозитов) are created later when concrete deposit events are
      recorded via the admin deposit endpoint.
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

        - The direct referrer receives a ReferralEvent with deposit_amount = 1000.
        - All ancestors in the chain receive a PLAYER_STACK ReferralReward
          (1 free starting stack) with depth starting from 1 for the direct
          referrer, 2 for the next level, and so on.
        - Influencer monetary rewards are generated later from concrete deposit
          events (AdminCreateReferralEventSerializer).
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

            member.referred_by = referrer
            member.save(update_fields=["referred_by"])

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

            # New deep referral logic: stacks for all ancestors.
            create_player_stack_rewards_for_new_member(member)

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
    """Serializer for a single node in the referral tree."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    is_influencer = serializers.BooleanField()
    depth = serializers.IntegerField()
    direct_referrals_count = serializers.IntegerField()
    total_descendants_count = serializers.IntegerField()


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
    and applies business rules for influencers vs regular players.

    For influencers in the referral chain, deep multi-level rewards are generated
    via ReferralReward:
    - 1000 ₽ за первый турнир реферала (тип INFLUENCER_FIRST_TOURNAMENT);
    - 10% со всех дальнейших депозитов (тип INFLUENCER_DEPOSIT_PERCENT).
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

        if referred.referred_by is None:
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
        referrer: Member = referred.referred_by

        deposit_amount: int = validated_data["deposit_amount"]
        created_at = validated_data.get("created_at") or timezone.now()

        # For analytics and compatibility we still store a ReferralEvent record,
        # but all deep influencer rewards are handled by ReferralReward.
        event = ReferralEvent.objects.create(
            referrer=referrer,
            referred=referred,
            bonus_amount=0,
            money_amount=0,
            deposit_amount=deposit_amount,
            created_at=created_at,
        )

        # Deep influencer rewards (first tournament + 10% of further deposits).
        create_influencer_deposit_rewards(
            source_member=referred,
            deposit_amount=deposit_amount,
            event_time=created_at,
        )

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
