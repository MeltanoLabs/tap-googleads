"""GoogleAds Authentication."""

import json

import requests
from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
from singer_sdk.helpers._util import utc_now


class ProxyGoogleAdsAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """API Authenticator for Proxy OAuth 2.0 flows."""

    def __init__(
        self,
        auth_endpoint: str | None = None,
        oauth_scopes: str | None = None,
        auth_headers: dict | None = None,
        auth_body: dict | None = None,
    ) -> None:
        """Create a new authenticator.

        Args:
            auth_endpoint: API username.
            oauth_scopes: API password.
            auth_headers: Headers to use for the auth request.
            auth_body: Body to use for the auth request.
        """
        super().__init__(
            auth_endpoint=auth_endpoint,
            oauth_scopes=oauth_scopes,
        )

        self._auth_headers = auth_headers
        self._auth_body = auth_body

    # Authentication and refresh
    def update_access_token(self) -> None:
        """Update `access_token` along with: `last_refreshed` and `expires_in`.

        Raises:
            RuntimeError: When OAuth login fails.
        """
        request_time = utc_now()

        token_response = requests.post(
            self.auth_endpoint,
            headers=self._auth_headers,
            data=json.dumps(self._auth_body),
        )
        try:
            token_response.raise_for_status()
            self.logger.info("OAuth authorization attempt was successful.")
        except Exception as ex:  # noqa: BLE001
            raise RuntimeError(f"Failed OAuth login, response was '{token_response.json()}'. {ex}")
        token_json = token_response.json()
        self.access_token = token_json["access_token"]
        self.expires_in = token_json["expires_in"]
        self.last_refreshed = request_time

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the GoogleAds API."""
        return {}


# The SingletonMeta metaclass makes your streams reuse the same authenticator instance.
# If this behaviour interferes with your use-case, you can remove the metaclass.
class GoogleAdsAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for GoogleAds."""

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the GoogleAds API."""
        return {}
