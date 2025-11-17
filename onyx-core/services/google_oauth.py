"""
Google OAuth2 Service

This module handles Google OAuth2 authentication flow for Google Drive access.
"""

import os
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
import logging

from utils.encryption import get_encryption_service
from utils.database import get_db_service

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for Google OAuth2 authentication"""

    def __init__(self):
        """Initialize OAuth service"""
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:3000/api/auth/google/callback"
        )

        self.scopes = [
            "https://www.googleapis.com/auth/drive",  # Full Drive access for doc creation/editing
            "https://www.googleapis.com/auth/documents",  # Google Docs API for doc creation
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ]

        if not self.client_id or not self.client_secret:
            logger.warning(
                "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set. "
                "OAuth flow will fail."
            )

        self.encryption_service = get_encryption_service()
        self.db_service = get_db_service()

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
            )

            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=state,
                prompt="consent",  # Force consent to get refresh token
            )

            logger.info("Generated OAuth authorization URL")
            return auth_url

        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise

    def exchange_code_for_tokens(
        self, authorization_code: str
    ) -> Tuple[str, str, datetime, List[str]]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            authorization_code: Authorization code from callback

        Returns:
            Tuple of (access_token, refresh_token, expiry, scopes)

        Raises:
            Exception: If token exchange fails
        """
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri],
                    }
                },
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
            )

            # Exchange code for tokens
            flow.fetch_token(code=authorization_code)

            # Extract credentials
            creds = flow.credentials
            access_token = creds.token
            refresh_token = creds.refresh_token

            if not refresh_token:
                logger.warning(
                    "No refresh token received. User may need to re-authorize."
                )
                raise ValueError("No refresh token received from Google")

            # Calculate expiry
            expiry = datetime.now() + timedelta(seconds=3600)  # Default 1 hour
            if creds.expiry:
                expiry = creds.expiry

            scopes_list = list(creds.scopes) if creds.scopes else self.scopes

            logger.info("Successfully exchanged authorization code for tokens")
            return access_token, refresh_token, expiry, scopes_list

        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            raise

    def store_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scopes: List[str],
    ) -> bool:
        """
        Encrypt and store OAuth tokens

        Args:
            user_id: User UUID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expiry: Token expiry timestamp
            scopes: List of granted scopes

        Returns:
            True if successful
        """
        try:
            # Encrypt tokens
            encrypted_access, encrypted_refresh = (
                self.encryption_service.encrypt_token_pair(access_token, refresh_token)
            )

            # Store in database
            success = self.db_service.store_oauth_tokens(
                user_id=user_id,
                provider="google_drive",
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_expiry=expiry,
                scopes=scopes,
            )

            if success:
                logger.info(f"Stored OAuth tokens for user {user_id}")
            else:
                logger.error(f"Failed to store OAuth tokens for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to store tokens: {e}")
            return False

    def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Retrieve and decrypt OAuth credentials for a user

        Args:
            user_id: User UUID

        Returns:
            Google Credentials object or None if not found

        Raises:
            Exception: If decryption fails
        """
        try:
            # Retrieve encrypted tokens from database
            token_data = self.db_service.get_oauth_tokens(user_id, "google_drive")

            if not token_data:
                logger.warning(f"No OAuth tokens found for user {user_id}")
                return None

            # Decrypt tokens
            access_token, refresh_token = self.encryption_service.decrypt_token_pair(
                token_data["encrypted_access_token"],
                token_data["encrypted_refresh_token"],
            )

            # Create credentials object
            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=token_data.get("scopes", self.scopes),
            )

            # Set expiry
            if token_data.get("token_expiry"):
                creds.expiry = token_data["token_expiry"]

            # Refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info(f"Access token expired for user {user_id}, refreshing...")
                creds.refresh(Request())

                # Store refreshed tokens
                new_expiry = datetime.now() + timedelta(seconds=3600)
                if creds.expiry:
                    new_expiry = creds.expiry

                self.store_tokens(
                    user_id=user_id,
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expiry=new_expiry,
                    scopes=list(creds.scopes) if creds.scopes else self.scopes,
                )

                logger.info(f"Refreshed OAuth tokens for user {user_id}")

            return creds

        except Exception as e:
            logger.error(f"Failed to retrieve credentials for user {user_id}: {e}")
            return None

    def revoke_tokens(self, user_id: str) -> bool:
        """
        Revoke OAuth tokens for a user (disconnect Google Drive)

        Args:
            user_id: User UUID

        Returns:
            True if successful
        """
        try:
            # Delete tokens from database
            success = self.db_service.delete_oauth_tokens(user_id, "google_drive")

            if success:
                logger.info(f"Revoked OAuth tokens for user {user_id}")
            else:
                logger.error(f"Failed to revoke OAuth tokens for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to revoke tokens: {e}")
            return False

    def is_authenticated(self, user_id: str) -> bool:
        """
        Check if user has valid OAuth credentials

        Args:
            user_id: User UUID

        Returns:
            True if authenticated
        """
        try:
            creds = self.get_credentials(user_id)
            return creds is not None and creds.valid
        except Exception:
            return False


# Global OAuth service instance
_oauth_service = None


def get_oauth_service() -> GoogleOAuthService:
    """Get or create OAuth service instance"""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = GoogleOAuthService()
    return _oauth_service
