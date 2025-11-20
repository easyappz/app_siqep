from rest_framework import serializers

from .models import Member, ReferralEvent


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
        """Создать нового участника (Member) и применить реферальную бизнес-логику.

        Правила на момент регистрации (первое посещение / первый стек):
        - Всегда создаётся ReferralEvent с deposit_amount = 1000 (первый стартовый стек).
        - Если referrer.is_influencer == False (обычный игрок клуба):
          * он получает немонетарное вознаграждение — один бесплатный стек (1000 ₽);
          * это отражается как bonus_amount = 1, а суммарный счётчик Member.total_bonus_points
            увеличивается на 1;
          * money_amount = 0.
        - Если referrer.is_influencer == True (инфлюенсер):
          * он получает денежное вознаграждение в размере 1000 ₽ за первое участие
            приглашённого игрока (первый стек);
          * это отражается как money_amount = 1000, а Member.total_money_earned
            увеличивается на 1000;
          * bonus_amount = 0.

        В будущем для инфлюенсеров будет добавлена отдельная логика начисления 10% от
        последующих депозитов (через отдельный эндпоинт/события). В данном методе
        обрабатывается только первый стек при регистрации.
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
            # Защита от гипотетической саморефералки (на практике невозможна при регистрации).
            if referrer.id == member.id:
                raise serializers.ValidationError(
                    "Пользователь не может использовать собственный реферальный код."
                )

            member.referred_by = referrer
            member.save(update_fields=["referred_by"])

            deposit_amount = 1000
            if referrer.is_influencer:
                bonus_amount = 0
                money_amount = 1000
                referrer.total_money_earned += money_amount
            else:
                bonus_amount = 1
                money_amount = 0
                referrer.total_bonus_points += bonus_amount

            referrer.save(update_fields=["total_bonus_points", "total_money_earned"])

            ReferralEvent.objects.create(
                referrer=referrer,
                referred=member,
                bonus_amount=bonus_amount,
                money_amount=money_amount,
                deposit_amount=deposit_amount,
            )

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
