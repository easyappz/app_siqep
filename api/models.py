from __future__ import annotations

import secrets
from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# Referral and rank constants
MAX_REFERRAL_DEPTH = 10

PLAYER_DIRECT_REFERRAL_BONUS_VCOINS = Decimal("1000")
PLAYER_DEPTH_BASE_BONUS_VCOINS = Decimal("100")

INFLUENCER_DIRECT_REFERRAL_BONUS_CASH = Decimal("500")
INFLUENCER_DEPTH_BASE_BONUS_CASH = Decimal("50")

INFLUENCER_DEPOSIT_PERCENT = Decimal("0.10")

USER_TYPE_PLAYER = "player"
USER_TYPE_INFLUENCER = "influencer"

USER_TYPE_CHOICES = (
    (USER_TYPE_PLAYER, "Player"),
    (USER_TYPE_INFLUENCER, "Influencer"),
)

RANK_STANDARD = "standard"
RANK_SILVER = "silver"
RANK_GOLD = "gold"
RANK_PLATINUM = "platinum"

RANK_CHOICES = (
    (RANK_STANDARD, "Standard"),
    (RANK_SILVER, "Silver"),
    (RANK_GOLD, "Gold"),
    (RANK_PLATINUM, "Platinum"),
)


class Member(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    # Flags used by existing logic
    is_influencer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    # Ranked referral system fields
    referrer = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_referrals",
    )
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default=USER_TYPE_PLAYER,
    )
    rank = models.CharField(
        max_length=20,
        choices=RANK_CHOICES,
        default=RANK_STANDARD,
    )
    v_coins_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    cash_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    withdrawal_bank_details = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Реквизиты банковской карты/счёта для вывода средств (видит только "
            "владелец аккаунта и администратор)."
        ),
    )
    withdrawal_crypto_wallet = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Адрес криптовалютного кошелька для вывода средств (видит только "
            "владелец аккаунта и администратор)."
        ),
    )

    # Legacy referral fields kept for backward compatibility
    referral_code = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        null=True,
        blank=True,
    )
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    password_hash = models.CharField(max_length=128)
    total_bonus_points = models.IntegerField(default=0)
    total_money_earned = models.IntegerField(
        default=0,
        help_text="Total money earned in rubles.",
    )
    influencer_since = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the member became an influencer.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone})"

    @property
    def is_authenticated(self) -> bool:  # For DRF compatibility
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_player(self) -> bool:
        return self.user_type == USER_TYPE_PLAYER

    @property
    def is_influencer_user_type(self) -> bool:
        return self.user_type == USER_TYPE_INFLUENCER

    @property
    def wallet_balance(self) -> Decimal:
        """Unified wallet balance backed by cash_balance.

        All members (players and influencers) use this as their spendable
        in-app money balance.
        """

        if self.cash_balance is None:
            return Decimal("0.00")
        return self.cash_balance

    def get_balance(self) -> Decimal:
        """Return the current wallet balance for this member."""

        return self.wallet_balance

    @property
    def total_deposits(self) -> Decimal:
        """Return the total sum of all deposits for this member.

        Includes both test and real deposits. Returned as Decimal with 2 digits.
        """

        total = self.deposits.aggregate(total=Sum("amount"))["total"]
        if total is None:
            return Decimal("0.00")
        return total

    @property
    def total_influencer_earnings(self) -> Decimal:
        """Return the total influencer earnings (₽) based on referral rewards.

        Sums only monetary rewards: INFLUENCER_FIRST_TOURNAMENT and
        INFLUENCER_DEPOSIT_PERCENT.
        """

        total = (
            self.rewards.filter(
                reward_type__in=[
                    "INFLUENCER_FIRST_TOURNAMENT",
                    "INFLUENCER_DEPOSIT_PERCENT",
                ]
            ).aggregate(total=Sum("amount_rub"))["total"]
        )
        if total is None:
            return Decimal("0.00")
        return total

    @property
    def available_for_withdrawal(self) -> Decimal:
        """Return influencer earnings available for withdrawal.

        Calculated as total_influencer_earnings minus amounts from withdrawal
        requests that are already processed/approved (statuses 'approved' or 'paid').
        """

        total_withdrawn = (
            self.withdrawal_requests.filter(status__in=["approved", "paid"]).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        available = self.total_influencer_earnings - total_withdrawn
        if available < Decimal("0.00"):
            return Decimal("0.00")
        return available

    def set_password(self, raw_password: str) -> None:
        """Hash and store the given raw password."""
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Return True if the given raw password matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    def generate_referral_code(self) -> str:
        """Generate a deterministic-but-random-looking referral code.

        Uses the instance primary key plus a short random hex suffix.
        """
        if not self.pk:
            raise ValueError("Cannot generate referral code before Member has a primary key.")
        random_suffix = secrets.token_hex(2).upper()  # 4 hex characters
        return f"REF{self.pk}{random_suffix}"

    def save(self, *args, **kwargs) -> None:
        """Ensure a referral_code is generated and influencer_since is set correctly.

        - influencer_since is set once when a member becomes an influencer.
        - referral_code is guaranteed to be non-empty for all persisted members.
        """
        is_new = self.pk is None

        previous = None
        if not is_new:
            try:
                previous = Member.objects.get(pk=self.pk)
            except Member.DoesNotExist:
                previous = None

        # Set influencer_since only when a member becomes an influencer
        if is_new:
            if self.is_influencer and self.influencer_since is None:
                self.influencer_since = timezone.now()
        else:
            if (
                previous is not None
                and not previous.is_influencer
                and self.is_influencer
                and self.influencer_since is None
            ):
                self.influencer_since = timezone.now()

        super().save(*args, **kwargs)

        # Ensure referral code exists for all members once a primary key is available.
        # This covers both newly created members and legacy records that might not
        # have had a code generated previously.
        if self.pk and not self.referral_code:
            self.referral_code = self.generate_referral_code()
            super().save(update_fields=["referral_code"])

    def _apply_wallet_change(
        self,
        delta: Decimal,
        tx_type: str,
        description: str | None = None,
        meta: dict | None = None,
    ) -> "WalletTransaction":
        """Internal helper to change wallet balance and create a transaction.

        delta > 0 means credit, delta < 0 means debit. Resulting balance
        is clamped to not go below zero.
        """

        if delta == 0:
            raise ValueError("Amount must be non-zero.")

        with transaction.atomic():
            locked = Member.objects.select_for_update().get(pk=self.pk)
            current_balance = locked.cash_balance or Decimal("0.00")
            new_balance = current_balance + delta
            if new_balance < Decimal("0.00"):
                raise ValueError("Insufficient wallet balance.")

            new_balance = new_balance.quantize(Decimal("0.01"))
            amount = abs(delta).quantize(Decimal("0.01"))

            tx = WalletTransaction.objects.create(
                member=locked,
                type=tx_type,
                amount=amount,
                balance_after=new_balance,
                description=description or "",
                meta=meta or None,
            )

            # Trigger referral bonus logic for spend transactions
            if tx_type == WalletTransaction.Type.SPEND:
                from .referral_utils import create_spend_referral_bonus

                create_spend_referral_bonus(tx)

            locked.cash_balance = new_balance
            locked.save(update_fields=["cash_balance"])

        # Keep the in-memory instance in sync
        self.cash_balance = new_balance
        return tx

    def deposit(
        self,
        amount: Decimal,
        description: str | None = None,
        meta: dict | None = None,
    ) -> "WalletTransaction":
        """Credit the member's wallet by the given positive amount.

        Creates a DEPOSIT transaction and updates the cached balance atomically.
        """

        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        return self._apply_wallet_change(
            delta=amount,
            tx_type=WalletTransaction.Type.DEPOSIT,
            description=description,
            meta=meta,
        )

    def spend(
        self,
        amount: Decimal,
        description: str | None = None,
        meta: dict | None = None,
    ) -> "WalletTransaction":
        """Debit the member's wallet by the given positive amount.

        Raises ValueError if the balance is insufficient. Creates a SPEND
        transaction and updates the cached balance atomically.
        """

        if amount <= 0:
            raise ValueError("Spend amount must be positive.")
        return self._apply_wallet_change(
            delta=-amount,
            tx_type=WalletTransaction.Type.SPEND,
            description=description,
            meta=meta,
        )

    def adjust_balance(
        self,
        delta: Decimal,
        description: str | None = None,
        meta: dict | None = None,
    ) -> "WalletTransaction":
        """Manually adjust wallet balance by delta.

        Intended for admin-only corrections. Positive delta credits the
        wallet, negative delta debits it (cannot result in negative balance).
        """

        if delta == 0:
            raise ValueError("Adjustment amount must be non-zero.")
        return self._apply_wallet_change(
            delta=delta,
            tx_type=WalletTransaction.Type.ADJUSTMENT,
            description=description,
            meta=meta,
        )

    def admin_debit(
        self,
        amount: Decimal,
        reason: str | None = None,
        meta: dict | None = None,
        admin: "Member" | None = None,
    ) -> "WalletTransaction":
        """Admin-initiated debit operation on the member's wallet.

        - Validates that the amount is positive.
        - Ensures the balance is sufficient.
        - Creates a WalletTransaction with type ADMIN_DEBIT.
        - Optionally stores admin id and source in meta.
        """

        if amount <= 0:
            raise ValueError("Debit amount must be positive.")

        base_meta: dict = {"source": "admin_debit"}
        if admin is not None and getattr(admin, "id", None) is not None:
            base_meta["admin_id"] = admin.id
        if meta:
            base_meta.update(meta)

        return self._apply_wallet_change(
            delta=-amount,
            tx_type=WalletTransaction.Type.ADMIN_DEBIT,
            description=reason or "",
            meta=base_meta,
        )


class Deposit(models.Model):
    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="deposits",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(
        max_length=8,
        default="RUB",
    )
    is_test = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Deposit {self.amount} {self.currency} for member {self.member_id}"


class ReferralEvent(models.Model):
    id = models.AutoField(primary_key=True)
    referrer = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="referral_events",
    )
    referred = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="referred_event",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_amount = models.IntegerField(default=0)
    money_amount = models.IntegerField(
        default=0,
        help_text="Money amount for influencer in rubles.",
    )
    deposit_amount = models.IntegerField(
        default=1000,
        help_text="Deposit amount in rubles associated with the referral.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Referral from {self.referrer} to {self.referred}"


class ReferralReward(models.Model):
    class RewardType(models.TextChoices):
        PLAYER_STACK = "PLAYER_STACK", "Player Stack"
        INFLUENCER_FIRST_TOURNAMENT = (
            "INFLUENCER_FIRST_TOURNAMENT",
            "Influencer First Tournament",
        )
        INFLUENCER_DEPOSIT_PERCENT = (
            "INFLUENCER_DEPOSIT_PERCENT",
            "Influencer Deposit Percent",
        )

    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    source_member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="generated_rewards",
    )
    reward_type = models.CharField(
        max_length=64,
        choices=RewardType.choices,
    )
    amount_rub = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    stack_count = models.IntegerField(default=0)
    depth = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reward {self.reward_type} for {self.member_id} from {self.source_member_id}"


class ReferralRelation(models.Model):
    id = models.AutoField(primary_key=True)
    ancestor = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="referral_descendants",
    )
    descendant = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="referral_ancestors",
    )
    level = models.PositiveIntegerField()
    has_paid_first_bonus = models.BooleanField(default=False)

    class Meta:
        unique_together = ("ancestor", "descendant")
        ordering = ["ancestor_id", "level"]

    def __str__(self) -> str:
        return f"Relation anc={self.ancestor_id} desc={self.descendant_id} lvl={self.level}"


class RankRule(models.Model):
    rank = models.CharField(
        primary_key=True,
        max_length=20,
        choices=RANK_CHOICES,
    )
    required_referrals = models.PositiveIntegerField()
    player_depth_bonus_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
    )
    influencer_depth_bonus_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
    )

    class Meta:
        ordering = ["required_referrals"]

    def __str__(self) -> str:
        return f"RankRule {self.rank} (required={self.required_referrals})"


class WithdrawalRequest(models.Model):
    class Method(models.TextChoices):
        CARD = "card", "Bank card"
        CRYPTO = "crypto", "Crypto wallet"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(
        max_length=16,
        choices=Method.choices,
    )
    destination = models.TextField(
        help_text=(
            "Destination details for payout (card number or crypto wallet address)."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WithdrawalRequest {self.id} member={self.member_id} amount={self.amount}"

    def mark_as_paid(self) -> "WalletTransaction | None":
        """Mark this withdrawal as paid and deduct funds from the member wallet.

        Deduction is performed via Member.spend and is atomic with the status
        update. If the request is already paid, this is a no-op.
        """

        if self.status == self.Status.PAID:
            return None

        with transaction.atomic():
            locked = (
                WithdrawalRequest.objects.select_for_update()
                .select_related("member")
                .get(pk=self.pk)
            )
            if locked.status == self.Status.PAID:
                return None

            member = locked.member
            tx = member.spend(
                locked.amount,
                description="Withdrawal payout",
                meta={"withdrawal_request_id": locked.id},
            )

            locked.status = self.Status.PAID
            locked.processed_at = timezone.now()
            locked.save(update_fields=["status", "processed_at"])

        # Keep in-memory state in sync
        self.status = locked.status
        self.processed_at = locked.processed_at
        return tx


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        SPEND = "spend", "Spend"
        WITHDRAW = "withdraw", "Withdraw"
        REFUND = "refund", "Refund"
        ADJUSTMENT = "adjustment", "Adjustment"
        ADMIN_DEBIT = "admin_debit", "Admin debit"
        BONUS = "bonus", "Referral bonus"

    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="wallet_transactions",
    )
    type = models.CharField(
        max_length=32,
        choices=Type.choices,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, default="")
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"WalletTransaction(id={self.id}, member={self.member_id}, "
            f"type={self.type}, amount={self.amount})"
        )


class ReferralBonus(models.Model):
    id = models.AutoField(primary_key=True)
    referrer = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="referral_bonuses",
    )
    referred_member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="generated_bonuses",
    )
    spend_transaction = models.OneToOneField(
        "WalletTransaction",
        on_delete=models.CASCADE,
        related_name="referral_bonus",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"ReferralBonus(id={self.id}, referrer={self.referrer_id}, "
            f"referred={self.referred_member_id}, tx={self.spend_transaction_id}, "
            f"amount={self.amount})"
        )


class MemberAuthToken(models.Model):
    key = models.CharField(primary_key=True, max_length=64, editable=False)
    member = models.OneToOneField(
        Member,
        on_delete=models.CASCADE,
        related_name="auth_token",
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"Token for {self.member}"

    @staticmethod
    def generate_key() -> str:
        """Generate a secure random token key."""
        return secrets.token_hex(32)

    @classmethod
    def create_for_member(cls, member: "Member") -> "MemberAuthToken":
        """Create or regenerate a token for the given member.

        Ensures there is at most one active token per member.
        """
        cls.objects.filter(member=member).delete()
        key = cls.generate_key()
        return cls.objects.create(member=member, key=key)


class PasswordResetCode(models.Model):
    """One-time code used to reset a Member's password.

    Codes are created on password reset request and must be confirmed within
    a limited time window. After successful use, codes are marked as used.
    """

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
    )
    code = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PasswordResetCode(member={self.member_id}, used={self.is_used})"


@receiver(post_save, sender=Deposit)
def handle_deposit_post_save(sender, instance: "Deposit", created: bool, **kwargs) -> None:
    """When a new Deposit is created, apply full referral logic for this deposit.

    This will:
    - create a corresponding ReferralEvent for analytics (if there is a referrer),
    - trigger first-tournament bonuses if this is the first qualifying deposit,
    - apply 10% influencer commission for the direct influencer referrer.

    Additionally, the deposited amount is credited to the member's unified
    wallet balance via Member.deposit.
    """

    if not created:
        return

    if instance.member_id is None:
        return

    # Import lazily to avoid circular imports at module load time.
    from .referral_utils import process_deposit_for_referrals

    # Apply referral logic based on this deposit
    process_deposit_for_referrals(instance)

    # Credit the member's wallet with the deposited amount
    member = instance.member
    if member is not None:
        try:
            member.deposit(
                instance.amount,
                description="External deposit",
                meta={"deposit_id": instance.id, "currency": instance.currency},
            )
        except ValueError:
            # In case of unexpected negative/zero amounts, just skip wallet update
            pass
