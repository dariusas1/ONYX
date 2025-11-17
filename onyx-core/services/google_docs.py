"""
Google Docs API Service

This module handles Google Docs creation, formatting, and management.
Supports Markdown to Google Docs conversion with comprehensive formatting.
"""

import re
import time
import logging
import asyncio
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from services.google_oauth import GoogleOAuthService
from utils.database import get_db_service

logger = logging.getLogger(__name__)

# Global service instance
_docs_service = None


class GoogleDocsService:
    """Service for creating and managing Google Docs with formatted content"""

    def __init__(self, oauth_service: Optional[GoogleOAuthService] = None):
        """
        Initialize Google Docs service

        Args:
            oauth_service: GoogleOAuthService instance for authentication
        """
        self.oauth_service = oauth_service or GoogleOAuthService()
        self.db_service = get_db_service()
        self.docs_service = None
        self.drive_service = None

    def _get_docs_service(self, credentials: Credentials):
        """Get authenticated Google Docs API service"""
        if self.docs_service is None:
            self.docs_service = build("docs", "v1", credentials=credentials)
        return self.docs_service

    def _get_drive_service(self, credentials: Credentials):
        """Get authenticated Google Drive API service"""
        if self.drive_service is None:
            self.drive_service = build("drive", "v3", credentials=credentials)
        return self.drive_service

    async def create_document(
        self,
        user_id: str,
        title: str,
        content_markdown: str,
        folder_id: Optional[str] = None,
        agent_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Google Doc from Markdown content

        Args:
            user_id: User ID for OAuth credentials
            title: Document title
            content_markdown: Markdown-formatted content
            folder_id: Optional Google Drive folder ID for placement
            agent_context: Optional context dict with agent/task info

        Returns:
            Dict with doc_id, url, created_at, and performance metrics

        Raises:
            ValueError: If title or content is empty
            PermissionError: If user lacks required permissions
            Exception: For other API errors
        """
        start_time = time.time()

        # Validate inputs
        if not title or not title.strip():
            raise ValueError("Document title cannot be empty")
        if not content_markdown or not content_markdown.strip():
            raise ValueError("Document content cannot be empty")

        try:
            # Get credentials
            credentials = self.oauth_service.get_credentials(user_id)
            if not credentials:
                raise PermissionError("User has not authorized Google Docs access")

            drive_service = self._get_drive_service(credentials)
            docs_service = self._get_docs_service(credentials)

            # Create empty document
            doc_body = {"title": title}
            document = (
                drive_service.files()
                .create(body=doc_body, fields="id,webViewLink,createdTime")
                .execute()
            )

            doc_id = document["id"]
            web_link = document["webViewLink"]
            created_at = document["createdTime"]

            # Move to folder if specified
            if folder_id:
                await self._move_to_folder(drive_service, doc_id, folder_id)

            # Convert and insert formatted content
            requests = self._markdown_to_gdocs_requests(content_markdown)
            if requests:
                docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

            # Store metadata
            await self._store_metadata(
                user_id=user_id,
                doc_id=doc_id,
                title=title,
                folder_id=folder_id,
                url=web_link,
                created_at=created_at,
                agent_context=agent_context,
            )

            elapsed_time = time.time() - start_time

            logger.info(
                f"Created Google Doc: {title} ({doc_id}) in {elapsed_time:.2f}s"
            )

            return {
                "doc_id": doc_id,
                "url": web_link,
                "created_at": created_at,
                "title": title,
                "performance_ms": int(elapsed_time * 1000),
                "metadata_stored": True,
            }

        except PermissionError as e:
            logger.error(f"Permission denied creating doc for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Google Doc: {e}")
            if "quota" in str(e).lower():
                raise PermissionError("Google Drive quota exceeded")
            raise

    def _markdown_to_gdocs_requests(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert Markdown to Google Docs API requests

        Args:
            markdown: Markdown-formatted text

        Returns:
            List of batchUpdate requests for Google Docs API
        """
        requests = []

        # Parse markdown into blocks
        blocks = self._parse_markdown_blocks(markdown)

        for block in blocks:
            block_type = block["type"]
            content = block["content"]

            if block_type == "heading1":
                requests.extend(self._create_heading_request(content, "HEADING_1"))
            elif block_type == "heading2":
                requests.extend(self._create_heading_request(content, "HEADING_2"))
            elif block_type == "heading3":
                requests.extend(self._create_heading_request(content, "HEADING_3"))
            elif block_type == "heading4":
                requests.extend(self._create_heading_request(content, "HEADING_4"))
            elif block_type == "heading5":
                requests.extend(self._create_heading_request(content, "HEADING_5"))
            elif block_type == "heading6":
                requests.extend(self._create_heading_request(content, "HEADING_6"))
            elif block_type == "paragraph":
                requests.extend(self._create_paragraph_request(content))
            elif block_type == "bullet_list":
                requests.extend(self._create_bullet_list_request(content))
            elif block_type == "ordered_list":
                requests.extend(self._create_ordered_list_request(content))
            elif block_type == "code_block":
                requests.extend(self._create_code_block_request(content))
            elif block_type == "horizontal_rule":
                requests.append(self._create_horizontal_rule_request())

        return requests

    def _parse_markdown_blocks(self, markdown: str) -> List[Dict[str, str]]:
        """Parse Markdown into logical blocks"""
        blocks = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Headings
            if line.startswith("######"):
                blocks.append({"type": "heading6", "content": line[6:].strip()})
                i += 1
            elif line.startswith("#####"):
                blocks.append({"type": "heading5", "content": line[5:].strip()})
                i += 1
            elif line.startswith("####"):
                blocks.append({"type": "heading4", "content": line[4:].strip()})
                i += 1
            elif line.startswith("###"):
                blocks.append({"type": "heading3", "content": line[3:].strip()})
                i += 1
            elif line.startswith("##"):
                blocks.append({"type": "heading2", "content": line[2:].strip()})
                i += 1
            elif line.startswith("#"):
                blocks.append({"type": "heading1", "content": line[1:].strip()})
                i += 1
            # Horizontal rule
            elif line.strip() in ["---", "***", "___"]:
                blocks.append({"type": "horizontal_rule", "content": ""})
                i += 1
            # Code block
            elif line.startswith("```"):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # Skip closing ```
                blocks.append({"type": "code_block", "content": "\n".join(code_lines)})
            # Bullet list
            elif line.lstrip().startswith(("-", "*", "+")):
                list_items = []
                while i < len(lines) and (
                    lines[i].lstrip().startswith(("-", "*", "+"))
                    or not lines[i].strip()
                ):
                    if lines[i].strip():
                        list_items.append(lines[i].lstrip()[1:].strip())
                    i += 1
                blocks.append({"type": "bullet_list", "content": list_items})
            # Ordered list
            elif re.match(r"^\d+\.", line.lstrip()):
                list_items = []
                while i < len(lines) and (
                    re.match(r"^\d+\.", lines[i].lstrip()) or not lines[i].strip()
                ):
                    if lines[i].strip():
                        list_items.append(re.sub(r"^\d+\.\s*", "", lines[i].lstrip()))
                    i += 1
                blocks.append({"type": "ordered_list", "content": list_items})
            # Regular paragraph
            else:
                paragraph_lines = []
                while (
                    i < len(lines)
                    and lines[i].strip()
                    and not any(
                        [
                            lines[i].startswith(("#", "```")),
                            re.match(r"^\d+\.", lines[i].lstrip()),
                            lines[i].lstrip().startswith(("-", "*", "+")),
                            lines[i].strip() in ["---", "***", "___"],
                        ]
                    )
                ):
                    paragraph_lines.append(lines[i])
                    i += 1
                if paragraph_lines:
                    blocks.append(
                        {"type": "paragraph", "content": " ".join(paragraph_lines)}
                    )

        return blocks

    def _create_heading_request(self, content: str, style: str) -> List[Dict]:
        """Create a heading with formatting"""
        return [
            {"insertText": {"text": content + "\n"}},
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": len(content) + 1},
                    "textStyle": {},
                    "fields": "bold",
                }
            },
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": 1, "endIndex": len(content) + 1},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            },
        ]

    def _create_paragraph_request(self, content: str) -> List[Dict]:
        """Create a formatted paragraph with inline styling"""
        requests = [{"insertText": {"text": content + "\n"}}]

        # Apply inline formatting (bold, italic, links, code)
        requests.extend(self._apply_inline_formatting(content))

        return requests

    def _apply_inline_formatting(self, text: str) -> List[Dict]:
        """Apply inline formatting (bold, italic, links, code) to text"""
        requests = []

        # Find and apply bold formatting
        bold_pattern = r"\*\*(.+?)\*\*"
        for match in re.finditer(bold_pattern, text):
            start = text[: match.start()].count("\n") == 0 and match.start() or 0
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": match.start(), "endIndex": match.end()},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                }
            )

        # Find and apply italic formatting
        italic_pattern = r"\*(.+?)\*|\_(.+?)\_"
        for match in re.finditer(italic_pattern, text):
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": match.start(), "endIndex": match.end()},
                        "textStyle": {"italic": True},
                        "fields": "italic",
                    }
                }
            )

        # Find and apply link formatting
        link_pattern = r"\[(.+?)\]\((.+?)\)"
        for match in re.finditer(link_pattern, text):
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": match.start(), "endIndex": match.end()},
                        "textStyle": {"link": {"url": match.group(2)}},
                        "fields": "link",
                    }
                }
            )

        # Find and apply code formatting
        code_pattern = r"`(.+?)`"
        for match in re.finditer(code_pattern, text):
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": match.start(), "endIndex": match.end()},
                        "textStyle": {
                            "backgroundColor": {
                                "color": {
                                    "rgbColor": {
                                        "red": 0.95,
                                        "green": 0.95,
                                        "blue": 0.95,
                                    }
                                }
                            },
                            "fontFamily": "Courier New",
                        },
                        "fields": "backgroundColor,fontFamily",
                    }
                }
            )

        return requests

    def _create_bullet_list_request(self, items: List[str]) -> List[Dict]:
        """Create a bullet list"""
        requests = []
        for item in items:
            requests.extend(
                [
                    {"insertText": {"text": item + "\n"}},
                    {
                        "createParagraphBullets": {
                            "range": {"startIndex": 1, "endIndex": len(item) + 2},
                            "bulletPreset": "BULLET_DISC",
                        }
                    },
                ]
            )
        return requests

    def _create_ordered_list_request(self, items: List[str]) -> List[Dict]:
        """Create an ordered list"""
        requests = []
        for idx, item in enumerate(items, 1):
            requests.extend(
                [
                    {"insertText": {"text": item + "\n"}},
                    {
                        "createParagraphBullets": {
                            "range": {"startIndex": 1, "endIndex": len(item) + 2},
                            "bulletPreset": "NUMBER_DECIMAL",
                        }
                    },
                ]
            )
        return requests

    def _create_code_block_request(self, code: str) -> List[Dict]:
        """Create a code block with monospace formatting"""
        return [
            {"insertText": {"text": code + "\n"}},
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": len(code) + 1},
                    "textStyle": {
                        "fontFamily": "Courier New",
                        "backgroundColor": {
                            "color": {
                                "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                            }
                        },
                    },
                    "fields": "fontFamily,backgroundColor",
                }
            },
        ]

    def _create_horizontal_rule_request(self) -> Dict:
        """Create a horizontal rule"""
        return {"insertText": {"text": "─" * 50 + "\n"}}

    async def _move_to_folder(self, drive_service, doc_id: str, folder_id: str):
        """Move document to specified folder"""
        try:
            drive_service.files().update(
                fileId=doc_id, addParents=folder_id, fields="id,parents"
            ).execute()
            logger.info(f"Moved document {doc_id} to folder {folder_id}")
        except Exception as e:
            logger.warning(f"Failed to move document to folder: {e}")
            # Non-blocking - document still created, just not in desired folder

    async def _store_metadata(
        self,
        user_id: str,
        doc_id: str,
        title: str,
        folder_id: Optional[str],
        url: str,
        created_at: str,
        agent_context: Optional[Dict[str, Any]],
    ):
        """Store document metadata in database"""
        try:
            # Check if table exists, if not create it
            connection = await self.db_service.get_connection()

            # Create table if not exists
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS google_docs_created (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    doc_id VARCHAR(255) NOT NULL UNIQUE,
                    title VARCHAR(1024) NOT NULL,
                    folder_id VARCHAR(255),
                    url TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    agent_context JSONB,
                    stored_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Insert metadata
            await connection.execute(
                """
                INSERT INTO google_docs_created 
                (user_id, doc_id, title, folder_id, url, created_at, agent_context)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (doc_id) DO NOTHING
            """,
                user_id,
                doc_id,
                title,
                folder_id,
                url,
                created_at,
                agent_context,
            )

            logger.info(f"Stored metadata for document {doc_id}")

        except Exception as e:
            logger.warning(f"Failed to store document metadata: {e}")
            # Non-blocking - document created, metadata storage is optional

    def get_document(self, user_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata and content"""
        try:
            credentials = self.oauth_service.get_credentials(user_id)
            if not credentials:
                return None

            docs_service = self._get_docs_service(credentials)
            document = docs_service.documents().get(documentId=doc_id).execute()

            return {
                "title": document.get("title"),
                "doc_id": doc_id,
                "body": document.get("body", {}),
            }

        except Exception as e:
            logger.error(f"Failed to retrieve document {doc_id}: {e}")
            return None


def get_docs_service() -> GoogleDocsService:
    """Get or create Google Docs service instance"""
    global _docs_service
    if _docs_service is None:
        _docs_service = GoogleDocsService()
    return _docs_service
