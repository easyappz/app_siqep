from typing import Optional, Tuple

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from .models import MemberAuthToken


class MemberTokenAuthentication(BaseAuthentication):
    """Token-based authentication for Member instances.

    Clients should authenticate by passing the token key in the
    "Authorization" HTTP header, prepended with the string "Token":

        Authorization: Token <key>
    """

    keyword = "Token"

    def authenticate(self, request: Request) -> Optional[Tuple[object, None]]:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2:
            return None

        if parts[0] != self.keyword:
            return None

        token_key = parts[1].strip()
        if not token_key:
            return None

        try:
            token = MemberAuthToken.objects.select_related("member").get(key=token_key)
        except MemberAuthToken.DoesNotExist:
            return None

        member = token.member
        return member, None
