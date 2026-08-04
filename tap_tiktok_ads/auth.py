"""TikTok authentication."""

from hotglue_singer_sdk.authenticators import OAuthAuthenticator


class TikTokAuthenticator(OAuthAuthenticator):
    def is_token_valid(self) -> bool:
        return bool(self._tap._config.get("access_token"))
