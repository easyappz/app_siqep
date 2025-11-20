from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
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
