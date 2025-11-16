"""
Memory Extraction Service

This service automatically extracts memories from conversations using LLM analysis,
pattern matching, and confidence scoring. It processes messages to identify
important information that should be stored as persistent memories.
"""

import os
import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI
from memory_service import MemoryService, MemoryCategory, SourceType, CreateMemoryRequest

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 1000
EXTRACTION_CONFIDENCE_THRESHOLD = 0.6
CONVERSATION_MEMORY_LIMIT = 20  # Max memories to extract per conversation
MESSAGE_PROCESSING_BATCH_SIZE = 10

class ExtractionMode(str, Enum):
    """Memory extraction modes"""
    AUTO = "auto"  # Automatic extraction from recent messages
    MANUAL = "manual"  # Manual extraction request
    BATCH = "batch"  # Batch processing of multiple conversations

@dataclass
class ExtractionContext:
    """Context for memory extraction"""
    user_id: str
    conversation_id: str
    messages: List[Dict[str, Any]]
    mode: ExtractionMode
    existing_memories: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None

@dataclass
class ExtractedMemory:
    """Memory extracted from conversation"""
    fact: str
    category: MemoryCategory
    confidence: float
    source_message_id: str
    evidence: List[str]  # Supporting quotes from messages
    extraction_method: str
    metadata: Dict[str, Any]

class MemoryPatternExtractor:
    """Pattern-based memory extraction using regex and heuristics"""

    # Patterns for different types of memories
    MEMORY_PATTERNS = {
        MemoryCategory.PRIORITY: [
            r"(?:i need|i must|i have to|important to me|my priority(?:ies)?)(?:\s+is|\s+are)\s+([^.!?]+)",
            r"(?:let's\s+make\s+sure|we\s+should|don't\s+forget)\s+([^.!?]+)",
            r"(?:my\s+goal(?:s)?|i\s+want\s+to|i\s+plan\s+to)\s+([^.!?]+)"
        ],
        MemoryCategory.DECISION: [
            r"(?:i've\s+decided|i\s+decide|we've\s+decided|let's\s+go\s+with)\s+([^.!?]+)",
            r"(?:the\s+decision\s+is|final\s+decision|i'm\s+choosing)\s+([^.!?]+)",
            r"(?:we'll|i'll|i\s+will)\s+([^.!?]+)(?:\s+instead|\s+rather)"
        ],
        MemoryCategory.PREFERENCE: [
            r"(?:i\s+prefer|i\s+like|i'd\s+rather|i\s+enjoy)\s+([^.!?]+)",
            r"(?:my\s+preference(?:s)?|(?:i'm|i\s+am)\s+comfortable\s+with)\s+([^.!?]+)",
            r"(?:don't\s+(?:want|like)|avoid)\s+([^.!?]+)"
        ],
        MemoryCategory.CONTEXT: [
            r"(?:background\s+info|context|for\s+reference|fyi)\s*:\s*([^.!?]+)",
            r"(?:remember\s+that|keep\s+in\s+mind|it's\s+important\s+to\s+note)\s+([^.!?]+)",
            r"(?:just\s+so\s+you\s+know|for\s+context)\s*,?\s*([^.!?]+)"
        ],
        MemoryCategory.RELATIONSHIP: [
            r"(?:([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:is\s+my|works\s+with|reports\s+to|manages))\s*([^.!?]+)",
            r"(?:my\s+(?:boss|manager|colleague|friend|partner))\s*([^.!?]+)",
            r"(?:we\s+(?:work\s+together|collaborate|report)\s+(?:with|to))\s*([^.!?]+)"
        ],
        MemoryCategory.GOAL: [
            r"(?:my\s+goal(?:s)?|objective(?:s)?|target(?:s)?)\s+(?:is|are)\s+([^.!?]+)",
            r"(?:i\s+aim\s+to|i\s+plan\s+to|i\s+want\s+to\s+achieve)\s+([^.!?]+)",
            r"(?:by\s+(?:next\s+week|this\s+month|the\s+end\s+of))\s*,?\s*i\s+([^.!?]+)"
        ]
    }

    @classmethod
    def extract_from_messages(cls, messages: List[Dict[str, Any]]) -> List[ExtractedMemory]:
        """Extract memories using pattern matching"""
        extracted = []

        for message in messages:
            if message.get('role') == 'assistant':
                continue  # Skip AI responses for pattern extraction

            content = message.get('content', '')
            message_id = message.get('id')

            for category, patterns in cls.MEMORY_PATTERNS.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        fact = match.group(1).strip()

                        # Quality filters
                        if cls._is_valid_memory_fact(fact):
                            confidence = cls._calculate_pattern_confidence(fact, category, content)

                            if confidence >= EXTRACTION_CONFIDENCE_THRESHOLD:
                                memory = ExtractedMemory(
                                    fact=fact,
                                    category=category,
                                    confidence=confidence,
                                    source_message_id=message_id,
                                    evidence=[match.group(0)],
                                    extraction_method='pattern',
                                    metadata={
                                        'pattern': pattern,
                                        'original_text': match.group(0)
                                    }
                                )
                                extracted.append(memory)

        return cls._deduplicate_memories(extracted)

    @classmethod
    def _is_valid_memory_fact(cls, fact: str) -> bool:
        """Check if extracted fact is valid and meaningful"""
        if not fact or len(fact.strip()) < 10:
            return False

        if len(fact.strip()) > 500:  # Too long
            return False

        # Check for meaningful content
        meaningful_patterns = [
            r'\b(?:need|want|prefer|decide|plan|goal|remember)\b',
            r'\b(?:important|priority|critical|essential)\b',
            r'\b(?:boss|manager|colleague|friend|family)\b'
        ]

        has_meaningful_content = any(
            re.search(pattern, fact, re.IGNORECASE)
            for pattern in meaningful_patterns
        )

        return has_meaningful_content

    @classmethod
    def _calculate_pattern_confidence(cls, fact: str, category: MemoryCategory, context: str) -> float:
        """Calculate confidence score for pattern-extracted memory"""
        base_confidence = 0.6

        # Boost confidence based on factors
        confidence = base_confidence

        # Length factor (optimal length is 50-200 chars)
        fact_length = len(fact)
        if 50 <= fact_length <= 200:
            confidence += 0.1
        elif fact_length < 20:
            confidence -= 0.2

        # Category-specific factors
        if category == MemoryCategory.PRIORITY:
            if any(word in fact.lower() for word in ['must', 'critical', 'essential', 'urgent']):
                confidence += 0.2

        elif category == MemoryCategory.DECISION:
            if any(word in fact.lower() for word in ['decided', 'final', 'confirmed', 'approved']):
                confidence += 0.15

        elif category == MemoryCategory.PREFERENCE:
            if any(word in fact.lower() for word in ['prefer', 'like', 'enjoy', 'comfortable']):
                confidence += 0.1

        # Context evidence
        if any(word in context.lower() for word in ['remember', 'important', 'note', 'fyi']):
            confidence += 0.1

        return min(confidence, 0.95)  # Cap at 0.95 for pattern extraction

    @classmethod
    def _deduplicate_memories(cls, memories: List[ExtractedMemory]) -> List[ExtractedMemory]:
        """Remove duplicate memories based on similar content"""
        unique = []
        seen_facts = set()

        for memory in memories:
            # Normalize fact for comparison
            normalized_fact = memory.fact.lower().strip()

            # Simple similarity check
            is_duplicate = False
            for seen_fact in seen_facts:
                if cls._calculate_similarity(normalized_fact, seen_fact) > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(memory)
                seen_facts.add(normalized_fact)

        return unique

    @classmethod
    def _calculate_similarity(cls, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

class LLMMemoryExtractor:
    """LLM-based memory extraction using OpenAI-compatible API"""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    async def extract_memories(
        self,
        messages: List[Dict[str, Any]],
        existing_memories: List[Dict[str, Any]] = None
    ) -> List[ExtractedMemory]:
        """Extract memories using LLM analysis"""
        try:
            # Prepare conversation context
            conversation_text = self._format_conversation(messages)

            # Prepare existing memories context
            existing_context = ""
            if existing_memories:
                existing_context = self._format_existing_memories(existing_memories)

            # Create extraction prompt
            prompt = self._create_extraction_prompt(conversation_text, existing_context)

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )

            # Parse response
            content = response.choices[0].message.content
            return self._parse_llm_response(content, messages)

        except Exception as e:
            logger.error(f"LLM memory extraction failed: {e}")
            return []

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format conversation for LLM analysis"""
        formatted = []

        for message in messages:
            role = message.get('role', 'unknown')
            content = message.get('content', '')

            if role == 'user':
                formatted.append(f"User: {content}")
            elif role == 'assistant':
                formatted.append(f"Assistant: {content}")

        return "\n".join(formatted)

    def _format_existing_memories(self, memories: List[Dict[str, Any]]) -> str:
        """Format existing memories to avoid duplicates"""
        if not memories:
            return ""

        formatted = ["Existing memories to avoid duplicating:"]
        for memory in memories[:10]:  # Limit to 10 most recent
            formatted.append(f"- {memory['fact']} (Category: {memory['category']})")

        return "\n".join(formatted)

    def _get_system_prompt(self) -> str:
        """Get system prompt for memory extraction"""
        return """You are a memory extraction assistant. Your task is to identify important information from conversations that should be stored as persistent memories.

Extract the following types of information:
1. PRIORITIES: Important goals, tasks, or things the user needs to remember
2. DECISIONS: Key decisions made and the reasoning behind them
3. CONTEXT: Important background information or situational context
4. PREFERENCES: User preferences, likes, dislikes, communication style
5. RELATIONSHIPS: Information about people, relationships, or interactions
6. GOALS: User objectives, targets, or things they want to achieve

For each memory you identify:
- Extract the core fact as a concise statement
- Assign the appropriate category
- Assign a confidence score (0.0-1.0) based on how certain you are
- Provide supporting evidence from the conversation

Return your response as a JSON array with the following format:
[
  {
    "fact": "The user prefers to receive updates via email rather than chat",
    "category": "preference",
    "confidence": 0.85,
    "evidence": ["User: I prefer email updates over chat notifications"],
    "extraction_method": "llm"
  }
]

Be conservative - only extract information that is clearly important and actionable. Avoid extracting trivial or temporary information."""

    def _create_extraction_prompt(self, conversation: str, existing_context: str = "") -> str:
        """Create the extraction prompt"""
        prompt = f"""Extract important memories from the following conversation:

{existing_context}

Conversation:
{conversation}

Please identify any information that should be remembered for future conversations. Focus on:

1. User preferences and communication style
2. Important decisions or choices made
3. Priority tasks or goals mentioned
4. Context that might be relevant to future interactions
5. Information about people or relationships
6. Background information that might be needed later

Extract only information that is likely to be useful in future conversations."""

        return prompt

    def _parse_llm_response(self, response: str, messages: List[Dict[str, Any]]) -> List[ExtractedMemory]:
        """Parse LLM response into ExtractedMemory objects"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return []

            json_str = json_match.group(0)
            extracted_data = json.loads(json_str)

            memories = []
            for item in extracted_data:
                try:
                    # Validate category
                    category_str = item.get('category', '').lower()
                    try:
                        category = MemoryCategory(category_str)
                    except ValueError:
                        category = MemoryCategory.CONTEXT  # Default category

                    # Validate confidence
                    confidence = float(item.get('confidence', 0.7))
                    confidence = max(0.0, min(1.0, confidence))

                    # Find source message
                    evidence = item.get('evidence', [])
                    source_message_id = self._find_source_message(evidence, messages)

                    memory = ExtractedMemory(
                        fact=item.get('fact', ''),
                        category=category,
                        confidence=confidence,
                        source_message_id=source_message_id,
                        evidence=evidence,
                        extraction_method='llm',
                        metadata={
                            'llm_model': self.model,
                            'raw_response': item
                        }
                    )
                    memories.append(memory)

                except Exception as e:
                    logger.warning(f"Failed to parse memory item: {e}")
                    continue

            return memories

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return []

    def _find_source_message(self, evidence: List[str], messages: List[Dict[str, Any]]) -> Optional[str]:
        """Find the source message ID from evidence"""
        if not evidence:
            return None

        for evidence_text in evidence:
            for message in messages:
                if message.get('role') == 'user':
                    content = message.get('content', '')
                    if evidence_text in content:
                        return message.get('id')

        return None

class MemoryExtractionService:
    """Main service for extracting memories from conversations"""

    def __init__(self):
        self.pattern_extractor = MemoryPatternExtractor()
        self.llm_extractor = LLMMemoryExtractor()
        self.memory_service = None

    async def _ensure_memory_service(self):
        """Ensure memory service is initialized"""
        if self.memory_service is None:
            from memory_service import get_memory_service
            self.memory_service = await get_memory_service()

    async def extract_memories_from_conversation(
        self,
        context: ExtractionContext
    ) -> List[Dict[str, Any]]:
        """Extract memories from a conversation"""
        await self._ensure_memory_service()

        try:
            # Combine pattern extraction and LLM extraction
            pattern_memories = self.pattern_extractor.extract_from_messages(context.messages)

            llm_memories = []
            if context.mode != ExtractionMode.MANUAL:  # Use LLM for auto/batch modes
                llm_memories = await self.llm_extractor.extract_memories(
                    context.messages,
                    context.existing_memories
                )

            # Combine and deduplicate
            all_memories = pattern_memories + llm_memories
            unique_memories = self._merge_and_deduplicate_memories(all_memories)

            # Filter by confidence and create memory requests
            memory_requests = []
            for memory in unique_memories:
                if memory.confidence >= EXTRACTION_CONFIDENCE_THRESHOLD:
                    request = CreateMemoryRequest(
                        user_id=context.user_id,
                        fact=memory.fact,
                        category=memory.category,
                        confidence=memory.confidence,
                        source_type=SourceType.EXTRACTED_FROM_CHAT,
                        source_message_id=memory.source_message_id,
                        conversation_id=context.conversation_id,
                        metadata={
                            'extraction_method': memory.extraction_method,
                            'extraction_time': datetime.utcnow().isoformat(),
                            'evidence': memory.evidence,
                            **memory.metadata
                        }
                    )
                    memory_requests.append(request)

            # Limit to avoid overwhelming the user
            if len(memory_requests) > CONVERSATION_MEMORY_LIMIT:
                # Sort by confidence and take the top ones
                memory_requests.sort(key=lambda x: x.confidence, reverse=True)
                memory_requests = memory_requests[:CONVERSATION_MEMORY_LIMIT]

            # Create memories
            created_memories = []
            for request in memory_requests:
                try:
                    memory = await self.memory_service.create_memory(request)
                    created_memories.append(memory.__dict__)
                except Exception as e:
                    logger.warning(f"Failed to create memory: {e}")

            return created_memories

        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []

    def _merge_and_deduplicate_memories(
        self,
        memories: List[ExtractedMemory]
    ) -> List[ExtractedMemory]:
        """Merge memories from different extraction methods and remove duplicates"""
        if not memories:
            return []

        # Group by similar content
        groups = []
        for memory in memories:
            added_to_group = False

            for group in groups:
                # Check if memory is similar to group
                if any(
                    self._calculate_similarity(memory.fact, existing.fact) > 0.7
                    for existing in group
                ):
                    group.append(memory)
                    added_to_group = True
                    break

            if not added_to_group:
                groups.append([memory])

        # Select best memory from each group
        result = []
        for group in groups:
            # Sort by confidence, then by extraction method priority
            method_priority = {'llm': 3, 'pattern': 2, 'manual': 1}

            best_memory = max(
                group,
                key=lambda m: (
                    m.confidence,
                    method_priority.get(m.extraction_method, 0)
                )
            )
            result.append(best_memory)

        return result

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity for deduplication"""
        from MemoryPatternExtractor import MemoryPatternExtractor
        return MemoryPatternExtractor._calculate_similarity(text1.lower(), text2.lower())

# Global extraction service instance
_extraction_service = None

async def get_memory_extraction_service() -> MemoryExtractionService:
    """Get or create memory extraction service instance"""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = MemoryExtractionService()
    return _extraction_service