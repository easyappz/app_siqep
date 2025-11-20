from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_mark_timur_influencer"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="influencer_since",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Date and time when the member became an influencer.",
            ),
        ),
        migrations.CreateModel(
            name="ReferralReward",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "reward_type",
                    models.CharField(
                        max_length=64,
                        choices=[
                            ("PLAYER_STACK", "Player Stack"),
                            (
                                "INFLUENCER_FIRST_TOURNAMENT",
                                "Influencer First Tournament",
                            ),
                            (
                                "INFLUENCER_DEPOSIT_PERCENT",
                                "Influencer Deposit Percent",
                            ),
                        ],
                    ),
                ),
                (
                    "amount_rub",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=0,
                    ),
                ),
                ("stack_count", models.IntegerField(default=0)),
                ("depth", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rewards",
                        to="api.member",
                    ),
                ),
                (
                    "source_member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generated_rewards",
                        to="api.member",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterField(
            model_name="referralevent",
            name="referred",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="referred_event",
                to="api.member",
            ),
        ),
    ]
