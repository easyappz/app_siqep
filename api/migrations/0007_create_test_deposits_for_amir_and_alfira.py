from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations, models
from django.utils import timezone


def create_test_deposits_for_amir_and_alfira(apps, schema_editor):
    """Create test deposits for Амир and Альфира and ensure Timur earns commission.

    Steps:
    - Ensure influencer Timur exists and is marked as influencer.
    - Ensure test members Амир и Альфира exist (using fixed test phone numbers).
    - Link them as direct referrals of Timur.
    - Create a 2000 RUB test Deposit for each of them (if not already present).
    - For each newly created Deposit, run the standard referral deposit logic
      so that Timur receives his commission and rewards are recorded.

    The migration is idempotent: if members, relations or deposits already
    exist, they are reused and not duplicated.
    """

    Member = apps.get_model("api", "Member")
    Deposit = apps.get_model("api", "Deposit")

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

    # Import referral utilities from the current codebase.
    from api import referral_utils

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
            # Build referral relations for the new member
            referral_utils.on_new_user_registered(member)
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
                # Rebuild referral relations for this member
                referral_utils.on_new_user_registered(member)

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

    # Apply referral logic for all newly created deposits so that Timur earns
    # his commission and rewards are properly recorded.
    for deposit in new_deposits:
        referral_utils.process_deposit_for_referrals(deposit)


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
