import secrets
from datetime import timedelta, datetime
from decimal import Decimal

from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from .authentication import MemberTokenAuthentication
from .models import (
    Member,
    ReferralEvent,
    MemberAuthToken,
    ReferralReward,
    ReferralRelation,
    WithdrawalRequest,
    WalletTransaction,
)
from .permissions import IsAdminMember
from .referral_utils import (
    check_for_rank_up,
    get_rank_multiplier,
    on_member_deposit,
    on_new_user_registered,
    on_user_first_tournament_completed,
    process_member_deposit,
    simulate_business_model,
    simulate_demo_deposits_for_amir_alfira,
)
