from datetime import timedelta
import secrets
from decimal import Decimal

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
    ReferralBonus,
    AdminBalanceOperation,
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


class ReferralDepositSerializer(serializers.ModelSerializer):
    """Serializer for deposits made by referrals of the current member."""

    member = MemberReferrerSerializer(read_only=True)

    class Meta:
        model = Deposit
        fields = [
            "id",
            "member",
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


class WalletAdminDebitSerializer(serializers.Serializer):
    """Input serializer for admin-initiated wallet debits."""

    member_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        member_id = attrs.get("member_id")
        amount = attrs.get("amount")

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"member_id": "Пользователь с таким ID не найден."}
            )

        if amount is None or amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Сумма списания должна быть положительным числом."}
            )

        balance = member.get_balance()
        if balance < amount:
            raise serializers.ValidationError(
                {"amount": "Недостаточно средств на балансе пользователя для списания."}
            )

        attrs["member"] = member
        return attrs

    def create(self, validated_data):
        member: Member = validated_data["member"]
        amount = validated_data["amount"]
        reason = validated_data.get("reason") or ""

        request = self.context.get("request")
        admin = getattr(request, "user", None) if request is not None else None

        try:
            tx = member.admin_debit(
                amount=amount,
                reason=reason,
                admin=admin,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"amount": [str(exc)]})

        return tx


class WalletAdminDepositSerializer(serializers.Serializer):
    """Input serializer for admin-initiated wallet deposits."""

    member_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        member_id = attrs.get("member_id")
        amount = attrs.get("amount")

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"member_id": "Пользователь с таким ID не найден."}
            )

        if amount is None or amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Сумма пополнения должна быть положительным числом."}
            )

        attrs["member"] = member
        return attrs

    def create(self, validated_data):
        member: Member = validated_data["member"]
        amount = validated_data["amount"]
        reason = validated_data.get("reason") or ""

        try:
            tx = member.deposit(
                amount=amount,
                description=reason,
                meta={"source": "admin_deposit"},
            )
        except ValueError as exc:
            raise serializers.ValidationError({"amount": [str(exc)]})

        return tx


class WalletAdminSpendSerializer(serializers.Serializer):
    """Input serializer for admin-initiated wallet spends (simulated player spend)."""

    member_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        member_id = attrs.get("member_id")
        amount = attrs.get("amount")

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"member_id": "Пользователь с таким ID не найден."}
            )

        if amount is None or amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Сумма списания должна быть положительным числом."}
            )

        attrs["member"] = member
        return attrs

    def create(self, validated_data):
        member: Member = validated_data["member"]
        amount = validated_data["amount"]
        description = validated_data.get("description") or ""
        category = validated_data.get("category") or ""

        meta = {"source": "admin_spend"}
        if category:
            meta["category"] = category

        try:
            tx = member.spend(
                amount=amount,
                description=description,
                meta=meta,
            )
        except ValueError as exc:
            message = str(exc)
            if "Insufficient wallet balance" in message:
                raise serializers.ValidationError(
                    {"amount": ["Недостаточно средств на кошельке пользователя."]}
                )
            raise serializers.ValidationError({"amount": [message]})

        return tx


class ReferralBonusSerializer(serializers.ModelSerializer):
    """Serializer for referral bonuses created on wallet spend events."""

    referred_member = MemberReferrerSerializer(read_only=True)
    spend_transaction_id = serializers.IntegerField(
        source="spend_transaction_id",
        read_only=True,
    )
    spend_amount = serializers.DecimalField(
        source="spend_transaction.amount",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = ReferralBonus
        fields = [
            "id",
            "referred_member",
            "amount",
            "spend_transaction_id",
            "spend_amount",
            "created_at",
        ]
        read_only_fields = fields


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
        return (
            ReferralRelation.objects.filter(ancestor=obj, level=1)
            .values("descendant_id")
            .distinct()
            .count()
        )

    def get_active_direct_referrals_count(self, obj: Member) -> int:
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
        total = getattr(obj, "total_deposits", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_total_influencer_earnings(self, obj: Member):
        total = getattr(obj, "total_influencer_earnings", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_referred_members_count(self, obj: Member) -> int:
        return self.get_direct_referrals_count(obj)

    def get_available_for_withdrawal(self, obj: Member) -> str:
        available = getattr(obj, "available_for_withdrawal", None)
        if available is None:
            return "0.00"
        return str(available)

    def get_last_withdrawal_request(self, obj: Member):
        request_obj = obj.withdrawal_requests.order_by("-created_at").first()
        if request_obj is None:
            return None
        return WithdrawalRequestSerializer(request_obj).data

    def get_wallet_balance(self, obj: Member) -> str:
        balance = getattr(obj, "wallet_balance", None)
        if balance is None:
            return "0.00"
        return str(balance)

    def get_wallet_total_deposited(self, obj: Member) -> str:
        total = (
            obj.wallet_transactions.filter(
                type=WalletTransaction.Type.DEPOSIT,
            ).aggregate(total=Sum("amount"))["total"]
        )
        if total is None:
            return "0.00"
        return str(total)

    def get_wallet_total_spent(self, obj: Member) -> str:
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
        code = getattr(obj, "referral_code", None)
        if code:
            return code

        if not getattr(obj, "pk", None):
            return ""

        try:
            new_code = obj.generate_referral_code()
            obj.referral_code = new_code
            obj.save(update_fields=["referral_code"])
            return new_code or ""
        except Exception:
            return ""


class RegistrationSerializer(serializers.Serializer):
    """Serializer used for public registration endpoint."""

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(required=False, allow_blank=True)

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

    def validate_password(self, value: str) -> str:
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value

    def validate(self, attrs):
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
        referrer = validated_data.pop("referrer", None)
        validated_data.pop("referral_code", None)
        raw_password = validated_data.pop("password")

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
            if referrer.id == member.id:
                raise serializers.ValidationError(
                    "Пользователь не может использовать собственный реферальный код."
                )

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

            ReferralEvent.objects.create(
                referrer=referrer,
                referred=member,
                bonus_amount=bonus_amount,
                money_amount=money_amount,
                deposit_amount=deposit_amount,
            )

            on_new_user_registered(member)

        return member


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = (attrs.get("phone") or "").strip()
        password = attrs.get("password") or ""

        if not phone or not password:
            raise serializers.ValidationError(
                {"phone": "Неверный номер телефона или пароль."}
            )

        try:
            member = Member.objects.get(phone=phone)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"phone": "Неверный номер телефона или пароль."}
            )

        if not member.check_password(password):
            raise serializers.ValidationError(
                {"phone": "Неверный номер телефона или пароль."}
            )

        attrs["member"] = member
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
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


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        phone = (attrs.get("phone") or "").strip()
        email = (attrs.get("email") or "").strip()

        if not phone and not email:
            raise serializers.ValidationError(
                "Укажите номер телефона или электронную почту для сброса пароля."
            )

        member = None

        if phone:
            try:
                member = Member.objects.get(phone=phone)
            except Member.DoesNotExist:
                raise serializers.ValidationError(
                    {"phone": "Пользователь с таким номером телефона не найден."}
                )
        elif email:
            try:
                member = Member.objects.get(email=email)
            except Member.DoesNotExist:
                raise serializers.ValidationError(
                    {"email": "Пользователь с такой электронной почтой не найден."}
                )

        attrs["member"] = member
        return attrs

    def create(self, validated_data):
        member = validated_data["member"]

        PasswordResetCode.objects.filter(member=member, is_used=False).update(
            is_used=True
        )

        code = "".join(str(secrets.randbelow(10)) for _ in range(6))

        expires_at = timezone.now() + timedelta(minutes=15)

        reset_code = PasswordResetCode.objects.create(
            member=member,
            code=code,
            expires_at=expires_at,
        )

        return reset_code


class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=6,
        error_messages={
            "min_length": "Пароль должен содержать не менее 6 символов.",
            "blank": "Укажите новый пароль.",
        },
    )

    def validate(self, attrs):
        code = (attrs.get("code") or "").strip()

        if not code:
            raise serializers.ValidationError(
                {"code": "Укажите код для сброса пароля."}
            )

        now = timezone.now()
        try:
            reset_code = (
                PasswordResetCode.objects.filter(
                    code=code,
                    is_used=False,
                    expires_at__gt=now,
                )
                .select_related("member")
                .latest("created_at")
            )
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError(
                {"code": "Неверный или просроченный код для сброса пароля."}
            )

        attrs["member"] = reset_code.member
        attrs["reset_code"] = reset_code
        return attrs


class MeUpdateSerializer(serializers.ModelSerializer):
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

        qs = Member.objects.filter(email=value)
        instance = getattr(self, "instance", None)
        if instance is not None and instance.pk is not None:
            qs = qs.exclude(pk=instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Пользователь с такой электронной почтой уже существует."
            )
        return value

    def update(self, instance: Member, validated_data: dict) -> Member:
        email = validated_data.get("email", serializers.empty)
        if email is not serializers.empty:
            if email == "":
                instance.email = None
            else:
                instance.email = email

        first_name = validated_data.get("first_name", serializers.empty)
        if first_name is not serializers.empty:
            instance.first_name = first_name

        last_name = validated_data.get("last_name", serializers.empty)
        if last_name is not serializers.empty:
            instance.last_name = last_name

        bank_details = validated_data.get("withdrawal_bank_details", serializers.empty)
        if bank_details is not serializers.empty:
            instance.withdrawal_bank_details = bank_details

        crypto_wallet = validated_data.get("withdrawal_crypto_wallet", serializers.empty)
        if crypto_wallet is not serializers.empty:
            instance.withdrawal_crypto_wallet = crypto_wallet

        instance.save()
        return instance


# ============================
# Profile stats serializers
# ============================


class ReferralHistoryItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    referred_name = serializers.CharField()
    bonus_amount = serializers.IntegerField()
    money_amount = serializers.IntegerField()


class RegistrationsChartPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class PlayerDepositHistoryItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.IntegerField()


class LevelSummaryItemSerializer(serializers.Serializer):
    """Per-level referral summary item for profile stats."""

    level = serializers.IntegerField()
    total_referrals = serializers.IntegerField()
    active_referrals = serializers.IntegerField()


class ProfileStatsSerializer(serializers.Serializer):
    total_referrals = serializers.IntegerField()
    active_referrals = serializers.IntegerField()
    total_bonus_points = serializers.IntegerField()
    total_money_earned = serializers.IntegerField()
    history = ReferralHistoryItemSerializer(many=True)
    registrations_chart = RegistrationsChartPointSerializer(many=True)
    my_deposits_total_amount = serializers.IntegerField()
    my_deposits_count = serializers.IntegerField()
    my_deposits = PlayerDepositHistoryItemSerializer(many=True)
    referral_total_deposits_amount = serializers.IntegerField()
    referral_total_bonuses_amount = serializers.IntegerField()
    level_summary = LevelSummaryItemSerializer(many=True)


# ============================
# Referral tree and rewards serializers
# ============================


class ReferralNodeSerializer(serializers.Serializer):
    descendant_id = serializers.IntegerField()
    level = serializers.IntegerField()
    has_paid_first_bonus = serializers.BooleanField()
    username = serializers.CharField()
    user_type = serializers.ChoiceField(choices=["player", "influencer"])
    rank = serializers.ChoiceField(
        choices=["standard", "silver", "gold", "platinum"],
    )
    is_active_referral = serializers.BooleanField()


class ReferralRewardSerializer(serializers.ModelSerializer):
    source_member = serializers.IntegerField(source="source_member_id", read_only=True)
    source_member_name = serializers.SerializerMethodField()

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
        read_only_fields = fields

    def get_source_member_name(self, obj: ReferralReward) -> str:
        member = getattr(obj, "source_member", None)
        if member is None:
            return ""
        full_name = f"{member.first_name} {member.last_name}".strip()
        if full_name:
            return full_name
        return member.phone or ""


class ReferralRewardsSummarySerializer(serializers.Serializer):
    total_stack_count = serializers.IntegerField()
    total_influencer_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_first_tournament_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deposit_percent_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


# ============================
# Admin member serializers
# ============================


class AdminBalanceOperationSerializer(serializers.ModelSerializer):
    created_by = MemberReferrerSerializer(read_only=True)

    class Meta:
        model = AdminBalanceOperation
        fields = [
            "id",
            "operation_type",
            "deposit_change",
            "vcoins_change",
            "balance_deposit_after",
            "balance_vcoins_after",
            "comment",
            "created_at",
            "created_by",
        ]
        read_only_fields = fields


class AdminMemberSerializer(serializers.ModelSerializer):
    referred_by = MemberReferrerSerializer(read_only=True)
    total_referrals = serializers.SerializerMethodField()

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


class AdminMemberListSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    v_coins_balance = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

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
            "created_at",
            "wallet_balance",
            "v_coins_balance",
            "is_active",
        ]
        read_only_fields = fields

    def get_wallet_balance(self, obj: Member) -> str:
        balance = getattr(obj, "wallet_balance", None)
        if balance is None:
            return "0.00"
        return str(balance)

    def get_v_coins_balance(self, obj: Member) -> str:
        balance = getattr(obj, "v_coins_balance", None)
        if balance is None:
            return "0.00"
        return str(balance)

    def get_is_active(self, obj: Member) -> bool:
        wallet_balance = getattr(obj, "wallet_balance", Decimal("0.00"))
        v_coins = getattr(obj, "v_coins_balance", Decimal("0.00"))
        return bool(wallet_balance > Decimal("0.00") or v_coins > Decimal("0.00"))


class AdminMemberDetailSerializer(serializers.ModelSerializer):
    referred_by = MemberReferrerSerializer(read_only=True)
    total_deposits = serializers.SerializerMethodField()
    total_influencer_earnings = serializers.SerializerMethodField()
    available_for_withdrawal = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()
    operations = serializers.SerializerMethodField()

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
            "user_type",
            "rank",
            "v_coins_balance",
            "cash_balance",
            "wallet_balance",
            "total_deposits",
            "total_influencer_earnings",
            "available_for_withdrawal",
            "operations",
        ]
        read_only_fields = fields

    def get_total_deposits(self, obj: Member) -> str:
        total = getattr(obj, "total_deposits", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_total_influencer_earnings(self, obj: Member) -> str:
        total = getattr(obj, "total_influencer_earnings", None)
        if total is None:
            return "0.00"
        return str(total)

    def get_available_for_withdrawal(self, obj: Member) -> str:
        available = getattr(obj, "available_for_withdrawal", None)
        if available is None:
            return "0.00"
        return str(available)

    def get_wallet_balance(self, obj: Member) -> str:
        balance = getattr(obj, "wallet_balance", None)
        if balance is None:
            return "0.00"
        return str(balance)

    def get_operations(self, obj: Member):
        operations_qs = obj.admin_balance_operations.select_related("created_by").order_by(
            "-created_at"
        )[:20]
        return AdminBalanceOperationSerializer(operations_qs, many=True).data


class AdminCreateMemberSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "password",
            "is_influencer",
            "is_admin",
        ]

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

    def validate_password(self, value: str) -> str:
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value

    def create(self, validated_data: dict) -> Member:
        raw_password = validated_data.pop("password")

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
    new_password = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    def validate_new_password(self, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        if len(value) < 6:
            raise serializers.ValidationError(
                "Пароль должен содержать не менее 6 символов."
            )
        return value


class AdminBalanceAdjustmentSerializer(serializers.Serializer):
    deposit_delta = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    vcoins_delta = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=1000,
    )

    def validate(self, attrs):
        deposit_delta = attrs.get("deposit_delta")
        vcoins_delta = attrs.get("vcoins_delta")

        zero = Decimal("0.00")

        has_deposit_change = deposit_delta is not None and deposit_delta != zero
        has_vcoins_change = vcoins_delta is not None and vcoins_delta != zero

        if not has_deposit_change and not has_vcoins_change:
            raise serializers.ValidationError(
                "Укажите изменение депозита или V-Coins (значение не должно быть нулевым)."
            )

        member = self.context.get("member")
        if not isinstance(member, Member):
            return attrs

        current_deposit = member.get_balance()
        current_vcoins = member.v_coins_balance or Decimal("0.00")

        if has_deposit_change and current_deposit + deposit_delta < zero:
            raise serializers.ValidationError(
                {"deposit_delta": "Недостаточно средств на денежном балансе пользователя для списания."}
            )

        if has_vcoins_change and current_vcoins + vcoins_delta < zero:
            raise serializers.ValidationError(
                {"vcoins_delta": "Недостаточно V-Coins на балансе пользователя для списания."}
            )

        return attrs


# ============================
# Admin referral event & stats serializers
# ============================


class AdminReferralMemberBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "first_name", "last_name", "is_influencer"]


class AdminReferredMemberBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "first_name", "last_name"]


class ReferralEventAdminSerializer(serializers.ModelSerializer):
    referrer = AdminReferralMemberBriefSerializer(read_only=True)
    referred = AdminReferredMemberBriefSerializer(read_only=True)
    referrer_is_influencer = serializers.BooleanField(source="referrer.is_influencer", read_only=True)

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
        read_only_fields = fields


class AdminCreateReferralEventSerializer(serializers.Serializer):
    referred_id = serializers.IntegerField()
    deposit_amount = serializers.IntegerField()
    created_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_deposit_amount(self, value: int) -> int:
        if value <= 0:
            raise serializers.ValidationError(
                "Сумма депозита должна быть положительным числом."
            )
        return value

    def validate(self, attrs):
        referred_id = attrs.get("referred_id")
        try:
            member = Member.objects.get(pk=referred_id)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                {"referred_id": "Пользователь не найден."}
            )
        attrs["referred_member"] = member
        return attrs

    def create(self, validated_data):
        member = validated_data["referred_member"]
        deposit_amount = validated_data["deposit_amount"]
        created_at = validated_data.get("created_at")

        event = process_member_deposit(
            member=member,
            deposit_amount=deposit_amount,
            created_at=created_at,
        )

        if event is None:
            raise serializers.ValidationError(
                {
                    "referred_id": (
                        "Для указанного пользователя не настроен реферер, "
                        "невозможно создать реферальное событие."
                    )
                }
            )

        return event


class AdminStatsRegistrationsByDayItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class AdminStatsTopReferrerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_influencer = serializers.BooleanField()
    total_referrals = serializers.IntegerField()
    total_bonus_points = serializers.IntegerField()
    total_money_earned = serializers.IntegerField()


class AdminStatsIncomeBySourceSerializer(serializers.Serializer):
    total_income = serializers.IntegerField()
    income_from_influencers = serializers.IntegerField()
    income_from_regular_users = serializers.IntegerField()


class AdminStatsOverviewSerializer(serializers.Serializer):
    registrations_by_day = AdminStatsRegistrationsByDayItemSerializer(many=True)
    top_referrers = AdminStatsTopReferrerItemSerializer(many=True)
    income_by_source = AdminStatsIncomeBySourceSerializer()


class RankRuleSerializer(serializers.ModelSerializer):
    """Serializer exposing RankRule configuration for referral ranks."""

    class Meta:
        model = RankRule
        fields = [
            "rank",
            "required_referrals",
            "player_depth_bonus_multiplier",
            "influencer_depth_bonus_multiplier",
        ]
