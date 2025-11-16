"""
Slack API Client

This module provides Slack API integration with authentication, rate limiting,
and error handling for message retrieval and channel management.
"""

import os
import asyncio
import aiofiles
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError, SlackRateLimitError
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient

from utils.encryption import encrypt_data, decrypt_data
from utils.database import get_db_service
from services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SlackClientService:
    """Service for Slack API operations with rate limiting and error handling"""

    def __init__(self):
        """Initialize Slack client service"""
        self.rate_limiter = RateLimiter(
            max_requests=50,  # Slack tier 4 limit
            time_window=60,   # per minute
        )
        self.db_service = get_db_service()

    async def create_client(self, bot_token: str) -> AsyncWebClient:
        """
        Create authenticated Slack client

        Args:
            bot_token: Slack Bot Token (xoxb-...)

        Returns:
            Authenticated AsyncWebClient instance
        """
        try:
            client = AsyncWebClient(token=bot_token, retry_exponential_backoff=True)

            # Test authentication
            auth_response = await client.auth_test()
            logger.info(f"Slack client authenticated for team: {auth_response['team']}")

            return client

        except SlackApiError as e:
            logger.error(f"Slack authentication failed: {e.response['error']}")
            raise ValueError(f"Invalid Slack token: {e.response['error']}")

    async def validate_token(self, bot_token: str) -> Dict[str, Any]:
        """
        Validate Slack bot token and get workspace info

        Args:
            bot_token: Slack Bot Token

        Returns:
            Dictionary with authentication info or raises ValueError
        """
        try:
            client = await self.create_client(bot_token)
            auth_response = await client.auth_test()

            # Get team info
            team_info = await client.team_info()

            # Get bot info
            bot_info = await client.auth_teams_list()

            return {
                "ok": True,
                "team_id": auth_response["team"],
                "team_name": team_info["team"]["name"],
                "bot_user_id": auth_response["user_id"],
                "bot_name": auth_response["user"],
                "url": auth_response["url"],
                "bot_scopes": bot_info.get("scopes", []),
            }

        except SlackApiError as e:
            logger.error(f"Token validation failed: {e.response['error']}")
            return {"ok": False, "error": e.response["error"]}
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {"ok": False, "error": str(e)}

    async def get_channels(self, client: AsyncWebClient) -> List[Dict[str, Any]]:
        """
        Get all accessible channels for the bot

        Args:
            client: Authenticated Slack client

        Returns:
            List of channel information
        """
        channels = []
        cursor = None

        try:
            while True:
                # Check rate limit before making request
                await self.rate_limiter.acquire()

                if cursor:
                    response = await client.conversations_list(
                        cursor=cursor,
                        types="public_channel,private_channel",
                        exclude_archived=False
                    )
                else:
                    response = await client.conversations_list(
                        types="public_channel,private_channel",
                        exclude_archived=False
                    )

                channels.extend(response["channels"])

                if not response.get("has_more") or not response.get("response_metadata", {}).get("next_cursor"):
                    break

                cursor = response["response_metadata"]["next_cursor"]

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)

            logger.info(f"Retrieved {len(channels)} channels")
            return channels

        except SlackRateLimitError as e:
            logger.warning(f"Rate limited while fetching channels: {e}")
            # Add delay and retry once
            await asyncio.sleep(e.retry_after)
            return await self.get_channels(client)

        except SlackApiError as e:
            logger.error(f"Failed to fetch channels: {e.response['error']}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching channels: {e}")
            raise

    async def check_channel_access(self, client: AsyncWebClient, channel_id: str) -> bool:
        """
        Check if bot has access to a channel

        Args:
            client: Authenticated Slack client
            channel_id: Slack channel ID

        Returns:
            True if bot can access channel
        """
        try:
            await self.rate_limiter.acquire()

            # Try to get channel info
            response = await client.conversations_info(channel=channel_id)
            channel = response["channel"]

            # Check if bot is member (for private channels)
            if channel.get("is_private") or channel.get("is_mpim"):
                members_response = await client.conversations_members(channel=channel_id, limit=1)
                # Check if bot is in the channel
                return len(members_response.get("members", [])) > 0

            return True

        except SlackApiError as e:
            if e.response["error"] in ["not_in_channel", "restricted_action"]:
                logger.info(f"No access to channel {channel_id}: {e.response['error']}")
                return False
            logger.error(f"Error checking channel access: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error checking channel access: {e}")
            return False

    async def get_messages(
        self,
        client: AsyncWebClient,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a channel with pagination

        Args:
            client: Authenticated Slack client
            channel_id: Slack channel ID
            oldest: Get messages newer than this timestamp
            latest: Get messages older than this timestamp
            limit: Maximum number of messages to retrieve

        Returns:
            List of message objects
        """
        messages = []
        cursor = None

        try:
            while len(messages) < limit:
                # Check rate limit
                await self.rate_limiter.acquire()

                # Calculate remaining limit
                remaining_limit = min(limit - len(messages), 200)  # Slack API limit per request

                if cursor:
                    response = await client.conversations_history(
                        channel=channel_id,
                        cursor=cursor,
                        limit=remaining_limit,
                        oldest=oldest,
                        latest=latest
                    )
                else:
                    response = await client.conversations_history(
                        channel=channel_id,
                        limit=remaining_limit,
                        oldest=oldest,
                        latest=latest
                    )

                if not response.get("messages"):
                    break

                messages.extend(response["messages"])

                if not response.get("has_more") or not response.get("response_metadata", {}).get("next_cursor"):
                    break

                cursor = response["response_metadata"]["next_cursor"]

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)

            logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")
            return messages

        except SlackRateLimitError as e:
            logger.warning(f"Rate limited while fetching messages: {e}")
            await asyncio.sleep(e.retry_after)
            return await self.get_messages(client, channel_id, oldest, latest, limit)

        except SlackApiError as e:
            logger.error(f"Failed to fetch messages from {channel_id}: {e.response['error']}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching messages: {e}")
            raise

    async def get_thread_replies(
        self,
        client: AsyncWebClient,
        channel_id: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """
        Get all replies in a thread

        Args:
            client: Authenticated Slack client
            channel_id: Slack channel ID
            thread_ts: Thread timestamp

        Returns:
            List of thread reply messages
        """
        replies = []
        cursor = None

        try:
            while True:
                await self.rate_limiter.acquire()

                if cursor:
                    response = await client.conversations_replies(
                        channel=channel_id,
                        ts=thread_ts,
                        cursor=cursor,
                        limit=200
                    )
                else:
                    response = await client.conversations_replies(
                        channel=channel_id,
                        ts=thread_ts,
                        limit=200
                    )

                # Filter out the parent message (included in first position)
                thread_messages = response.get("messages", [])[1:]  # Skip parent
                replies.extend(thread_messages)

                if not response.get("has_more") or not response.get("response_metadata", {}).get("next_cursor"):
                    break

                cursor = response["response_metadata"]["next_cursor"]

                await asyncio.sleep(0.1)

            logger.info(f"Retrieved {len(replies)} replies for thread {thread_ts}")
            return replies

        except SlackRateLimitError as e:
            logger.warning(f"Rate limited while fetching thread replies: {e}")
            await asyncio.sleep(e.retry_after)
            return await self.get_thread_replies(client, channel_id, thread_ts)

        except SlackApiError as e:
            logger.error(f"Failed to fetch thread replies: {e.response['error']}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching thread replies: {e}")
            raise

    async def get_file_info(self, client: AsyncWebClient, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file information and metadata

        Args:
            client: Authenticated Slack client
            file_id: Slack file ID

        Returns:
            File information or None if not accessible
        """
        try:
            await self.rate_limiter.acquire()

            response = await client.files_info(file=file_id)

            if response.get("ok"):
                return response.get("file")
            else:
                logger.warning(f"File not accessible: {file_id}")
                return None

        except SlackApiError as e:
            if e.response["error"] in ["file_not_found", "not_authed"]:
                logger.info(f"File not accessible: {file_id} - {e.response['error']}")
                return None
            logger.error(f"Failed to get file info: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error getting file info: {e}")
            return None

    async def download_file(self, client: AsyncWebClient, file_url: str, file_id: str) -> Optional[bytes]:
        """
        Download file content

        Args:
            client: Authenticated Slack client
            file_url: File download URL
            file_id: File ID for logging

        Returns:
            File content as bytes or None
        """
        try:
            await self.rate_limiter.acquire()

            # Use the download URL from file info (includes auth)
            response = await client.http_client.request("GET", file_url)

            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed to download file {file_id}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None

    async def get_user_info(self, client: AsyncWebClient, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information

        Args:
            client: Authenticated Slack client
            user_id: Slack user ID

        Returns:
            User information or None
        """
        try:
            await self.rate_limiter.acquire()

            response = await client.users_info(user=user_id)

            if response.get("ok"):
                return response.get("user")
            else:
                logger.warning(f"User not found: {user_id}")
                return None

        except SlackApiError as e:
            if e.response["error"] in ["user_not_found", "not_authed"]:
                logger.info(f"User not accessible: {user_id} - {e.response['error']}")
                return None
            logger.error(f"Failed to get user info: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error getting user info: {e}")
            return None

    def extract_message_mentions(self, message: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract user and channel mentions from message text

        Args:
            message: Slack message object

        Returns:
            Dictionary with extracted mentions
        """
        mentions = {"users": [], "channels": []}
        text = message.get("text", "")

        # Extract user mentions like <@U123>
        import re
        user_pattern = r"<@(U[A-Z0-9]+)>"
        mentions["users"] = list(set(re.findall(user_pattern, text)))

        # Extract channel mentions like <#C123>
        channel_pattern = r"<#(C[A-Z0-9]+)\|[^>]*>"
        mentions["channels"] = list(set(re.findall(channel_pattern, text)))

        return mentions

    def get_oldest_timestamp_for_sync(self, minutes_ago: int = 10) -> str:
        """
        Get timestamp for incremental sync (oldest messages to retrieve)

        Args:
            minutes_ago: Number of minutes ago to sync from

        Returns:
            Slack timestamp string
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
        # Convert to Slack timestamp format
        return str(cutoff_time.timestamp())


# Global client service instance
_slack_client = None


def get_slack_client() -> SlackClientService:
    """Get or create Slack client service instance"""
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClientService()
    return _slack_client