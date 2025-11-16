"""
Slack Sync Service

This module orchestrates the Slack synchronization process including
message retrieval, thread reconstruction, file processing, and embedding generation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from services.slack_client import get_slack_client
from services.message_processor import get_message_processor
from services.rag_service import get_rag_service
from utils.database import get_db_service

logger = logging.getLogger(__name__)


class SlackSyncService:
    """Service for orchestrating Slack synchronization"""

    def __init__(self):
        """Initialize Slack sync service"""
        self.slack_client = get_slack_client()
        self.message_processor = get_message_processor()
        self.rag_service = get_rag_service()
        self.db_service = get_db_service()

    async def sync_slack_workspace(
        self,
        user_id: str,
        bot_token: str,
        full_sync: bool = False,
        channel_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sync Slack workspace messages and files

        Args:
            user_id: User UUID
            bot_token: Slack Bot Token
            full_sync: If True, perform full sync instead of incremental
            channel_ids: Specific channels to sync (None for all accessible)

        Returns:
            Sync statistics and results
        """
        sync_start = datetime.now()
        stats = {
            "channels_attempted": 0,
            "channels_synced": 0,
            "channels_failed": 0,
            "messages_processed": 0,
            "messages_indexed": 0,
            "messages_failed": 0,
            "files_processed": 0,
            "files_indexed": 0,
            "files_failed": 0,
            "threads_processed": 0,
            "errors": [],
            "duration": 0,
        }

        try:
            # Create authenticated client
            client = await self.slack_client.create_client(bot_token)

            # Get authentication info
            auth_info = await self.slack_client.validate_token(bot_token)
            if not auth_info.get("ok"):
                raise ValueError(f"Invalid Slack token: {auth_info.get('error')}")

            team_id = auth_info["team_id"]
            team_name = auth_info["team_name"]
            bot_user_id = auth_info["bot_user_id"]

            logger.info(f"Starting Slack sync for team {team_name} ({team_id})")

            # Get sync state
            sync_state = self.db_service.get_slack_sync_state(user_id) or {}

            # Get channels to sync
            if channel_ids:
                # Sync specific channels
                channels_to_sync = []
                for channel_id in channel_ids:
                    try:
                        channel_info = await client.conversations_info(channel=channel_id)
                        if channel_info.get("ok"):
                            channels_to_sync.append(channel_info["channel"])
                    except Exception as e:
                        logger.error(f"Failed to get channel info for {channel_id}: {e}")
                        stats["errors"].append(f"Channel {channel_id}: {str(e)}")
            else:
                # Get all accessible channels
                all_channels = await self.slack_client.get_channels(client)
                channels_to_sync = []

                # Filter channels based on access and sync state
                for channel in all_channels:
                    # Skip archived channels unless full sync
                    if not full_sync and channel.get("is_archived"):
                        continue

                    # Check if we have access
                    has_access = await self.slack_client.check_channel_access(
                        client, channel["id"]
                    )
                    if not has_access:
                        continue

                    channels_to_sync.append(channel)

            stats["channels_attempted"] = len(channels_to_sync)

            # Sync each channel
            for channel in channels_to_sync:
                try:
                    channel_stats = await self.sync_channel(
                        client=client,
                        user_id=user_id,
                        channel_info=channel,
                        sync_state=sync_state,
                        full_sync=full_sync
                    )

                    # Update cumulative stats
                    stats["channels_synced"] += 1
                    stats["messages_processed"] += channel_stats["messages_processed"]
                    stats["messages_indexed"] += channel_stats["messages_indexed"]
                    stats["messages_failed"] += channel_stats["messages_failed"]
                    stats["files_processed"] += channel_stats["files_processed"]
                    stats["files_indexed"] += channel_stats["files_indexed"]
                    stats["files_failed"] += channel_stats["files_failed"]
                    stats["threads_processed"] += channel_stats["threads_processed"]
                    stats["errors"].extend(channel_stats.get("errors", []))

                except Exception as e:
                    logger.error(f"Failed to sync channel {channel['id']}: {e}")
                    stats["channels_failed"] += 1
                    stats["errors"].append(f"Channel {channel['id']}: {str(e)}")

                    # Update channel sync status
                    self.db_service.update_slack_channel_sync(
                        user_id=user_id,
                        channel_id=channel["id"],
                        sync_status="failed",
                        error_message=str(e)
                    )

            # Update overall sync state
            await self._update_sync_state(
                user_id=user_id,
                team_id=team_id,
                team_name=team_name,
                bot_user_id=bot_user_id,
                stats=stats,
                last_error=None if stats["errors"] == [] else "; ".join(stats["errors"][:5])
            )

            # Cleanup temp files
            self.message_processor.cleanup_temp_files()

            stats["duration"] = (datetime.now() - sync_start).total_seconds()
            stats["success"] = stats["channels_failed"] == 0 and stats["error_rate"] < 0.02
            stats["error_rate"] = stats["messages_failed"] / max(stats["messages_processed"], 1)

            logger.info(
                f"Slack sync completed: {stats['channels_synced']}/{stats['channels_attempted']} channels, "
                f"{stats['messages_indexed']} messages indexed, {stats['error_rate']:.2%} error rate"
            )

            return stats

        except Exception as e:
            logger.error(f"Slack sync failed for user {user_id}: {e}")
            stats["errors"].append(f"Sync failed: {str(e)}")
            stats["duration"] = (datetime.now() - sync_start).total_seconds()
            stats["success"] = False
            return stats

    async def sync_channel(
        self,
        client: AsyncWebClient,
        user_id: str,
        channel_info: Dict[str, Any],
        sync_state: Dict[str, Any],
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync messages from a single channel

        Args:
            client: Authenticated Slack client
            user_id: User UUID
            channel_info: Channel information
            sync_state: Current sync state
            full_sync: Whether to perform full sync

        Returns:
            Channel sync statistics
        """
        channel_id = channel_info["id"]
        channel_name = channel_info.get("name", channel_id)
        channel_type = channel_info.get("is_private", "public_channel")

        channel_stats = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "messages_processed": 0,
            "messages_indexed": 0,
            "messages_failed": 0,
            "files_processed": 0,
            "files_indexed": 0,
            "files_failed": 0,
            "threads_processed": 0,
            "errors": []
        }

        try:
            logger.info(f"Syncing channel {channel_name} ({channel_id})")

            # Update channel status to syncing
            self.db_service.upsert_slack_channel(
                user_id=user_id,
                channel_id=channel_id,
                channel_name=channel_name,
                channel_type=channel_type,
                is_member=channel_info.get("is_member", True),
                sync_status="syncing"
            )

            # Determine time range for sync
            if full_sync:
                oldest = None
                latest = None
            else:
                # Incremental sync - get messages from last 10 minutes
                oldest = self.slack_client.get_oldest_timestamp_for_sync(10)
                latest = None

            # Get messages
            messages = await self.slack_client.get_messages(
                client, channel_id, oldest=oldest, latest=latest, limit=1000
            )

            if not messages:
                logger.info(f"No new messages in channel {channel_name}")
                self.db_service.update_slack_channel_sync(
                    user_id=user_id,
                    channel_id=channel_id,
                    sync_status="completed"
                )
                return channel_stats

            # Process messages
            processed_threads = set()
            for message in messages:
                try:
                    channel_stats["messages_processed"] += 1

                    # Check if this is a thread parent or reply
                    thread_ts = message.get("thread_ts")
                    if thread_ts:
                        if thread_ts not in processed_threads:
                            # Process entire thread
                            parent_message = None
                            if message.get("ts") == thread_ts:
                                parent_message = message
                            else:
                                # Find parent message in current batch
                                for msg in messages:
                                    if msg.get("ts") == thread_ts:
                                        parent_message = msg
                                        break

                            if parent_message:
                                parent_doc_id, reply_doc_ids = await self.message_processor.process_thread(
                                    client, parent_message, channel_info
                                )
                                processed_threads.add(thread_ts)

                                # Index thread content
                                if parent_doc_id:
                                    await self._index_thread_content(
                                        user_id, parent_doc_id, reply_doc_ids, parent_message
                                    )
                                    channel_stats["messages_indexed"] += len([parent_doc_id] + reply_doc_ids])

                            channel_stats["threads_processed"] += 1
                        else:
                            # Thread reply already processed with parent
                            continue
                    else:
                        # Regular message, process individually
                        doc_id = await self.message_processor.process_message(client, message, channel_info)
                        if doc_id:
                            # Index message content
                            await self._index_message_content(user_id, doc_id, message)
                            channel_stats["messages_indexed"] += 1

                except Exception as e:
                    logger.error(f"Failed to process message {message.get('ts', 'unknown')}: {e}")
                    channel_stats["messages_failed"] += 1
                    channel_stats["errors"].append(f"Message {message.get('ts', 'unknown')}: {str(e)}")

            # Update channel sync status
            self.db_service.update_slack_channel_sync(
                user_id=user_id,
                channel_id=channel_id,
                sync_status="completed",
                messages_count=channel_stats["messages_processed"]
            )

            logger.info(
                f"Channel sync completed: {channel_stats['messages_indexed']}/{channel_stats['messages_processed']} messages indexed"
            )

            return channel_stats

        except Exception as e:
            logger.error(f"Channel sync failed {channel_name}: {e}")
            channel_stats["errors"].append(f"Channel sync failed: {str(e)}")

            # Update channel sync status to failed
            self.db_service.update_slack_channel_sync(
                user_id=user_id,
                channel_id=channel_id,
                sync_status="failed",
                error_message=str(e)
            )

            return channel_stats

    async def _index_message_content(
        self, user_id: str, doc_id: str, message: Dict[str, Any]
    ):
        """Index message content in vector database"""
        try:
            # Get message content including file text
            slack_doc = self.db_service.get_slack_document(message["ts"])
            if not slack_doc:
                return

            # Combine message text with file content
            content_parts = [slack_doc["text"]]

            # Add file content if available
            if slack_doc["file_attachments"]:
                for file_info in slack_doc["file_attachments"]:
                    if file_info.get("extracted_text"):
                        content_parts.append(file_info["extracted_text"])

            combined_content = "\n\n".join(content_parts)

            if combined_content.strip():
                # Create metadata for RAG
                metadata = {
                    "doc_id": doc_id,
                    "title": f"Slack Message in #{slack_doc['channel_name']}",
                    "source_type": "slack",
                    "source_id": slack_doc["source_id"],
                    "channel_id": slack_doc["channel_id"],
                    "channel_name": slack_doc["channel_name"],
                    "user_id": slack_doc["user_id"],
                    "user_name": slack_doc["user_name"],
                    "timestamp": slack_doc["timestamp"].isoformat(),
                    "thread_id": slack_doc["thread_id"],
                    "message_type": slack_doc["message_type"],
                    "permissions": [user_id],  # TODO: Add proper permissions
                }

                # Index in RAG service
                await self.rag_service.index_document(
                    content=combined_content,
                    metadata=metadata,
                    chunk_size=500,
                    chunk_overlap=50
                )

        except Exception as e:
            logger.error(f"Failed to index message content: {e}")

    async def _index_thread_content(
        self, user_id: str, parent_doc_id: str, reply_doc_ids: List[str], parent_message: Dict[str, Any]
    ):
        """Index thread content with conversation context"""
        try:
            # Get thread documents
            all_doc_ids = [parent_doc_id] + reply_doc_ids
            thread_content_parts = []

            # Get all documents and build conversation context
            for doc_id in all_doc_ids:
                # Get from slack_documents table
                # Note: This would need to be implemented to fetch by document ID
                # For now, use the parent message content
                if doc_id == parent_doc_id:
                    thread_content_parts.append(f"Thread Parent:\n{parent_message.get('text', '')}")

            combined_thread_content = "\n\n".join(thread_content_parts)

            if combined_thread_content.strip():
                # Create thread metadata
                metadata = {
                    "doc_id": parent_doc_id,
                    "title": f"Slack Thread in #{parent_message.get('channel', {}).get('name', 'unknown')}",
                    "source_type": "slack_thread",
                    "source_id": parent_message["ts"],
                    "channel_id": parent_message.get("channel"),
                    "thread_id": parent_message.get("thread_ts"),
                    "message_count": len(all_doc_ids),
                    "permissions": [user_id],  # TODO: Add proper permissions
                }

                # Index thread as a single document
                await self.rag_service.index_document(
                    content=combined_thread_content,
                    metadata=metadata,
                    chunk_size=800,  # Larger chunks for threads
                    chunk_overlap=100
                )

        except Exception as e:
            logger.error(f"Failed to index thread content: {e}")

    async def _update_sync_state(
        self,
        user_id: str,
        team_id: str,
        team_name: str,
        bot_user_id: str,
        stats: Dict[str, Any],
        last_error: Optional[str] = None
    ):
        """Update Slack sync state in database"""
        try:
            # Get current state
            current_state = self.db_service.get_slack_sync_state(user_id) or {}

            # Update with new stats
            await self.db_service.update_slack_sync_state(
                user_id=user_id,
                team_id=team_id,
                team_name=team_name,
                bot_user_id=bot_user_id,
                channels_synced=stats["channels_synced"],
                messages_synced=stats["messages_indexed"],
                messages_failed=stats["messages_failed"],
                files_processed=stats["files_processed"],
                files_failed=stats["files_failed"],
                last_error=last_error,
                error_details={"errors": stats["errors"][:10]} if stats["errors"] else None
            )

        except Exception as e:
            logger.error(f"Failed to update sync state: {e}")

    async def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive sync status for a user"""
        try:
            sync_state = self.db_service.get_slack_sync_state(user_id)
            channels = self.db_service.get_slack_channels(user_id)

            status = {
                "user_id": user_id,
                "is_configured": sync_state is not None,
                "team_info": None,
                "last_sync_at": None,
                "channels": {
                    "total": len(channels),
                    "synced": 0,
                    "failed": 0,
                    "pending": 0,
                },
                "sync_stats": {
                    "channels_synced": sync_state.get("channels_synced", 0) if sync_state else 0,
                    "messages_synced": sync_state.get("messages_synced", 0) if sync_state else 0,
                    "messages_failed": sync_state.get("messages_failed", 0) if sync_state else 0,
                    "files_processed": sync_state.get("files_processed", 0) if sync_state else 0,
                    "files_failed": sync_state.get("files_failed", 0) if sync_state else 0,
                },
                "last_error": sync_state.get("last_error") if sync_state else None,
            }

            if sync_state:
                status["team_info"] = {
                    "team_id": sync_state["team_id"],
                    "team_name": sync_state["team_name"],
                    "bot_user_id": sync_state["bot_user_id"],
                }
                status["last_sync_at"] = sync_state["last_sync_at"].isoformat() if sync_state.get("last_sync_at") else None

            # Count channel statuses
            for channel in channels:
                status["channels"][channel["sync_status"]] += 1

            return status

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {"error": str(e)}


# Global sync service instance
_slack_sync_service = None


def get_slack_sync_service() -> SlackSyncService:
    """Get or create Slack sync service instance"""
    global _slack_sync_service
    if _slack_sync_service is None:
        _slack_sync_service = SlackSyncService()
    return _slack_sync_service