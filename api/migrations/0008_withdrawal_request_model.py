from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_create_test_deposits_for_amir_and_alfira"),
    ]

    operations = [
        migrations.CreateModel(
            name="WithdrawalRequest",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "amount",
                    models.DecimalField(max_digits=12, decimal_places=2),
                ),
                (
                    "method",
                    models.CharField(
                        max_length=16,
                        choices=[
                            ("card", "Bank card"),
                            ("crypto", "Crypto wallet"),
                        ],
                    ),
                ),
                (
                    "destination",
                    models.TextField(
                        help_text=(
                            "Destination details for payout (card number or crypto wallet address)."
                        ),
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("paid", "Paid"),
                        ],
                        default="pending",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(null=True, blank=True)),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="withdrawal_requests",
                        to="api.member",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
