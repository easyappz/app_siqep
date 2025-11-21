from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0012_remove_demo_members_and_test_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminBalanceOperation",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "operation_type",
                    models.CharField(
                        max_length=64,
                        choices=[
                            ("deposit_accrual", "Deposit accrual"),
                            ("deposit_withdrawal", "Deposit withdrawal"),
                            ("vcoins_increase", "V-Coins increase"),
                            ("vcoins_decrease", "V-Coins decrease"),
                            ("combined_adjustment", "Combined adjustment"),
                        ],
                    ),
                ),
                (
                    "deposit_change",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "vcoins_change",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "balance_deposit_after",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=Decimal("0.00"),
                    ),
                ),
                (
                    "balance_vcoins_after",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=Decimal("0.00"),
                    ),
                ),
                ("comment", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_admin_balance_operations",
                        null=True,
                        blank=True,
                        to="api.member",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="admin_balance_operations",
                        to="api.member",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
