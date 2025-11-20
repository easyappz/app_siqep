from django.db import migrations
from django.utils import timezone


def forwards_func(apps, schema_editor):
    Member = apps.get_model("api", "Member")

    # Locate Timur by phone number; this is the canonical identifier for this fix
    qs = Member.objects.filter(phone="89031221111")
    member = qs.first()

    if not member:
        # If the member is not found, exit gracefully without raising errors
        return

    updated_fields = []

    # Ensure influencer flag is set
    if not getattr(member, "is_influencer", False):
        member.is_influencer = True
        updated_fields.append("is_influencer")

    # Ensure user_type reflects influencer status
    if getattr(member, "user_type", None) != "influencer":
        member.user_type = "influencer"
        updated_fields.append("user_type")

    # Backfill influencer_since so that historical activity is clearly
    # associated with influencer status. We use created_at when available,
    # otherwise fall back to the current timestamp.
    if getattr(member, "influencer_since", None) is None:
        created_at = getattr(member, "created_at", None)
        member.influencer_since = created_at or timezone.now()
        updated_fields.append("influencer_since")

    if updated_fields:
        member.save(update_fields=updated_fields)

    # Note on historical recalculation:
    #
    # Existing referral and deposit logic (see api.referral_utils) applies
    # bonuses at the time events happen and does not expose a general
    # "rebuild all history" helper. To keep this migration safe and
    # idempotent, we only normalize Timur's status fields here so that:
    # - All existing referral relations already recorded for him are now
    #   interpreted with influencer status where relevant in the current
    #   business logic.
    # - All future bonuses (referral and deposit) will follow influencer
    #   program rules.
    #
    # We intentionally avoid trying to re-apply or mutate historical
    # monetary balances in this data migration, because there is no
    # reliable, idempotent way to recompute them from first principles
    # with the current schema and utilities.


def reverse_func(apps, schema_editor):
    # One-off data correction; keep reverse a no-op to avoid accidental
    # loss of influencer status if migrations are rolled back.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_ranked_referral_models"),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
