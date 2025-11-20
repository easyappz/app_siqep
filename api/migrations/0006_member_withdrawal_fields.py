from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_mark_timur_influencer_and_recalculate"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="withdrawal_bank_details",
            field=models.TextField(
                null=True,
                blank=True,
                help_text=(
                    "Реквизиты банковской карты/счёта для вывода средств (видит только "
                    "владелец аккаунта и администратор)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="withdrawal_crypto_wallet",
            field=models.TextField(
                null=True,
                blank=True,
                help_text=(
                    "Адрес криптовалютного кошелька для вывода средств (видит только "
                    "владелец аккаунта и администратор)."
                ),
            ),
        ),
    ]
