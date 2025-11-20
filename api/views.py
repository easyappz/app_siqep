from datetime import timedelta, datetime

from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import MemberTokenAuthentication
from .models import Member, ReferralEvent, MemberAuthToken
from .permissions import IsAdminMember
from .serializers import (
    MessageSerializer,
    MemberSerializer,
    RegistrationSerializer,
    LoginSerializer,
    ProfileStatsSerializer,
    AdminMemberSerializer,
    AdminCreateMemberSerializer,
    ReferralEventAdminSerializer,
    AdminStatsOverviewSerializer,
    AdminCreateReferralEventSerializer,
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
        description="Регистрация нового пользователя по номеру телефона.",
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

        # Top referrers
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
                    "total_bonus_points": item["total_bonus_points"] or 0,
                    "total_money_earned": item["total_money_earned"] or 0,
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
