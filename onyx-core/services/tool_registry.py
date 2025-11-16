"""
Tool Registry Service for ONYX Core

Manages registration and discovery of tools available to agents.
Provides a centralized registry for tool metadata and endpoints.

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Definition of a tool available to agents."""

    name: str = Field(..., description="Unique tool name")
    display_name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description and purpose")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters schema")
    returns: Dict[str, Any] = Field(..., description="Expected return value schema")
    endpoint: Optional[str] = Field(None, description="API endpoint for the tool")
    method: str = Field("POST", description="HTTP method for the tool")
    auth_required: bool = Field(True, description="Whether authentication is required")
    category: str = Field("general", description="Tool category for organization")
    version: str = Field("1.0.0", description="Tool version")
    tags: List[str] = Field(default_factory=list, description="Tags for tool discovery")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    registered_at: datetime = Field(default_factory=datetime.utcnow, description="Registration timestamp")
    enabled: bool = Field(True, description="Whether the tool is enabled")

    class Config:
        schema_extra = {
            "example": {
                "name": "scrape_url",
                "display_name": "URL Content Scraper",
                "description": "Scrape and extract clean content from web pages using Mozilla Readability",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape and extract content from",
                        "required": True
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Skip cache and force fresh scraping",
                        "default": False
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Scraped content with metadata"
                },
                "endpoint": "/tools/scrape_url",
                "method": "POST",
                "auth_required": True,
                "category": "web_automation"
            }
        }


class ToolRegistry:
    """Registry for managing tools available to agents."""

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._tags: Dict[str, List[str]] = {}
        logger.info("ToolRegistry initialized")

    async def register_tool(self, name: str, tool_def: ToolDefinition) -> bool:
        """
        Register a tool in the registry.

        Args:
            name: Unique tool name
            tool_def: Tool definition

        Returns:
            True if registered successfully, False if tool already exists

        Raises:
            ValueError: If tool definition is invalid
        """
        if not name or not name.strip():
            raise ValueError("Tool name cannot be empty")

        name = name.strip().lower()

        if name in self._tools:
            logger.warning(f"Tool {name} already registered, skipping")
            return False

        # Validate tool definition
        if not tool_def.description:
            raise ValueError("Tool description cannot be empty")

        if not tool_def.parameters:
            tool_def.parameters = {}

        # Store tool
        self._tools[name] = tool_def

        # Update category index
        category = tool_def.category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)

        # Update tag index
        for tag in tool_def.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            if name not in self._tags[tag]:
                self._tags[tag].append(name)

        logger.info(f"Tool {name} registered successfully in category {category}")
        return True

    async def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            name: Tool name to unregister

        Returns:
            True if unregistered successfully, False if tool not found
        """
        name = name.strip().lower()

        if name not in self._tools:
            logger.warning(f"Tool {name} not found for unregistration")
            return False

        tool_def = self._tools[name]

        # Remove from category index
        category = tool_def.category
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)
            if not self._categories[category]:
                del self._categories[category]

        # Remove from tag index
        for tag in tool_def.tags:
            if tag in self._tags and name in self._tags[tag]:
                self._tags[tag].remove(name)
                if not self._tags[tag]:
                    del self._tags[tag]

        # Remove tool
        del self._tools[name]

        logger.info(f"Tool {name} unregistered successfully")
        return True

    async def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition if found, None otherwise
        """
        name = name.strip().lower()
        return self._tools.get(name)

    async def list_tools(self, category: Optional[str] = None, enabled_only: bool = True) -> List[ToolDefinition]:
        """
        List all tools or tools in a specific category.

        Args:
            category: Optional category filter
            enabled_only: Whether to return only enabled tools

        Returns:
            List of tool definitions
        """
        tools = list(self._tools.values())

        # Filter by category
        if category:
            category = category.strip().lower()
            tools = [tool for tool in tools if tool.category.lower() == category]

        # Filter by enabled status
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]

        return tools

    async def get_categories(self) -> Dict[str, List[str]]:
        """
        Get all categories and their tools.

        Returns:
            Dictionary mapping category names to tool names
        """
        return dict(self._categories)

    async def get_tags(self) -> Dict[str, List[str]]:
        """
        Get all tags and their associated tools.

        Returns:
            Dictionary mapping tag names to tool names
        """
        return dict(self._tags)

    async def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        Search for tools by name, description, or tags.

        Args:
            query: Search query

        Returns:
            List of matching tool definitions
        """
        query = query.strip().lower()
        if not query:
            return []

        matching_tools = []

        for tool in self._tools.values():
            # Search in name
            if query in tool.name.lower():
                matching_tools.append(tool)
                continue

            # Search in display name
            if query in tool.display_name.lower():
                matching_tools.append(tool)
                continue

            # Search in description
            if query in tool.description.lower():
                matching_tools.append(tool)
                continue

            # Search in tags
            if any(query in tag.lower() for tag in tool.tags):
                matching_tools.append(tool)
                continue

        return matching_tools

    async def enable_tool(self, name: str) -> bool:
        """
        Enable a tool.

        Args:
            name: Tool name

        Returns:
            True if enabled successfully, False if tool not found
        """
        tool = await self.get_tool(name)
        if tool:
            tool.enabled = True
            logger.info(f"Tool {name} enabled")
            return True
        return False

    async def disable_tool(self, name: str) -> bool:
        """
        Disable a tool.

        Args:
            name: Tool name

        Returns:
            True if disabled successfully, False if tool not found
        """
        tool = await self.get_tool(name)
        if tool:
            tool.enabled = False
            logger.info(f"Tool {name} disabled")
            return True
        return False

    async def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        total_tools = len(self._tools)
        enabled_tools = len([t for t in self._tools.values() if t.enabled])
        total_categories = len(self._categories)
        total_tags = len(self._tags)

        # Category distribution
        category_counts = {
            category: len(tools) for category, tools in self._categories.items()
        }

        return {
            "total_tools": total_tools,
            "enabled_tools": enabled_tools,
            "disabled_tools": total_tools - enabled_tools,
            "total_categories": total_categories,
            "total_tags": total_tags,
            "category_distribution": category_counts,
            "last_updated": datetime.utcnow().isoformat()
        }

    async def export_tools(self, format: str = "json") -> str:
        """
        Export tool registry in specified format.

        Args:
            format: Export format ("json" or "yaml")

        Returns:
            Exported registry data as string
        """
        tools_data = {
            "tools": {
                name: tool.dict() for name, tool in self._tools.items()
            },
            "categories": self._categories,
            "tags": self._tags,
            "exported_at": datetime.utcnow().isoformat(),
            "total_tools": len(self._tools)
        }

        if format.lower() == "json":
            import json
            return json.dumps(tools_data, indent=2, default=str)
        elif format.lower() == "yaml":
            try:
                import yaml
                return yaml.dump(tools_data, default_flow_style=False)
            except ImportError:
                logger.error("PyYAML not available for YAML export")
                raise ValueError("PyYAML required for YAML export")
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global registry instance
_registry: Optional[ToolRegistry] = None


async def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        logger.info("Global ToolRegistry instance created")
    return _registry


async def register_core_tools():
    """
    Register core tools that are always available.

    This function should be called during application startup to register
    the built-in tools like scrape_url, search_web, etc.
    """
    registry = await get_tool_registry()

    # Register scrape_url tool
    scrape_url_tool = ToolDefinition(
        name="scrape_url",
        display_name="URL Content Scraper",
        description="Scrape and extract clean content from web pages using Mozilla Readability algorithm. Removes ads, navigation, and scripts to extract main article content as Markdown with metadata.",
        parameters={
            "url": {
                "type": "string",
                "description": "URL to scrape and extract content from",
                "required": True,
                "format": "uri"
            },
            "force_refresh": {
                "type": "boolean",
                "description": "Skip cache and force fresh scraping",
                "default": False,
                "required": False
            }
        },
        returns={
            "type": "object",
            "description": "Scraped content with metadata",
            "properties": {
                "url": {"type": "string", "description": "Original URL"},
                "title": {"type": "string", "description": "Extracted title"},
                "text_content": {"type": "string", "description": "Plain text content"},
                "markdown_content": {"type": "string", "description": "Content formatted as Markdown"},
                "author": {"type": "string", "description": "Extracted author"},
                "publish_date": {"type": "string", "description": "Publication date"},
                "excerpt": {"type": "string", "description": "Content excerpt"},
                "word_count": {"type": "integer", "description": "Word count of content"},
                "execution_time_ms": {"type": "integer", "description": "Execution time in milliseconds"},
                "scraped_at": {"type": "string", "description": "Timestamp of scraping"}
            }
        },
        endpoint="/tools/scrape_url",
        method="POST",
        auth_required=True,
        category="web_automation",
        version="1.0.0",
        tags=["scraping", "content-extraction", "web", "readability", "markdown"],
        examples=[
            {
                "description": "Basic URL scraping",
                "parameters": {
                    "url": "https://example.com/article"
                }
            },
            {
                "description": "Force refresh to bypass cache",
                "parameters": {
                    "url": "https://news.example.com/story",
                    "force_refresh": True
                }
            }
        ]
    )

    success = await registry.register_tool("scrape_url", scrape_url_tool)
    if success:
        logger.info("Core tool scrape_url registered successfully")
    else:
        logger.warning("Failed to register scrape_url tool")

    # Future: Register search_web tool when API endpoint is created
    # search_web_tool = ToolDefinition(
    #     name="search_web",
    #     display_name="Web Search",
    #     description="Search the web using SerpAPI or Exa with intelligent fallback and caching",
    #     # ... rest of definition
    # )
    # await registry.register_tool("search_web", search_web_tool)

    logger.info("Core tools registration completed")