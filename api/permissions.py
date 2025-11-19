from rest_framework.permissions import BasePermission


class IsAdminMember(BasePermission):
    """Разрешение только для админ-пользователей (Member.is_admin == True).

    Это разрешение используется для эндпоинтов админ-панели в React,
    чтобы ограничить доступ только участникам с флагом is_admin.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None:
            return False

        is_authenticated = getattr(user, "is_authenticated", False)
        if not is_authenticated:
            return False

        return bool(getattr(user, "is_admin", False))
