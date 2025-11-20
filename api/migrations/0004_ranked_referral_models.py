from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def forwards_populate_rank_rules(apps, schema_editor):
    RankRule = apps.get_model("api", "RankRule")

    rules = [
        {
            "rank": "standard",
            "required_referrals": 0,
            "multiplier": Decimal("1.00"),
        },
        {
            "rank": "silver",
            "required_referrals": 5,
            "multiplier": Decimal("1.50"),
        },
        {
            "rank": "gold",
            "required_referrals": 20,
            "multiplier": Decimal("2.00"),
        },
        {
            "rank": "platinum",
            "required_referrals": 50,
            "multiplier": Decimal("2.50"),
        },
    ]

    for rule in rules:
        RankRule.objects.update_or_create(
            rank=rule["rank"],
            defaults={
                "required_referrals": rule["required_referrals"],
                "player_depth_bonus_multiplier": rule["multiplier"],
                "influencer_depth_bonus_multiplier": rule["multiplier"],
            },
        )


def backwards_delete_rank_rules(apps, schema_editor):
    RankRule = apps.get_model("api", "RankRule")
    RankRule.objects.filter(
        rank__in=["standard", "silver", "gold", "platinum"]
    ).delete()


def forwards_sync_member_fields(apps, schema_editor):
    Member = apps.get_model("api", "Member")

    for member in Member.objects.all():
        # Keep new referrer aligned with legacy referred_by
        if member.referred_by_id and member.referrer_id is None:
            member.referrer_id = member.referred_by_id

        # Derive user_type from is_influencer flag when not set
        if not member.user_type:
            member.user_type = "influencer" if member.is_influencer else "player"

        if member.rank is None or member.rank == "":
            member.rank = "standard"

        if member.v_coins_balance is None:
            member.v_coins_balance = Decimal("0.00")

        if member.cash_balance is None:
            member.cash_balance = Decimal("0.00")

        member.save(update_fields=[
            "referrer",
            "user_type",
            "rank",
            "v_coins_balance",
            "cash_balance",
        ])


def backwards_unset_member_referrer(apps, schema_editor):
    Member = apps.get_model("api", "Member")
    Member.objects.update(referrer=None)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_deep_referral_rewards"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="referrer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="direct_referrals",
                null=True,
                blank=True,
                to="api.member",
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="user_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("player", "Player"),
                    ("influencer", "Influencer"),
                ],
                default="player",
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="rank",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("standard", "Standard"),
                    ("silver", "Silver"),
                    ("gold", "Gold"),
                    ("platinum", "Platinum"),
                ],
                default="standard",
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="v_coins_balance",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                default=Decimal("0.00"),
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="cash_balance",
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                default=Decimal("0.00"),
            ),
        ),
        migrations.CreateModel(
            name="ReferralRelation",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("level", models.PositiveIntegerField()),
                ("has_paid_first_bonus", models.BooleanField(default=False)),
                (
                    "ancestor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_descendants",
                        to="api.member",
                    ),
                ),
                (
                    "descendant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_ancestors",
                        to="api.member",
                    ),
                ),
            ],
            options={
                "ordering": ["ancestor_id", "level"],
                "unique_together": {("ancestor", "descendant")},
            },
        ),
        migrations.CreateModel(
            name="RankRule",
            fields=[
                (
                    "rank",
                    models.CharField(
                        primary_key=True,
                        serialize=False,
                        max_length=20,
                        choices=[
                            ("standard", "Standard"),
                            ("silver", "Silver"),
                            ("gold", "Gold"),
                            ("platinum", "Platinum"),
                        ],
                    ),
                ),
                ("required_referrals", models.PositiveIntegerField()),
                (
                    "player_depth_bonus_multiplier",
                    models.DecimalField(max_digits=4, decimal_places=2),
                ),
                (
                    "influencer_depth_bonus_multiplier",
                    models.DecimalField(max_digits=4, decimal_places=2),
                ),
            ],
            options={
                "ordering": ["required_referrals"],
            },
        ),
        migrations.RunPython(
            forwards_populate_rank_rules,
            reverse_code=backwards_delete_rank_rules,
        ),
        migrations.RunPython(
            forwards_sync_member_fields,
            reverse_code=backwards_unset_member_referrer,
        ),
    ]
