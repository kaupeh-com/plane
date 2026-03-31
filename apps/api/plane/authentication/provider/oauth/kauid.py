# Kaupeh Pte Ltd — KauID OIDC Provider for KauTrack
# Based on the Gitea OAuth provider pattern

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytz
import requests

from plane.authentication.adapter.oauth import OauthAdapter
from plane.license.utils.instance_value import get_configuration_value
from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)


def _generate_pkce_pair():
    """Generate a PKCE code_verifier and S256 code_challenge."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


class KauIDOAuthProvider(OauthAdapter):
    provider = "kauid"
    scope = "openid email profile"

    def __init__(self, request, code=None, state=None, callback=None, code_verifier=None):
        (KAUID_CLIENT_ID, KAUID_CLIENT_SECRET, KAUID_HOST) = get_configuration_value(
            [
                {
                    "key": "KAUID_CLIENT_ID",
                    "default": os.environ.get("KAUID_CLIENT_ID"),
                },
                {
                    "key": "KAUID_CLIENT_SECRET",
                    "default": os.environ.get("KAUID_CLIENT_SECRET"),
                },
                {
                    "key": "KAUID_HOST",
                    "default": os.environ.get("KAUID_HOST"),
                },
            ]
        )

        if not (KAUID_CLIENT_ID and KAUID_CLIENT_SECRET and KAUID_HOST):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["KAUID_NOT_CONFIGURED"],
                error_message="KAUID_NOT_CONFIGURED",
            )

        KAUID_HOST = KAUID_HOST.rstrip("/")

        # KauID OIDC endpoints (tenant-scoped under /kauid/)
        self.token_url = f"{KAUID_HOST}/kauid/oauth/token"
        self.userinfo_url = f"{KAUID_HOST}/kauid/oauth/userinfo"

        client_id = KAUID_CLIENT_ID
        client_secret = KAUID_CLIENT_SECRET

        redirect_uri = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}/auth/kauid/callback/"
        url_params = {
            "client_id": client_id,
            "scope": self.scope,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if code is None:
            # Initiate path: generate PKCE pair and embed challenge in auth URL.
            # The verifier is stored on the instance so the view can persist it
            # in the session for retrieval during the callback.
            self.code_verifier, code_challenge = _generate_pkce_pair()
            url_params["code_challenge"] = code_challenge
            url_params["code_challenge_method"] = "S256"
        else:
            # Callback path: receive the verifier that was stored in the session.
            self.code_verifier = code_verifier

        auth_url = f"{KAUID_HOST}/kauid/oauth/authorize?{urlencode(url_params)}"

        super().__init__(
            request,
            self.provider,
            client_id,
            self.scope,
            redirect_uri,
            auth_url,
            self.token_url,
            self.userinfo_url,
            client_secret,
            code,
            callback=callback,
        )

    def set_token_data(self):
        data = {
            "code": self.code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        if self.code_verifier:
            data["code_verifier"] = self.code_verifier
        headers = {"Accept": "application/json"}
        token_response = self.get_user_token(data=data, headers=headers)
        super().set_token_data(
            {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token", None),
                "access_token_expired_at": (
                    datetime.now(tz=pytz.utc) + timedelta(seconds=token_response.get("expires_in"))
                    if token_response.get("expires_in")
                    else None
                ),
                "refresh_token_expired_at": None,
                "id_token": token_response.get("id_token", ""),
            }
        )

    def set_user_data(self):
        user_info_response = self.get_user_response()

        email = user_info_response.get("email")
        if not email:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["KAUID_OAUTH_PROVIDER_ERROR"],
                error_message="KAUID_OAUTH_PROVIDER_ERROR: No email in userinfo response",
            )

        # KauID returns name as a single field
        full_name = user_info_response.get("name", "")
        name_parts = full_name.split(" ", 1) if full_name else [""]
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        super().set_user_data(
            {
                "email": email,
                "user": {
                    "provider_id": str(user_info_response.get("sub", user_info_response.get("gid", ""))),
                    "email": email,
                    "avatar": user_info_response.get("picture", ""),
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_password_autoset": True,
                },
            }
        )
