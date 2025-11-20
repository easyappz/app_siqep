from django.contrib import admin

from .models import Member, ReferralEvent, MemberAuthToken


admin.site.site_header = "Панель администратора"
administrative_site_title = "Администрирование сайта"
admin.site.site_title = administrative_site_title
admin.site.index_title = "Управление данными"


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "phone",
        "email",
        "is_influencer",
        "is_admin",
        "referred_by",
        "created_at",
    )
    list_filter = ("is_influencer", "is_admin", "created_at")
    search_fields = ("first_name", "last_name", "phone", "email")
    readonly_fields = (
        "referral_code",
        "created_at",
        "total_bonus_points",
        "total_money_earned",
    )
    ordering = ("-created_at",)
    list_editable = ("is_influencer", "is_admin")
    actions = ("mark_as_influencer", "unmark_as_influencer")

    @admin.action(description="Отметить как инфлюенсера")
    def mark_as_influencer(self, request, queryset):
        queryset.update(is_influencer=True)

    @admin.action(description="Снять метку инфлюенсера")
    def unmark_as_influencer(self, request, queryset):
        queryset.update(is_influencer=False)


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

    short_key.short_description = "Ключ"
