from datetime import timedelta

from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import MemberTokenAuthentication
from .models import Member, ReferralEvent, MemberAuthToken
from .serializers import (
    MessageSerializer,
    MemberSerializer,
    RegistrationSerializer,
    LoginSerializer,
    ProfileStatsSerializer,
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
