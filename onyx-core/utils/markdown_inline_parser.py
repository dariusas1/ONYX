"""
Markdown Inline Formatting Parser

Parses inline markdown elements (bold, italic, links, code) and provides
clean text and position information for applying formatting.
"""

import re
from typing import List, Tuple, Optional, NamedTuple


class InlineMarkdownElement(NamedTuple):
    """Represents a parsed inline markdown element"""

    text: str  # Plain text without markers
    start_pos: int  # Start position in cleaned text
    end_pos: int  # End position in cleaned text
    element_type: str  # 'bold', 'italic', 'link', 'code'
    url: Optional[str] = None  # For links


class MarkdownInlineParser:
    """Parses inline markdown elements from text"""

    # Regex patterns for inline elements
    # Order matters: bold before italic (** before *)
    BOLD_PATTERN = r"\*\*(.+?)\*\*|__(.+?)__"
    ITALIC_PATTERN = (
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)"
    )
    LINK_PATTERN = r"\[(.+?)\]\((.+?)\)"
    CODE_PATTERN = r"`(.+?)`"

    def parse_paragraph(
        self, markdown_text: str
    ) -> Tuple[str, List[InlineMarkdownElement]]:
        """
        Parse a paragraph for inline markdown elements.

        Args:
            markdown_text: Text with markdown formatting

        Returns:
            Tuple of (cleaned_text, list_of_inline_elements)
            - cleaned_text: Original text with all markdown markers removed
            - inline_elements: List of InlineMarkdownElement with positions in cleaned text
        """
        elements = []

        # Process in order: code, links, bold, italic
        # This prevents patterns from interfering with each other
        cleaned_text = markdown_text

        # First pass: extract code (backticks)
        cleaned_text, code_elements = self._extract_elements(
            cleaned_text, self.CODE_PATTERN, "code"
        )
        elements.extend(code_elements)

        # Second pass: extract links
        cleaned_text, link_elements = self._extract_elements(
            cleaned_text, self.LINK_PATTERN, "link", group_extra=2
        )
        elements.extend(link_elements)

        # Third pass: extract bold (before italic to avoid overlap)
        cleaned_text, bold_elements = self._extract_elements(
            cleaned_text, self.BOLD_PATTERN, "bold"
        )
        elements.extend(bold_elements)

        # Fourth pass: extract italic
        cleaned_text, italic_elements = self._extract_elements(
            cleaned_text, self.ITALIC_PATTERN, "italic"
        )
        elements.extend(italic_elements)

        # Sort elements by position for consistent ordering
        elements.sort(key=lambda e: e.start_pos)

        return cleaned_text, elements

    def _extract_elements(
        self,
        text: str,
        pattern: str,
        element_type: str,
        group_extra: Optional[int] = None,
    ) -> Tuple[str, List[InlineMarkdownElement]]:
        """
        Extract elements matching a pattern and return cleaned text with positions.

        Args:
            text: Text to search
            pattern: Regex pattern to match
            element_type: Type of element ('bold', 'italic', 'link', 'code')
            group_extra: Group number for extra data (e.g., URL in links)

        Returns:
            Tuple of (cleaned_text, list_of_elements)
        """
        elements = []
        cleaned_parts = []
        last_end = 0
        position_offset = 0

        for match in re.finditer(pattern, text):
            # Add text before this match
            before_text = text[last_end : match.start()]
            cleaned_parts.append(before_text)

            # Extract the plain text (without markdown markers)
            # Group 1 is usually the content, Group 2 is for alternate patterns
            plain_text = match.group(1) or (
                match.group(2) if match.lastindex >= 2 else ""
            )

            # For links, group(2) is the URL
            url = None
            if element_type == "link" and group_extra == 2:
                url = match.group(2)
                plain_text = match.group(1)

            # Calculate position in cleaned text
            start_pos = len("".join(cleaned_parts))
            cleaned_parts.append(plain_text)
            end_pos = len("".join(cleaned_parts))

            # Create element
            element = InlineMarkdownElement(
                text=plain_text,
                start_pos=start_pos,
                end_pos=end_pos,
                element_type=element_type,
                url=url,
            )
            elements.append(element)

            last_end = match.end()

        # Add remaining text after last match
        cleaned_parts.append(text[last_end:])
        cleaned_text = "".join(cleaned_parts)

        return cleaned_text, elements
