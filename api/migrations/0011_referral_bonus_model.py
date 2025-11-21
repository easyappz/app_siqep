from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_wallet_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralBonus",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("amount", models.DecimalField(max_digits=12, decimal_places=2)),
                ("description", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_bonuses",
                        to="api.member",
                    ),
                ),
                (
                    "referred_member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generated_bonuses",
                        to="api.member",
                    ),
                ),
                (
                    "spend_transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_bonus",
                        to="api.wallettransaction",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterField(
            model_name="wallettransaction",
            name="type",
            field=models.CharField(
                max_length=32,
                choices=[
                    ("deposit", "Deposit"),
                    ("spend", "Spend"),
                    ("withdraw", "Withdraw"),
                    ("refund", "Refund"),
                    ("adjustment", "Adjustment"),
                    ("bonus", "Referral bonus"),
                ],
            ),
        ),
    ]
