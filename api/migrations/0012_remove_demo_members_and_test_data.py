from django.db import migrations
from django.db.models import Q


def remove_demo_members_and_test_data(apps, schema_editor):
    Member = apps.get_model("api", "Member")
    Deposit = apps.get_model("api", "Deposit")
    ReferralEvent = apps.get_model("api", "ReferralEvent")
    ReferralRelation = apps.get_model("api", "ReferralRelation")
    ReferralReward = apps.get_model("api", "ReferralReward")
    WalletTransaction = apps.get_model("api", "WalletTransaction")
    ReferralBonus = apps.get_model("api", "ReferralBonus")
    WithdrawalRequest = apps.get_model("api", "WithdrawalRequest")
    PasswordResetCode = apps.get_model("api", "PasswordResetCode")
    MemberAuthToken = apps.get_model("api", "MemberAuthToken")

    # Phones of demo members used in historical test flows
    demo_phones = [
        "89031221111",      # Timur
        "+79990000001",    # Amir
        "+79990000002",    # Alfira
    ]

    demo_members_qs = Member.objects.filter(phone__in=demo_phones)
    demo_member_ids = list(demo_members_qs.values_list("id", flat=True))

    # Always remove explicitly marked test deposits, regardless of member
    Deposit.objects.filter(is_test=True).delete()

    if not demo_member_ids:
        return

    # Delete deposits for demo members (in addition to is_test ones above)
    Deposit.objects.filter(member_id__in=demo_member_ids).delete()

    # Delete referral events where demo members participate as referrer or referred
    ReferralEvent.objects.filter(
        Q(referrer_id__in=demo_member_ids) | Q(referred_id__in=demo_member_ids)
    ).delete()

    # Delete referral relations involving demo members
    ReferralRelation.objects.filter(
        Q(ancestor_id__in=demo_member_ids) | Q(descendant_id__in=demo_member_ids)
    ).delete()

    # Delete referral rewards linked to demo members
    ReferralReward.objects.filter(
        Q(member_id__in=demo_member_ids) | Q(source_member_id__in=demo_member_ids)
    ).delete()

    # Delete wallet transactions for demo members
    WalletTransaction.objects.filter(member_id__in=demo_member_ids).delete()

    # Delete referral bonuses linked to demo members
    ReferralBonus.objects.filter(
        Q(referrer_id__in=demo_member_ids)
        | Q(referred_member_id__in=demo_member_ids)
    ).delete()

    # Delete withdrawal requests for demo members
    WithdrawalRequest.objects.filter(member_id__in=demo_member_ids).delete()

    # Delete password reset codes for demo members
    PasswordResetCode.objects.filter(member_id__in=demo_member_ids).delete()

    # Delete auth tokens for demo members
    MemberAuthToken.objects.filter(member_id__in=demo_member_ids).delete()

    # Finally, delete the demo Member records themselves
    Member.objects.filter(id__in=demo_member_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_referral_bonus_model"),
    ]

    operations = [
        migrations.RunPython(
            remove_demo_members_and_test_data,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
