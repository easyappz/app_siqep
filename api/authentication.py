from typing import Optional, Tuple

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .models import MemberAuthToken


class MemberTokenAuthentication(BaseAuthentication):
    """Token-based authentication for Member instances.

    Clients should authenticate by passing the token key in the
    "Authorization" HTTP header, prepended with the string "Token":

        Authorization: Token <key>
    """

    keyword = "Token"

    def authenticate(self, request: Request) -> Optional[Tuple[object, object]]:
        """Authenticate the request using a Token in the Authorization header.

        The implementation is intentionally close to DRF's built-in
        TokenAuthentication to reliably handle different header formats
        and WSGI environments.
        """

        auth = get_authorization_header(request).split()

        if not auth:
            return None

        try:
            keyword = auth[0].decode("ascii").lower()
        except UnicodeError:
            raise AuthenticationFailed(
                "Invalid token header. Token string should not contain invalid characters."
            )

        if keyword != self.keyword.lower():
            # Different auth scheme (e.g. Basic/Bearer) – let other authenticators handle it.
            return None

        if len(auth) == 1:
            raise AuthenticationFailed(
                "Invalid token header. No credentials provided."
            )

        if len(auth) > 2:
            raise AuthenticationFailed(
                "Invalid token header. Token string should not contain spaces."
            )

        try:
            token_key = auth[1].decode("ascii")
        except UnicodeError:
            raise AuthenticationFailed(
                "Invalid token header. Token string should not contain invalid characters."
            )

        if not token_key:
            raise AuthenticationFailed(
                "Invalid token header. No credentials provided."
            )

        try:
            token = MemberAuthToken.objects.select_related("member").get(key=token_key)
        except MemberAuthToken.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")

        member = token.member
        return member, token

    def authenticate_header(self, request: Request) -> str:  # pragma: no cover - simple header
        """Return the value for the WWW-Authenticate header on 401 responses."""

        return f"{self.keyword} realm=\"api\""
