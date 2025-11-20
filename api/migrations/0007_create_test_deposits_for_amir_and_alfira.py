from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations, models
from django.utils import timezone


def create_test_deposits_for_amir_and_alfira(apps, schema_editor):
    """Create test deposits for Амир and Альфира and ensure Timur earns commission.

    IMPORTANT: This migration uses only historical models obtained via
    ``apps.get_model`` and does NOT import runtime code from ``api``.
    This avoids mixing different ``Member`` model classes in ORM queries,
    which previously caused ``ValueError: Cannot query "Member object (X)":
    Must be "Member" instance.`` when calling runtime helpers from here.

    Steps:
    - Ensure influencer Timur exists and is marked as influencer.
    - Ensure test members Амир и Альфира exist (using fixed test phone numbers).
    - Link them as direct referrals of Timur and create corresponding
      ``ReferralRelation`` rows.
    - Create a 2000 RUB test ``Deposit`` for each of them (if not already present).
    - For each newly created ``Deposit``, record a ``ReferralEvent`` and apply
      influencer bonuses directly using the historical models:
        * one‑time 500 ₽ bonus for the first qualifying tournament/deposit;
        * lifetime 10% commission from each deposit.

    The migration is idempotent with respect to deposits: if a test deposit
    already exists for a given member, no new deposit or extra bonuses are
    created for that member.
    """

    Member = apps.get_model("api", "Member")
    Deposit = apps.get_model("api", "Deposit")
    ReferralRelation = apps.get_model("api", "ReferralRelation")
    ReferralEvent = apps.get_model("api", "ReferralEvent")
    ReferralReward = apps.get_model("api", "ReferralReward")

    # Constants duplicated here intentionally to keep the migration stable
    # even if business constants change in the Python code later.
    INFLUENCER_FIRST_TOURNAMENT_BONUS = Decimal("500")
    INFLUENCER_DEPOSIT_PERCENT = Decimal("0.10")

    # --- Ensure Timur exists and is an influencer ---
    timur = Member.objects.filter(phone="89031221111").first()
    if timur is None:
        timur = (
            Member.objects.filter(first_name="Тимур", last_name="Комаров").first()
        )

    if timur is None:
        # Create Timur with a deterministic test password.
        timur = Member.objects.create(
            first_name="Тимур",
            last_name="Комаров",
            phone="89031221111",
            email=None,
            is_influencer=True,
            is_admin=False,
            referral_code=None,
            password_hash=make_password("timur_test_password"),
            total_bonus_points=0,
            total_money_earned=0,
            user_type="influencer",
            rank="standard",
            v_coins_balance=Decimal("0.00"),
            cash_balance=Decimal("0.00"),
            influencer_since=timezone.now(),
        )
    else:
        updated_fields = []
        if not getattr(timur, "is_influencer", False):
            timur.is_influencer = True
            updated_fields.append("is_influencer")
        if getattr(timur, "user_type", None) != "influencer":
            timur.user_type = "influencer"
            updated_fields.append("user_type")
        if getattr(timur, "influencer_since", None) is None:
            created_at = getattr(timur, "created_at", None)
            timur.influencer_since = created_at or timezone.now()
            updated_fields.append("influencer_since")
        if updated_fields:
            timur.save(update_fields=updated_fields)

    players_def = [
        {
            "first_name": "Амир",
            "last_name": "Тестов",
            "phone": "+79990000001",
        },
        {
            "first_name": "Альфира",
            "last_name": "Тестова",
            "phone": "+79990000002",
        },
    ]

    amount_decimal = Decimal("2000.00")
    new_deposits = []

    for cfg in players_def:
        member = Member.objects.filter(phone=cfg["phone"]).first()
        if member is None:
            # Create a dedicated test member linked to Timur
            member = Member.objects.create(
                first_name=cfg["first_name"],
                last_name=cfg["last_name"],
                phone=cfg["phone"],
                email=None,
                is_influencer=False,
                is_admin=False,
                referral_code=None,
                password_hash=make_password("test1234"),
                total_bonus_points=0,
                total_money_earned=0,
                user_type="player",
                rank="standard",
                v_coins_balance=Decimal("0.00"),
                cash_balance=Decimal("0.00"),
                referrer=timur,
                referred_by=timur,
            )
        else:
            # Ensure the existing member is linked to Timur as direct referrer
            updated_fields = []
            if getattr(member, "referrer_id", None) != timur.id:
                member.referrer = timur
                updated_fields.append("referrer")
            if getattr(member, "referred_by_id", None) != timur.id:
                member.referred_by = timur
                updated_fields.append("referred_by")
            if getattr(member, "user_type", None) != "player":
                member.user_type = "player"
                updated_fields.append("user_type")
            if updated_fields:
                member.save(update_fields=updated_fields)

        # Ensure direct referral relation Timur -> member exists (level 1).
        if timur.id is not None and member.id is not None:
            ReferralRelation.objects.get_or_create(
                ancestor_id=timur.id,
                descendant_id=member.id,
                defaults={"level": 1, "has_paid_first_bonus": False},
            )

        # Create a test deposit for this member if it does not yet exist
        deposit_exists = Deposit.objects.filter(
            member_id=member.id,
            amount=amount_decimal,
            currency="RUB",
            is_test=True,
        ).exists()

        if not deposit_exists:
            deposit = Deposit.objects.create(
                member_id=member.id,
                amount=amount_decimal,
                currency="RUB",
                is_test=True,
            )
            new_deposits.append(deposit)

    # Apply simple referral logic for all newly created deposits so that Timur
    # earns his commission and rewards are properly recorded. We operate only
    # with historical models and primary keys to avoid cross-app model issues.
    for deposit in new_deposits:
        member = deposit.member
        if member is None or timur.id is None or member.id is None:
            continue

        # Create an analytics ReferralEvent if there is not already one with
        # the same referrer, referred and deposit amount.
        if not ReferralEvent.objects.filter(
            referrer_id=timur.id,
            referred_id=member.id,
            deposit_amount=int(deposit.amount),
        ).exists():
            ReferralEvent.objects.create(
                referrer_id=timur.id,
                referred_id=member.id,
                bonus_amount=0,
                money_amount=0,
                deposit_amount=int(deposit.amount),
                created_at=deposit.created_at,
            )

        # One-time first-tournament bonus for direct influencer referrer.
        relation = ReferralRelation.objects.filter(
            ancestor_id=timur.id,
            descendant_id=member.id,
        ).first()

        if relation and not relation.has_paid_first_bonus:
            bonus = INFLUENCER_FIRST_TOURNAMENT_BONUS

            timur.cash_balance = (timur.cash_balance or Decimal("0.00")) + bonus
            timur.total_money_earned = (timur.total_money_earned or 0) + int(bonus)
            timur.save(update_fields=["cash_balance", "total_money_earned"])

            ReferralReward.objects.create(
                member_id=timur.id,
                source_member_id=member.id,
                reward_type="INFLUENCER_FIRST_TOURNAMENT",
                amount_rub=bonus,
                stack_count=0,
                depth=1,
            )

            relation.has_paid_first_bonus = True
            relation.save(update_fields=["has_paid_first_bonus"])

        # Lifetime 10% influencer commission for this deposit.
        commission = (deposit.amount * INFLUENCER_DEPOSIT_PERCENT).quantize(
            Decimal("0.01")
        )
        if commission <= 0:
            continue

        timur.cash_balance = (timur.cash_balance or Decimal("0.00")) + commission
        timur.total_money_earned = (
            timur.total_money_earned or 0
        ) + int(commission)
        timur.save(update_fields=["cash_balance", "total_money_earned"])

        ReferralReward.objects.create(
            member_id=timur.id,
            source_member_id=member.id,
            reward_type="INFLUENCER_DEPOSIT_PERCENT",
            amount_rub=commission,
            stack_count=0,
            depth=1,
        )


def noop_reverse_func(apps, schema_editor):
    """Reverse operation is intentionally a no-op.

    We do not delete members, relations or deposits on migration rollback to
    avoid accidental loss of test data and referral history.
    """

    return


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_member_withdrawal_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Deposit",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("amount", models.DecimalField(max_digits=12, decimal_places=2)),
                ("currency", models.CharField(default="RUB", max_length=8)),
                ("is_test", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="deposits",
                        to="api.member",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(create_test_deposits_for_amir_and_alfira, noop_reverse_func),
    ]
