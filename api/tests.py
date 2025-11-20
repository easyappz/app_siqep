from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Member, ReferralReward
from .serializers import RegistrationSerializer, AdminCreateReferralEventSerializer


class ReferralRewardTests(TestCase):
    def _create_member(self, first_name, referred_by=None, is_influencer=False):
        index = Member.objects.count() + 1
        member = Member(
            first_name=first_name,
            last_name="Test",
            phone=f"+700000000{index}",
            email=None,
            is_influencer=is_influencer,
        )
        member.set_password("password123")
        member.save()
        if referred_by is not None:
            member.referred_by = referred_by
            member.save(update_fields=["referred_by"])
        return member

    def test_registration_creates_player_stack_rewards_for_full_chain(self):
        """A -> B -> C chain: registering C via B's referral gives stacks to B (depth 1) and A (depth 2)."""
        a = self._create_member("A")
        b = self._create_member("B", referred_by=a)

        data = {
            "first_name": "C",
            "last_name": "Test",
            "phone": "+79990000001",
            "email": "",
            "password": "secret123",
            "referral_code": b.referral_code,
        }
        serializer = RegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        member_c = serializer.save()

        rewards_b = ReferralReward.objects.filter(
            member=b,
            source_member=member_c,
            reward_type=ReferralReward.RewardType.PLAYER_STACK,
        )
        rewards_a = ReferralReward.objects.filter(
            member=a,
            source_member=member_c,
            reward_type=ReferralReward.RewardType.PLAYER_STACK,
        )

        self.assertEqual(rewards_b.count(), 1)
        self.assertEqual(rewards_a.count(), 1)
        self.assertEqual(rewards_b.first().depth, 1)
        self.assertEqual(rewards_a.first().depth, 2)

    def test_influencer_earns_first_tournament_and_deposit_percent_rewards(self):
        """Influencer with descendants earns 1000 RUB for first tournament and 10% of later deposits."""
        influencer = self._create_member("Influencer", is_influencer=True)
        # Ensure influencer_since is in the past so all events are eligible.
        influencer.influencer_since = timezone.now() - timedelta(days=1)
        influencer.save(update_fields=["influencer_since"])

        child = self._create_member("Child", referred_by=influencer)
        grandchild = self._create_member("Grandchild", referred_by=child)

        # Child deposits: first = first tournament, second = further deposit.
        s1 = AdminCreateReferralEventSerializer(
            data={"referred_id": child.id, "deposit_amount": 5000}
        )
        self.assertTrue(s1.is_valid(), s1.errors)
        s1.save()

        s2 = AdminCreateReferralEventSerializer(
            data={"referred_id": child.id, "deposit_amount": 2000}
        )
        self.assertTrue(s2.is_valid(), s2.errors)
        s2.save()

        # Grandchild deposits: first and second.
        s3 = AdminCreateReferralEventSerializer(
            data={"referred_id": grandchild.id, "deposit_amount": 3000}
        )
        self.assertTrue(s3.is_valid(), s3.errors)
        s3.save()

        s4 = AdminCreateReferralEventSerializer(
            data={"referred_id": grandchild.id, "deposit_amount": 4000}
        )
        self.assertTrue(s4.is_valid(), s4.errors)
        s4.save()

        rewards = ReferralReward.objects.filter(member=influencer)

        first_rewards = rewards.filter(
            reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT
        )
        self.assertEqual(first_rewards.count(), 2)
        for reward in first_rewards:
            self.assertEqual(reward.amount_rub, Decimal("1000.00"))

        percent_rewards = rewards.filter(
            reward_type=ReferralReward.RewardType.INFLUENCER_DEPOSIT_PERCENT
        )
        total_percent = sum(
            (reward.amount_rub for reward in percent_rewards),
            Decimal("0.00"),
        )
        expected = Decimal("2000") * Decimal("0.10") + Decimal("4000") * Decimal("0.10")
        self.assertEqual(total_percent, expected)

    def test_influencer_since_blocks_rewards_before_promotion(self):
        """Events before a member becomes influencer do not generate rewards; later events do."""
        influencer = self._create_member("Influencer", is_influencer=False)
        child = self._create_member("Child", referred_by=influencer)

        # Deposit before influencer promotion: should not create any rewards.
        s1 = AdminCreateReferralEventSerializer(
            data={"referred_id": child.id, "deposit_amount": 1000}
        )
        self.assertTrue(s1.is_valid(), s1.errors)
        s1.save()

        # Promote to influencer now.
        influencer.is_influencer = True
        influencer.save()

        # Deposit after promotion: should create first tournament reward.
        s2 = AdminCreateReferralEventSerializer(
            data={"referred_id": child.id, "deposit_amount": 1000}
        )
        self.assertTrue(s2.is_valid(), s2.errors)
        s2.save()

        rewards = ReferralReward.objects.filter(
            member=influencer,
            reward_type=ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT,
        )
        self.assertEqual(rewards.count(), 1)
