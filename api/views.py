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
    process_member_deposit,
    simulate_demo_deposits_for_amir_alfira,
    simulate_business_model,
)
from .serializers import (
    MessageSerializer,
    MemberSerializer,
    RegistrationSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    MeUpdateSerializer,
    ProfileStatsSerializer,
    ReferralNodeSerializer,
    ReferralRewardSerializer,
    ReferralRewardsSummarySerializer,
    AdminMemberSerializer,
    AdminCreateMemberSerializer,
    AdminResetMemberPasswordSerializer,
    ReferralEventAdminSerializer,
    AdminStatsOverviewSerializer,
    AdminCreateReferralEventSerializer,
    TestSimulateDepositsResponseSerializer,
    SimulateDemoDepositsRequestSerializer,
    SimulateDemoDepositsResponseSerializer,
    WithdrawalRequestSerializer,
    WalletTransactionSerializer,
    WalletSummarySerializer,
    WalletDepositRequestSerializer,
    WalletSpendRequestSerializer,
    BusinessSimulationRequestSerializer,
    BusinessSimulationResponseSerializer,
)

# ... existing view classes remain unchanged ...

class SimulateDemoDepositsView(APIView):
    """Test-only endpoint to simulate demo deposits for Amir and Alfirа and show Timur earnings.

    The endpoint:
    - Ensures that Амир и Альфира существуют и привязаны к Тимуру как прямому рефереру.
    - Для каждого из них создаёт (или переиспользует) депозит на указанную сумму
      через стандартный `process_member_deposit`.
    - Возвращает информацию о депозитах игроков и денежный баланс Тимура
      до и после операции.
    """

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]

    @extend_schema(
        request=SimulateDemoDepositsRequestSerializer,
        responses={200: SimulateDemoDepositsResponseSerializer},
        description=(
            "Тестовый админский эндпоинт, который моделирует покупку турнирных фишек "
            "(депозиты) по 2000 ₽ для игроков «Амир» и «Альфира» и показывает, "
            "сколько заработал инфлюенсер Тимур. При повторных вызовах переиспользует "
            "существующие тестовые депозиты, не удваивая начисления."
        ),
    )
    def post(self, request):
        request_serializer = SimulateDemoDepositsRequestSerializer(
            data=request.data or {}
        )
        request_serializer.is_valid(raise_exception=True)

        amount = request_serializer.validated_data.get("amount") or 2000

        try:
            result = simulate_demo_deposits_for_amir_alfira(amount=amount)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = SimulateDemoDepositsResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class BusinessModelSimulationView(APIView):
    """Test-only endpoint to run the influencer business model simulation."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]

    @extend_schema(
        request=BusinessSimulationRequestSerializer,
        responses={200: BusinessSimulationResponseSerializer},
        description=(
            "Тестовый эндпоинт, который разворачивает трёх инфлюенсеров с сотней игроков, "
            "запускает детерминированные пополнения через process_member_deposit и "
            "операции кошелька, а затем возвращает метрики по инфлюенсерам и глобальные итоги."
        ),
    )
    def post(self, request):
        serializer = BusinessSimulationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        seed = serializer.validated_data.get("seed") or 2024
        result = simulate_business_model(seed=seed)
        response_serializer = BusinessSimulationResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
