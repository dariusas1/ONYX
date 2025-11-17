"""
Conversation Summarizer Service for ONYX

This service handles LLM-based conversation summarization using DeepSeek
through LiteLLM proxy, including topic extraction and sentiment analysis.

Story 4-4: Auto-Summarization Pipeline
"""

import os
import json
import re
import time
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SummarizationRequest:
    """Request data for conversation summarization"""
    conversation_id: str
    message_range: Dict[str, int]
    user_id: str
    max_summary_length: int = 300
    min_summary_length: int = 20
    temperature: float = 0.3
    max_tokens: int = 150


@dataclass
class SummarizationResult:
    """Result of conversation summarization"""
    summary: str
    key_topics: List[str]
    sentiment: float
    confidence: float
    processing_time: int
    message_count: int
    model_used: str
    prompt_version: str = "1.0"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConversationSummarizer:
    """Service for LLM-based conversation summarization"""

    def __init__(self):
        """Initialize conversation summarizer"""
        self.connection_string = self._build_connection_string()
        self.litellm_proxy_url = os.getenv("LITELLM_PROXY_URL", "http://litellm-proxy:4000")
        self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-main")
        self.request_timeout = int(os.getenv("SUMMARIZATION_TIMEOUT_SECONDS", "30"))
        self.max_retries = int(os.getenv("SUMMARIZATION_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("SUMMARIZATION_RETRY_DELAY_MS", "1000"))

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "manus")
        user = os.getenv("POSTGRES_USER", "manus")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)

    # =========================================================================
    # Core Summarization Methods
    # =========================================================================

    async def generate_summary(self, request: SummarizationRequest) -> SummarizationResult:
        """
        Generate conversation summary using DeepSeek LLM

        Args:
            request: SummarizationRequest containing conversation details

        Returns:
            SummarizationResult with summary and metadata
        """
        start_time = time.time()

        try:
            # Fetch conversation messages
            messages = await self._fetch_conversation_messages(
                request.conversation_id,
                request.message_range
            )

            if not messages:
                raise ValueError(f"No messages found for conversation {request.conversation_id}")

            # Prepare conversation text for LLM
            conversation_text = self._format_conversation_text(messages)

            # Generate summary using LLM with retries
            summary_data = await self._call_llm_with_retry(conversation_text, request)

            # Extract topics and sentiment in parallel
            topics, sentiment = await asyncio.gather(
                self._extract_topics(summary_data["summary"], request),
                self._analyze_sentiment(messages)
            )

            processing_time = int((time.time() - start_time) * 1000)

            result = SummarizationResult(
                summary=summary_data["summary"],
                key_topics=topics,
                sentiment=sentiment,
                confidence=summary_data["confidence"],
                processing_time=processing_time,
                message_count=len(messages),
                model_used=summary_data["model_used"],
                prompt_version=request.prompt_version or "1.0",
                metadata={
                    "message_range": request.message_range,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "retry_count": summary_data.get("retry_count", 0)
                }
            )

            logger.info(
                f"Generated summary for conversation {request.conversation_id}: "
                f"{len(result.summary)} chars, {len(result.key_topics)} topics, "
                f"{result.processing_time}ms"
            )

            return result

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to generate summary for conversation {request.conversation_id}: {e}")

            # Return minimal result on error
            return SummarizationResult(
                summary=f"Error generating summary: {str(e)}",
                key_topics=[],
                sentiment=0.0,
                confidence=0.0,
                processing_time=processing_time,
                message_count=0,
                model_used=self.default_model,
                metadata={"error": str(e)}
            )

    # =========================================================================
    # LLM Integration Methods
    # =========================================================================

    async def _call_llm_with_retry(
        self,
        conversation_text: str,
        request: SummarizationRequest
    ) -> Dict[str, Any]:
        """Call LLM with retry logic"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self._call_llm_summarization(conversation_text, request)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"LLM call failed (attempt {attempt + 1}), retrying in {delay}ms: {e}")
                    await asyncio.sleep(delay / 1000)
                else:
                    logger.error(f"LLM call failed after {self.max_retries} attempts: {e}")

        # Final attempt failure
        raise Exception(f"LLM summarization failed after retries: {last_error}")

    async def _call_llm_summarization(
        self,
        conversation_text: str,
        request: SummarizationRequest
    ) -> Dict[str, Any]:
        """Call DeepSeek LLM for summarization"""
        prompt = self._build_summarization_prompt(conversation_text, request)

        try:
            response = await self._make_llm_request(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            if not response or "choices" not in response or not response["choices"]:
                raise ValueError("Invalid LLM response format")

            summary = response["choices"][0]["message"]["content"].strip()

            # Validate summary
            validation_result = self._validate_summary(summary, request)
            if not validation_result["valid"]:
                raise ValueError(f"Summary validation failed: {validation_result['reason']}")

            return {
                "summary": summary,
                "confidence": 0.9,  # High confidence for structured generation
                "model_used": self.default_model,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0)
            }

        except Exception as e:
            logger.error(f"LLM summarization call failed: {e}")
            raise

    def _build_summarization_prompt(
        self,
        conversation_text: str,
        request: SummarizationRequest
    ) -> str:
        """Build specialized prompt for conversation summarization"""
        return f"""
Summarize the following conversation in 2-3 sentences for future recall.

Focus on:
1. Key decisions made or conclusions reached
2. Important information shared or facts established
3. Action items, next steps, or commitments
4. User preferences or context revealed
5. Topics that might be important to reference later

Requirements:
- Length: {request.min_summary_length}-{request.max_summary_length} characters
- Factual and objective tone
- Include specific details where helpful
- Omit redundant information
- Focus on what would be valuable to recall in future conversations

Conversation:
{conversation_text}

Provide only the summary, no explanation or additional text."""

    async def _make_llm_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Make request to LiteLLM proxy"""
        import httpx

        request_data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.post(
                    f"{self.litellm_proxy_url}/chat/completions",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            raise Exception(f"HTTP error calling LLM: {e}")
        except Exception as e:
            raise Exception(f"Network error calling LLM: {e}")

    def _validate_summary(self, summary: str, request: SummarizationRequest) -> Dict[str, Any]:
        """Validate generated summary"""
        if not summary or not summary.strip():
            return {"valid": False, "reason": "Empty summary"}

        summary_length = len(summary.strip())

        if summary_length < request.min_summary_length:
            return {"valid": False, "reason": f"Summary too short: {summary_length} < {request.min_summary_length}"}

        if summary_length > request.max_summary_length:
            return {"valid": False, "reason": f"Summary too long: {summary_length} > {request.max_summary_length}"}

        # Check for common failure patterns
        failure_patterns = [
            "i cannot summarize",
            "i'm unable to summarize",
            "as an ai language model",
            "i don't have access to",
            "i cannot provide"
        ]

        summary_lower = summary.lower()
        for pattern in failure_patterns:
            if pattern in summary_lower:
                return {"valid": False, "reason": f"Summary contains refusal pattern: {pattern}"}

        return {"valid": True}

    # =========================================================================
    # Topic Extraction Methods
    # =========================================================================

    async def _extract_topics(self, summary: str, request: SummarizationRequest) -> List[str]:
        """Extract 3-5 key topics from summary using LLM"""
        prompt = f"""
Extract 3-5 key topics from this conversation summary.
Return as a JSON array of short topic phrases (1-3 words each).

Summary: {summary}

Example format: ["topic1", "topic2", "topic3"]

Requirements:
- 3-5 topics maximum
- Each topic should be 1-3 words
- Focus on main subjects, themes, or domains
- Avoid generic words like "discussion", "conversation", "talk"

Provide only the JSON array, no explanation."""

        try:
            response = await self._make_llm_request(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Lower temperature for consistent extraction
                max_tokens=100
            )

            if response and "choices" in response:
                topics_text = response["choices"][0]["message"]["content"].strip()

                # Try to parse as JSON
                try:
                    topics = json.loads(topics_text)
                    if isinstance(topics, list) and len(topics) > 0:
                        # Validate and normalize topics
                        return self._normalize_topics(topics[:5])  # Max 5 topics
                except json.JSONDecodeError:
                    pass  # Fall back to simple extraction

            # Fallback: simple keyword extraction
            return self._simple_topic_extraction(summary)

        except Exception as e:
            logger.warning(f"LLM topic extraction failed, using fallback: {e}")
            return self._simple_topic_extraction(summary)

    def _normalize_topics(self, topics: List[str]) -> List[str]:
        """Normalize and validate extracted topics"""
        normalized_topics = []
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'about', 'discussion',
            'conversation', 'talk', 'chat', 'user', 'assistant', 'ai', 'model'
        }

        for topic in topics:
            if isinstance(topic, str):
                # Clean and normalize
                topic = topic.strip().lower()
                topic = re.sub(r'[^\w\s]', '', topic)  # Remove punctuation
                words = topic.split()

                # Filter stop words and short words
                meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

                if meaningful_words:
                    normalized_topic = ' '.join(meaningful_words[:3])  # Max 3 words per topic
                    if normalized_topic and normalized_topic not in normalized_topics:
                        normalized_topics.append(normalized_topic)

        return normalized_topics

    def _simple_topic_extraction(self, text: str) -> List[str]:
        """Simple fallback topic extraction using keywords"""
        # Convert to lowercase and extract meaningful words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

        # Simple stop words filter
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was',
            'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new',
            'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'get', 'has', 'her', 'him',
            'his', 'how', 'its', 'made', 'may', 'our', 'out', 'see', 'she', 'too', 'use'
        }

        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]

        # Count word frequency
        word_freq = {}
        for word in meaningful_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Return top 5 most frequent words as topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:5]]

    # =========================================================================
    # Sentiment Analysis Methods
    # =========================================================================

    async def _analyze_sentiment(self, messages: List[Dict[str, Any]]) -> float:
        """Analyze conversation sentiment using simple keyword-based approach"""
        try:
            if not messages:
                return 0.0

            total_sentiment = 0.0
            message_count = 0

            for message in messages:
                if message.get("role") == "user":  # Analyze user messages only
                    content = message.get("content", "")
                    sentiment = self._calculate_message_sentiment(content)
                    total_sentiment += sentiment
                    message_count += 1

            if message_count == 0:
                return 0.0

            average_sentiment = total_sentiment / message_count

            # Ensure sentiment is within valid range
            return max(-1.0, min(1.0, average_sentiment))

        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return 0.0

    def _calculate_message_sentiment(self, content: str) -> float:
        """Calculate sentiment score for a single message"""
        # Simple keyword-based sentiment analysis
        positive_words = [
            'good', 'great', 'excellent', 'perfect', 'awesome', 'amazing', 'wonderful',
            'fantastic', 'love', 'like', 'enjoy', 'happy', 'pleased', 'satisfied',
            'thanks', 'thank', 'appreciate', 'helpful', 'useful', 'correct', 'right',
            'yes', 'agree', 'definitely', 'absolutely', 'brilliant', 'outstanding'
        ]

        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'wrong',
            'error', 'mistake', 'problem', 'issue', 'fail', 'failed', 'broken',
            'no', 'not', "don't", 'cannot', "can't", 'disagree', 'confused',
            'frustrated', 'angry', 'upset', 'disappointed', 'poor', 'worst'
        ]

        content_lower = content.lower()
        words = content_lower.split()

        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        # Calculate sentiment with dampening
        total_words = len(words)
        if total_words == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / max(total_words * 0.1, 1.0)
        return max(-1.0, min(1.0, sentiment))

    # =========================================================================
    # Data Access Methods
    # =========================================================================

    async def _fetch_conversation_messages(
        self,
        conversation_id: str,
        message_range: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Fetch messages within specified range"""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT role, content, created_at
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        conversation_id,
                        message_range["end"] - message_range["start"] + 1,
                        message_range["start"] - 1
                    )
                )
                messages = cur.fetchall()
                return [dict(msg) for msg in messages]

        except Exception as e:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def _format_conversation_text(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for LLM consumption"""
        formatted_parts = []

        for i, message in enumerate(messages, 1):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            created_at = message.get("created_at")

            if role == "user":
                role_display = "User"
            elif role == "assistant":
                role_display = "Assistant"
            else:
                role_display = role.title()

            formatted_message = f"[{i}] {role_display}: {content}"
            formatted_parts.append(formatted_message)

        return "\n\n".join(formatted_parts)

    # =========================================================================
    # Performance and Monitoring Methods
    # =========================================================================

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get summarizer performance metrics"""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_summaries,
                        AVG(processing_time_ms) as avg_processing_time,
                        MIN(processing_time_ms) as min_processing_time,
                        MAX(processing_time_ms) as max_processing_time,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN sentiment_score > 0.2 THEN 1 END) as positive_summaries,
                        COUNT(CASE WHEN sentiment_score < -0.2 THEN 1 END) as negative_summaries
                    FROM conversation_summaries
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    """
                )
                metrics = cur.fetchone()

            return {
                "model": self.default_model,
                "litellm_proxy_url": self.litellm_proxy_url,
                "request_timeout": self.request_timeout,
                "max_retries": self.max_retries,
                "last_24_hours": {
                    "total_summaries": metrics['total_summaries'],
                    "avg_processing_time_ms": float(metrics['avg_processing_time'] or 0),
                    "min_processing_time_ms": metrics['min_processing_time'],
                    "max_processing_time_ms": metrics['max_processing_time'],
                    "avg_confidence": float(metrics['avg_confidence'] or 0),
                    "positive_summaries": metrics['positive_summaries'],
                    "negative_summaries": metrics['negative_summaries']
                }
            }

        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
            return {"error": str(e)}
        finally:
            if 'conn' in locals():
                conn.close()


# Global service instance
_conversation_summarizer = None


def get_conversation_summarizer() -> ConversationSummarizer:
    """Get or create conversation summarizer instance"""
    global _conversation_summarizer
    if _conversation_summarizer is None:
        _conversation_summarizer = ConversationSummarizer()
    return _conversation_summarizer