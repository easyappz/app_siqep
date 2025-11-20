from django.db import migrations


def mark_timur_as_influencer(apps, schema_editor):
    Member = apps.get_model("api", "Member")
    Member.objects.filter(first_name="Тимур", last_name="Комаров").update(
        is_influencer=True
    )


def unmark_timur_as_influencer(apps, schema_editor):
    Member = apps.get_model("api", "Member")
    Member.objects.filter(first_name="Тимур", last_name="Комаров").update(
        is_influencer=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            mark_timur_as_influencer,
            reverse_code=unmark_timur_as_influencer,
        ),
    ]
