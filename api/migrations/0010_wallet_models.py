from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0009_passwordresetcode"),
    ]

    operations = [
        migrations.CreateModel(
            name="WalletTransaction",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "type",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("deposit", "Deposit"),
                            ("spend", "Spend"),
                            ("withdraw", "Withdraw"),
                            ("refund", "Refund"),
                            ("adjustment", "Adjustment"),
                        ],
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(max_digits=12, decimal_places=2),
                ),
                (
                    "balance_after",
                    models.DecimalField(max_digits=12, decimal_places=2),
                ),
                (
                    "description",
                    models.TextField(blank=True, default=""),
                ),
                ("meta", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet_transactions",
                        to="api.member",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
