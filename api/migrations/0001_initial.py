from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Member",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("phone", models.CharField(max_length=32, unique=True)),
                (
                    "email",
                    models.EmailField(
                        max_length=254,
                        unique=True,
                        null=True,
                        blank=True,
                    ),
                ),
                ("is_influencer", models.BooleanField(default=False)),
                ("is_admin", models.BooleanField(default=False)),
                (
                    "referral_code",
                    models.CharField(
                        max_length=32,
                        unique=True,
                        editable=False,
                        null=True,
                        blank=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("password_hash", models.CharField(max_length=128)),
                ("total_bonus_points", models.IntegerField(default=0)),
                (
                    "total_money_earned",
                    models.IntegerField(
                        default=0,
                        help_text="Total money earned in rubles.",
                    ),
                ),
                (
                    "referred_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="referrals",
                        blank=True,
                        null=True,
                        to="api.member",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReferralEvent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("bonus_amount", models.IntegerField(default=0)),
                (
                    "money_amount",
                    models.IntegerField(
                        default=0,
                        help_text="Money amount for influencer in rubles.",
                    ),
                ),
                (
                    "deposit_amount",
                    models.IntegerField(
                        default=1000,
                        help_text=(
                            "Deposit amount in rubles associated with the referral."
                        ),
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_events",
                        to="api.member",
                    ),
                ),
                (
                    "referred",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referred_event",
                        to="api.member",
                        unique=True,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MemberAuthToken",
            fields=[
                (
                    "key",
                    models.CharField(
                        primary_key=True,
                        serialize=False,
                        max_length=64,
                        editable=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "member",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auth_token",
                        to="api.member",
                    ),
                ),
            ],
            options={"ordering": ["-created"]},
        ),
    ]
