from django.contrib import admin

from .models import (
    Member,
    ReferralEvent,
    MemberAuthToken,
    ReferralRelation,
    RankRule,
    WalletTransaction,
)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "phone",
        "email",
        "user_type",
        "rank",
        "is_influencer",
        "is_admin",
        "referrer",
        "referred_by",
        "v_coins_balance",
        "cash_balance",
        "influencer_since",
        "created_at",
    )
    list_filter = (
        "user_type",
        "rank",
        "is_influencer",
        "is_admin",
        "created_at",
    )
    search_fields = ("first_name", "last_name", "phone", "email")
    readonly_fields = (
        "referral_code",
        "created_at",
        "total_bonus_points",
        "total_money_earned",
        "influencer_since",
    )
    ordering = ("-created_at",)


@admin.register(ReferralEvent)
class ReferralEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "referrer",
        "referred",
        "bonus_amount",
        "money_amount",
        "deposit_amount",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "referrer__first_name",
        "referrer__last_name",
        "referrer__phone",
        "referred__first_name",
        "referred__last_name",
        "referred__phone",
    )
    ordering = ("-created_at",)


@admin.register(MemberAuthToken)
class MemberAuthTokenAdmin(admin.ModelAdmin):
    list_display = ("short_key", "member", "created")
    search_fields = ("key", "member__phone", "member__email")
    readonly_fields = ("key", "created")
    ordering = ("-created",)

    def short_key(self, obj):
        if len(obj.key) <= 8:
            return obj.key
        return f"{obj.key[:8]}..."

    short_key.short_description = "Key"


@admin.register(ReferralRelation)
class ReferralRelationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ancestor",
        "descendant",
        "level",
        "has_paid_first_bonus",
    )
    list_filter = ("level", "has_paid_first_bonus")
    search_fields = (
        "ancestor__first_name",
        "ancestor__last_name",
        "ancestor__phone",
        "descendant__first_name",
        "descendant__last_name",
        "descendant__phone",
    )
    ordering = ("ancestor_id", "level")


@admin.register(RankRule)
class RankRuleAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "required_referrals",
        "player_depth_bonus_multiplier",
        "influencer_depth_bonus_multiplier",
    )
    search_fields = ("rank",)
    ordering = ("required_referrals",)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "member",
        "type",
        "amount",
        "balance_after",
        "created_at",
    )
    list_filter = ("type", "created_at")
    search_fields = (
        "member__first_name",
        "member__last_name",
        "member__phone",
    )
    readonly_fields = (
        "member",
        "type",
        "amount",
        "balance_after",
        "description",
        "meta",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
