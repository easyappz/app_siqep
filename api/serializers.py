from datetime import timedelta
from decimal import Decimal
import secrets

from django.utils import timezone
from django.db.models import Sum
from rest_framework import serializers

from .models import (
    Member,
    ReferralEvent,
    ReferralReward,
    ReferralRelation,
    RankRule,
    Deposit,
    WithdrawalRequest,
    PasswordResetCode,
    WalletTransaction,
)
from .referral_utils import (
    on_new_user_registered,
    process_member_deposit,
)

# ... existing serializers remain unchanged ...

class SimulateDemoDepositsResponseSerializer(serializers.Serializer):
    """Response schema for the demo deposits simulation endpoint."""

    players = SimulateDemoDepositsPlayerSerializer(many=True)
    timur = SimulateDemoDepositsTimurSerializer()


class BusinessSimulationRequestSerializer(serializers.Serializer):
    """Optional parameters for the business model simulation."""

    seed = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Опциональный детерминированный seed для симуляции.",
    )


class BusinessSimulationPlayerSerializer(serializers.Serializer):
    """Financial summary for a simulated player."""

    member_id = serializers.IntegerField()
    phone = serializers.CharField()
    influencer_id = serializers.IntegerField()
    deposit_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    spend_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class BusinessSimulationInfluencerSerializer(serializers.Serializer):
    """Aggregated metrics per influencer."""

    member_id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    players_count = serializers.IntegerField()
    active_players = serializers.IntegerField()
    total_deposit_volume = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_spend_volume = serializers.DecimalField(max_digits=14, decimal_places=2)
    referral_reward_volume = serializers.DecimalField(max_digits=14, decimal_places=2)
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class BusinessSimulationGlobalMetricsSerializer(serializers.Serializer):
    """Global totals for the simulation run."""

    total_influencers = serializers.IntegerField()
    total_players = serializers.IntegerField()
    total_deposit_volume = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_spend_volume = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_referral_rewards = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_active_referrals = serializers.IntegerField()


class BusinessSimulationCountersSerializer(serializers.Serializer):
    """Technical counters describing created entities."""

    new_influencers = serializers.IntegerField()
    new_players = serializers.IntegerField()
    new_referral_events = serializers.IntegerField()
    new_wallet_deposits = serializers.IntegerField()
    new_wallet_spends = serializers.IntegerField()


class BusinessSimulationResponseSerializer(serializers.Serializer):
    """Full payload for the business simulation endpoint."""

    scenario_tag = serializers.CharField()
    influencers = BusinessSimulationInfluencerSerializer(many=True)
    players = BusinessSimulationPlayerSerializer(many=True)
    global_metrics = BusinessSimulationGlobalMetricsSerializer()
    counters = BusinessSimulationCountersSerializer()


class AdminWalletOperationRequestSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    scenario = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=64)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminWalletOperationResponseSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deposits = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_referral_rewards = serializers.DecimalField(max_digits=14, decimal_places=2)
    transaction_id = serializers.IntegerField()
    transaction_type = serializers.CharField()
    transaction_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    scenario_tag = serializers.CharField(allow_blank=True)
    message = serializers.CharField()
