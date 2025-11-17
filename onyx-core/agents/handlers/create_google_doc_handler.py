"""
Agent Tool Handler for Google Docs Creation

This handler processes tool invocations from agents to create Google Docs
with formatted content. Validates inputs, calls the Google Docs service,
and returns results to the agent.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from services.google_docs import GoogleDocsService
from services.google_oauth import GoogleOAuthService

logger = logging.getLogger(__name__)


class CreateGoogleDocHandler:
    """Handler for create_google_doc agent tool"""

    def __init__(self):
        """Initialize the handler"""
        self.docs_service = GoogleDocsService()
        self.oauth_service = GoogleOAuthService()

    async def handle(
        self,
        user_id: str,
        title: str,
        content: str,
        folder_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle create_google_doc tool invocation

        Args:
            user_id: User ID for authentication
            title: Document title
            content: Document content (Markdown format)
            folder_id: Optional folder ID for placement
            agent_name: Optional agent name for context
            task_id: Optional task ID for context

        Returns:
            Dict with success status, document details, and any errors
        """
        try:
            logger.info(
                f"Processing create_google_doc for user {user_id}: "
                f"title='{title}', content_length={len(content)}"
            )

            # Validate inputs
            if not title or not title.strip():
                return {
                    "success": False,
                    "error": "Document title cannot be empty",
                    "error_code": "INVALID_TITLE",
                }

            if not content or not content.strip():
                return {
                    "success": False,
                    "error": "Document content cannot be empty",
                    "error_code": "INVALID_CONTENT",
                }

            if len(title) > 1024:
                return {
                    "success": False,
                    "error": "Document title too long (max 1024 characters)",
                    "error_code": "TITLE_TOO_LONG",
                }

            # Check user authorization
            credentials = self.oauth_service.get_credentials(user_id)
            if not credentials:
                return {
                    "success": False,
                    "error": "User has not authorized Google Docs access. "
                    "Please visit /api/google-drive/auth/authorize first.",
                    "error_code": "NOT_AUTHORIZED",
                    "action_required": "authorize_google_drive",
                }

            # Build agent context
            from datetime import timezone

            agent_context = {
                "agent": agent_name or "Unknown Agent",
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "handler": "create_google_doc_handler",
            }

            # Create document
            result = await self.docs_service.create_document(
                user_id=user_id,
                title=title,
                content_markdown=content,
                folder_id=folder_id,
                agent_context=agent_context,
            )

            # Return success
            return {
                "success": True,
                "data": {
                    "doc_id": result["doc_id"],
                    "url": result["url"],
                    "title": result["title"],
                    "created_at": result["created_at"],
                    "performance_ms": result["performance_ms"],
                },
                "message": f"Google Doc created successfully: {result['title']}",
            }

        except PermissionError as e:
            logger.warning(f"Permission denied for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "PERMISSION_DENIED",
            }

        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return {"success": False, "error": str(e), "error_code": "VALIDATION_ERROR"}

        except Exception as e:
            logger.error(f"Failed to create Google Doc: {e}", exc_info=True)

            # Determine error type
            error_msg = str(e).lower()
            if "quota" in error_msg:
                error_code = "QUOTA_EXCEEDED"
            elif "forbidden" in error_msg or "403" in error_msg:
                error_code = "PERMISSION_DENIED"
            elif "invalid" in error_msg:
                error_code = "INVALID_INPUT"
            else:
                error_code = "API_ERROR"

            return {
                "success": False,
                "error": f"Failed to create document: {str(e)}",
                "error_code": error_code,
            }


# Global handler instance
_handler = None


def get_handler() -> CreateGoogleDocHandler:
    """Get or create handler instance"""
    global _handler
    if _handler is None:
        _handler = CreateGoogleDocHandler()
    return _handler


async def create_google_doc_tool(
    user_id: str,
    title: str,
    content: str,
    folder_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool function for agents to create Google Docs

    This is the main entry point for agent invocations.

    Args:
        user_id: User ID for authentication
        title: Document title
        content: Document content in Markdown format
        folder_id: Optional Google Drive folder ID
        agent_name: Optional agent name for audit trail
        task_id: Optional task ID for context

    Returns:
        Result dict with success status and document details
    """
    handler = get_handler()
    return await handler.handle(
        user_id=user_id,
        title=title,
        content=content,
        folder_id=folder_id,
        agent_name=agent_name,
        task_id=task_id,
    )


# Tool definition for agent registry
TOOL_DEFINITION = {
    "name": "create_google_doc",
    "description": "Creates a new Google Doc with formatted content from Markdown. Returns a shareable URL to the document.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Document title (required, max 1024 characters)",
                "minLength": 1,
                "maxLength": 1024,
            },
            "content": {
                "type": "string",
                "description": "Document content in Markdown format (required)",
                "minLength": 1,
            },
            "folder_id": {
                "type": "string",
                "description": "Optional Google Drive folder ID for document placement",
            },
            "agent_name": {
                "type": "string",
                "description": "Optional agent name for audit trail",
            },
            "task_id": {
                "type": "string",
                "description": "Optional task ID for context tracking",
            },
        },
        "required": ["title", "content"],
    },
    "returns": {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether document creation was successful",
            },
            "data": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Google Docs document ID",
                    },
                    "url": {
                        "type": "string",
                        "description": "Shareable Google Docs URL",
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title as created",
                    },
                    "created_at": {
                        "type": "string",
                        "description": "ISO timestamp of creation",
                    },
                    "performance_ms": {
                        "type": "integer",
                        "description": "Document creation time in milliseconds",
                    },
                },
            },
            "error": {"type": "string", "description": "Error message if unsuccessful"},
            "error_code": {
                "type": "string",
                "description": "Error code for debugging (INVALID_TITLE, NOT_AUTHORIZED, QUOTA_EXCEEDED, etc.)",
            },
        },
    },
    "examples": [
        {
            "name": "Create strategic analysis document",
            "request": {
                "title": "Q1 2024 Strategic Analysis",
                "content": "# Q1 2024 Strategic Analysis\n\n## Overview\n\nKey findings from Q1 analysis:\n\n- Point 1\n- Point 2\n\n## Recommendations\n\n1. Action item 1\n2. Action item 2",
            },
            "response": {
                "success": True,
                "data": {
                    "doc_id": "1a2b3c4d5e6f7g8h",
                    "url": "https://docs.google.com/document/d/1a2b3c4d5e6f7g8h/edit",
                    "title": "Q1 2024 Strategic Analysis",
                    "created_at": "2024-01-15T10:00:00Z",
                    "performance_ms": 1200,
                },
            },
        }
    ],
}


if __name__ == "__main__":
    # Example usage
    async def demo():
        """Demonstrate tool usage"""
        result = await create_google_doc_tool(
            user_id="demo-user",
            title="Demo Document",
            content="# Demo\n\nThis is a test document.",
            agent_name="DemoAgent",
        )
        print("Result:", result)

    asyncio.run(demo())
