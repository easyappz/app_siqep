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
from rest_framework.exceptions import PermissionDenied

from .authentication import MemberTokenAuthentication
from .models import Member, ReferralEvent, MemberAuthToken, ReferralReward, ReferralRelation
from .permissions import IsAdminMember
from .referral_utils import process_member_deposit, simulate_demo_deposits_for_amir_alfira
from .serializers import (
    MessageSerializer,
    MemberSerializer,
    RegistrationSerializer,
    LoginSerializer,
    ProfileStatsSerializer,
    ReferralNodeSerializer,
    ReferralRewardSerializer,
    ReferralRewardsSummarySerializer,
    AdminMemberSerializer,
    AdminCreateMemberSerializer,
    ReferralEventAdminSerializer,
    AdminStatsOverviewSerializer,
    AdminCreateReferralEventSerializer,
    TestSimulateDepositsResponseSerializer,
    SimulateDemoDepositsRequestSerializer,
    SimulateDemoDepositsResponseSerializer,
)


class HelloView(APIView):
    """A simple API endpoint that returns a greeting message."""

    @extend_schema(
        responses={200: MessageSerializer},
        description="Get a hello world message",
    )
    def get(self, request):
        data = {"message": "Hello!", "timestamp": timezone.now()}
        serializer = MessageSerializer(data)
        return Response(serializer.data)


class RegisterView(APIView):
    """Public endpoint for member registration."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=RegistrationSerializer,
        responses={201: MemberSerializer},
        description=(
            "Регистрация нового пользователя по номеру телефона с опциональным реферальным кодом. "
            "При наличии реферального кода создаются связи в ранговой реферальной системе, "
            "а финансовые бонусы начисляются после первого турнира/депозита нового игрока."
        ),
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member: Member = serializer.save()
        token = MemberAuthToken.create_for_member(member)

        response_data = {
            "member": MemberSerializer(member).data,
            "token": token.key,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Public endpoint for login by phone and password."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: MemberSerializer},
        description="Авторизация пользователя по номеру телефона и паролю.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member: Member = serializer.validated_data["member"]
        token = MemberAuthToken.create_for_member(member)

        response_data = {
            "member": MemberSerializer(member).data,
            "token": token.key,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class MeView(APIView):
    """Return profile of the currently authenticated member."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MemberSerializer},
        description="Получить данные текущего пользователя.",
    )
    def get(self, request):
        serializer = MemberSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileStatsView(APIView):
    """Return referral statistics for the current member."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ProfileStatsSerializer},
        description=(
            "Получить статистику реферальной программы для текущего пользователя, "
            "включая количество рефералов, бонусы, историю начислений и график регистраций."
        ),
    )
    def get(self, request):
        member: Member = request.user

        events_qs = ReferralEvent.objects.filter(referrer=member).select_related(
            "referred"
        )

        total_referrals = events_qs.count()

        # active_referrals: referrals created within the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_referrals = events_qs.filter(created_at__gte=thirty_days_ago).count()

        total_bonus_points = member.total_bonus_points
        total_money_earned = member.total_money_earned

        history_list = []
        for event in events_qs.order_by("-created_at"):
            referred = event.referred
            referred_name = f"{referred.first_name} {referred.last_name}".strip()
            history_list.append(
                {
                    "date": event.created_at.date(),
                    "referred_name": referred_name,
                    "bonus_amount": event.bonus_amount,
                    "money_amount": event.money_amount,
                }
            )

        date_counts = (
            events_qs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        registrations_chart = [
            {"date": item["date"], "count": item["count"]}
            for item in date_counts
        ]

        stats_data = {
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "total_bonus_points": total_bonus_points,
            "total_money_earned": total_money_earned,
            "history": history_list,
            "registrations_chart": registrations_chart,
        }

        serializer = ProfileStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReferralTreeView(APIView):
    """Return ranked referral tree descendants for the current or specified member.

    Uses ReferralRelation to expose all descendants with their depth and activation status.
    """

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_target_member(self, request) -> Member:
        member: Member = request.user
        member_id = request.query_params.get("member_id")
        if member_id:
            if not member.is_admin:
                raise PermissionDenied(
                    "Просматривать дерево рефералов других пользователей может только администратор."
                )
            try:
                member_id_int = int(member_id)
            except ValueError:
                raise Http404("Пользователь не найден.")
            try:
                member = Member.objects.get(pk=member_id_int)
            except Member.DoesNotExist:
                raise Http404("Пользователь не найден.")
        return member

    def get(self, request):
        root_member = self._get_target_member(request)

        relations = (
            ReferralRelation.objects.select_related("descendant")
            .filter(ancestor=root_member)
            .order_by("level", "descendant_id")
        )

        nodes = []
        for relation in relations:
            descendant = relation.descendant
            if descendant is None:
                continue
            nodes.append(
                {
                    "descendant_id": descendant.id,
                    "level": relation.level,
                    "has_paid_first_bonus": relation.has_paid_first_bonus,
                    "username": descendant.phone,
                    "user_type": descendant.user_type,
                    "rank": descendant.rank,
                    "is_active_referral": bool(relation.has_paid_first_bonus),
                }
            )

        serializer = ReferralNodeSerializer(nodes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReferralRewardsView(APIView):
    """Return detailed referral rewards and summary for the current or specified member."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_target_member(self, request) -> Member:
        member: Member = request.user
        member_id = request.query_params.get("member_id")
        if member_id:
            if not member.is_admin:
                raise PermissionDenied(
                    "Просматривать вознаграждения других пользователей может только администратор."
                )
            try:
                member_id_int = int(member_id)
            except ValueError:
                raise Http404("Пользователь не найден.")
            try:
                member = Member.objects.get(pk=member_id_int)
            except Member.DoesNotExist:
                raise Http404("Пользователь не найден.")
        return member

    def get(self, request):
        member = self._get_target_member(request)
        rewards_qs = ReferralReward.objects.filter(member=member).order_by("-created_at")
        rewards = list(rewards_qs)

        rewards_serializer = ReferralRewardSerializer(rewards, many=True)

        total_stack_count = sum(
            (
                reward.stack_count
                for reward in rewards
                if reward.reward_type == ReferralReward.RewardType.PLAYER_STACK
            ),
            0,
        )

        total_first_tournament_amount = sum(
            (
                reward.amount_rub
                for reward in rewards
                if reward.reward_type
                == ReferralReward.RewardType.INFLUENCER_FIRST_TOURNAMENT
            ),
            Decimal("0.00"),
        )

        total_deposit_percent_amount = sum(
            (
                reward.amount_rub
                for reward in rewards
                if reward.reward_type
                == ReferralReward.RewardType.INFLUENCER_DEPOSIT_PERCENT
            ),
            Decimal("0.00"),
        )

        total_influencer_amount = (
            total_first_tournament_amount + total_deposit_percent_amount
        )

        summary_data = {
            "total_stack_count": total_stack_count,
            "total_influencer_amount": total_influencer_amount,
            "total_first_tournament_amount": total_first_tournament_amount,
            "total_deposit_percent_amount": total_deposit_percent_amount,
        }

        summary_serializer = ReferralRewardsSummarySerializer(summary_data)

        response_data = {
            "rewards": rewards_serializer.data,
            "summary": summary_serializer.data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


# ============================
# Admin-facing views
# ============================


class AdminMemberListCreateView(generics.ListCreateAPIView):
    """List all members and create new ones (including influencers/admins)."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]
    queryset = Member.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminCreateMemberSerializer
        return AdminMemberSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        output_serializer = AdminMemberSerializer(
            member,
            context=self.get_serializer_context(),
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class AdminMemberDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a single member from admin panel."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]
    queryset = Member.objects.all()
    serializer_class = AdminMemberSerializer
    lookup_field = "pk"


class AdminReferralEventListView(generics.ListCreateAPIView):
    """List referral events for admin panel with optional filtering and allow creation."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminCreateReferralEventSerializer
        return ReferralEventAdminSerializer

    def get_queryset(self):
        qs = ReferralEvent.objects.select_related("referrer", "referred").all().order_by(
            "-created_at"
        )

        params = self.request.query_params

        referrer_id = params.get("referrer_id")
        if referrer_id:
            try:
                referrer_id_int = int(referrer_id)
                qs = qs.filter(referrer_id=referrer_id_int)
            except ValueError:
                pass

        is_influencer = params.get("is_influencer")
        if is_influencer is not None and is_influencer != "":
            value = is_influencer.lower()
            if value in ("true", "1", "yes"):
                qs = qs.filter(referrer__is_influencer=True)
            elif value in ("false", "0", "no"):
                qs = qs.filter(referrer__is_influencer=False)

        from_date = params.get("from_date")
        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                qs = qs.filter(created_at__date__gte=from_dt)
            except ValueError:
                pass

        to_date = params.get("to_date")
        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                qs = qs.filter(created_at__date__lte=to_dt)
            except ValueError:
                pass

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        output_serializer = ReferralEventAdminSerializer(
            event,
            context=self.get_serializer_context(),
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class AdminStatsOverviewView(APIView):
    """Provide aggregated statistics for the admin dashboard."""

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]

    def get(self, request):
        # Registrations by day
        registrations_qs = (
            Member.objects.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        registrations_by_day = [
            {"date": item["date"], "count": item["count"]}
            for item in registrations_qs
        ]

        # Top referrers (based on ReferralEvent analytics and aggregated rewards)
        referrer_stats = (
            ReferralEvent.objects.values("referrer")
            .annotate(
                total_referrals=Count("id"),
                total_bonus_points=Sum("bonus_amount"),
                total_money_earned=Sum("money_amount"),
            )
            .order_by("-total_referrals")[:10]
        )

        referrer_ids = [item["referrer"] for item in referrer_stats]
        members_map = Member.objects.in_bulk(referrer_ids)

        top_referrers = []
        for item in referrer_stats:
            member = members_map.get(item["referrer"])
            if not member:
                continue
            top_referrers.append(
                {
                    "id": member.id,
                    "first_name": member.first_name,
                    "last_name": member.last_name,
                    "is_influencer": member.is_influencer,
                    "total_referrals": item["total_referrals"] or 0,
                    "total_bonus_points": member.total_bonus_points,
                    "total_money_earned": member.total_money_earned,
                }
            )

        # Income by source: based on sum of deposit_amount instead of fixed income per client
        total_income_data = ReferralEvent.objects.aggregate(
            total=Sum("deposit_amount")
        )
        total_income = total_income_data["total"] or 0

        influencer_income_data = ReferralEvent.objects.filter(
            referrer__is_influencer=True
        ).aggregate(total=Sum("deposit_amount"))
        income_from_influencers = influencer_income_data["total"] or 0

        income_from_regular_users = total_income - income_from_influencers

        income_by_source = {
            "total_income": total_income,
            "income_from_influencers": income_from_influencers,
            "income_from_regular_users": income_from_regular_users,
        }

        overview_data = {
            "registrations_by_day": registrations_by_day,
            "top_referrers": top_referrers,
            "income_by_source": income_by_source,
        }

        serializer = AdminStatsOverviewSerializer(overview_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestSimulateDepositsView(APIView):
    """Test-only endpoint to simulate deposits for Amir and Alfirа.

    Creates the members if they do not exist and processes a deposit for each
    using the same referral logic as real deposits.
    """

    authentication_classes = [MemberTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminMember]

    @extend_schema(
        request=None,
        responses={200: TestSimulateDepositsResponseSerializer},
        description=(
            "Тестовый эндпоинт для администраторов: создаёт (при необходимости) "
            "пользователей «Амир» и «Альфира» и проводит для каждого депозит "
            "на указанную сумму (по умолчанию 2000 ₽), применяя все стандартные "
            "реферальные начисления, включая бонус за первый турнир/депозит и "
            "10% для инфлюенсера от депозитов."
        ),
    )
    def post(self, request):
        # Determine deposit amount from request body (optional)
        default_amount = 2000
        raw_amount = request.data.get("amount", default_amount)
        try:
            amount_int = int(raw_amount)
        except (TypeError, ValueError):
            amount_int = default_amount
        if amount_int <= 0:
            amount_int = default_amount

        members_definition = [
            {"first_name": "Амир", "last_name": "Тестов", "phone": "+79990000001"},
            {"first_name": "Альфира", "last_name": "Тестова", "phone": "+79990000002"},
        ]

        deposits = []

        for item in members_definition:
            member = Member.objects.filter(phone=item["phone"]).first()
            if member is None:
                member = Member(
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    phone=item["phone"],
                    email=None,
                    is_influencer=False,
                    is_admin=False,
                )
                member.set_password("test1234")
                member.save()

            before_v_coins = member.v_coins_balance
            before_cash = member.cash_balance

            before_relations = list(
                ReferralRelation.objects.filter(
                    descendant=member,
                    has_paid_first_bonus=True,
                ).values("ancestor_id", "level")
            )

            process_member_deposit(member, Decimal(amount_int))
            member.refresh_from_db()

            after_relations = list(
                ReferralRelation.objects.filter(
                    descendant=member,
                    has_paid_first_bonus=True,
                ).values("ancestor_id", "level")
            )

            before_set = {(r["ancestor_id"], r["level"]) for r in before_relations}
            after_set = {(r["ancestor_id"], r["level"]) for r in after_relations}
            new_pairs = after_set - before_set

            referral_changes = [
                {"ancestor_id": ancestor_id, "level": level}
                for (ancestor_id, level) in sorted(new_pairs, key=lambda x: (x[1], x[0]))
            ]

            deposits.append(
                {
                    "member": MemberSerializer(member).data,
                    "amount": amount_int,
                    "v_coins_balance_before": before_v_coins,
                    "cash_balance_before": before_cash,
                    "v_coins_balance_after": member.v_coins_balance,
                    "cash_balance_after": member.cash_balance,
                    "referral_changes": referral_changes,
                }
            )

        response_data = {
            "status": "ok",
            "deposits": deposits,
        }

        serializer = TestSimulateDepositsResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
