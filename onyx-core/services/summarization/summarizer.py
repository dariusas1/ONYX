"""
Conversation Summarizer Service
Story 4-4: Auto-Summarization Pipeline

This service handles the core summarization logic using DeepSeek LLM,
including topic extraction and sentiment analysis.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import httpx
from dataclasses import dataclass

from .config import config
from .health_checker import health_checker

logger = logging.getLogger(__name__)

@dataclass
class SummarizationRequest:
    """Request structure for conversation summarization."""
    conversation_id: str
    message_range: Dict[str, int]
    user_id: str
    max_length: int = config.SUMMARY_MAX_LENGTH
    min_length: int = config.SUMMARY_MIN_LENGTH

@dataclass
class SummarizationResult:
    """Result structure for conversation summarization."""
    summary: str
    key_topics: List[str]
    sentiment: float
    confidence: float
    processing_time: int
    message_count: int
    model: str = "deepseek-main"
    prompt_version: str = "v1.0"

class ConversationSummarizer:
    """
    Service for generating conversation summaries using DeepSeek LLM.

    Features:
    - DeepSeek model integration via LiteLLM proxy
    - Specialized prompts for consistent summaries
    - Temperature control for reproducibility (0.3)
    - Token limits for concise output (150 tokens max)
    - Fallback handling for LLM failures
    - Topic extraction and sentiment analysis
    - Quality control with confidence scoring
    """

    def __init__(self, litellm_base_url: str = None):
        llm_config = config.get_llm_config()
        self.litellm_base_url = litellm_base_url or llm_config['base_url']
        self.model = llm_config['model']
        self.temperature = llm_config['temperature']
        self.max_tokens = llm_config['max_tokens']
        self.timeout = llm_config['timeout']

        # Prompts
        self.summary_prompt = """
Summarize the following conversation in 2-3 sentences for future recall. Focus on:
1. Key decisions made
2. Important information shared
3. Action items or next steps
4. User preferences or context revealed

Keep the summary factual and concise (20-300 characters).

Conversation:
{conversation_text}

Provide only the summary, no explanation."""

        self.topics_prompt = """Extract 3-5 key topics from this summary. Return as JSON array of short topic phrases (1-3 words each).

Summary: {summary}

Example format: ["topic1", "topic2", "topic3"]"""

        # Performance metrics
        self.metrics = {
            'summaries_generated': 0,
            'topics_extracted': 0,
            'sentiment_analyzed': 0,
            'errors': 0,
            'avg_processing_time': 0
        }

        logger.info("ConversationSummarizer initialized")

    async def generate_summary(self, request: SummarizationRequest) -> SummarizationResult:
        """
        Generate a summary for a conversation segment.

        Args:
            request: The summarization request

        Returns:
            SummarizationResult with summary, topics, sentiment, and metadata
        """
        start_time = datetime.utcnow()

        try:
            # Fetch conversation context
            messages = await self._get_messages_in_range(
                request.conversation_id,
                request.message_range
            )

            if not messages:
                raise ValueError("No messages found for summarization")

            # Prepare conversation text for LLM
            conversation_text = self._format_conversation(messages)

            # Generate summary using DeepSeek
            summary_result = await self._call_llm_summarization(conversation_text)

            # Validate summary length
            if not self._validate_summary_length(summary_result['summary'], request):
                raise ValueError(f"Summary length invalid: {len(summary_result['summary'])} characters")

            # Extract topics and sentiment in parallel
            topics_task = self._extract_topics(summary_result['summary'])
            sentiment_task = self._analyze_sentiment(messages)

            topics, sentiment = await asyncio.gather(topics_task, sentiment_task)

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Update metrics
            self.metrics['summaries_generated'] += 1
            self.metrics['topics_extracted'] += 1
            self.metrics['sentiment_analyzed'] += 1
            self._update_avg_processing_time(processing_time)

            result = SummarizationResult(
                summary=summary_result['summary'],
                key_topics=topics,
                sentiment=sentiment,
                confidence=summary_result['confidence'],
                processing_time=processing_time,
                message_count=len(messages)
            )

            logger.info(f"Summary generated for conversation {request.conversation_id}: "
                       f"{len(result.summary)} chars, {len(result.key_topics)} topics, "
                       f"sentiment {result.sentiment:.2f}")

            return result

        except Exception as error:
            self.metrics['errors'] += 1
            logger.error(f"Error generating summary for conversation {request.conversation_id}: {error}")
            raise ValueError(f"Summary generation failed: {error.message}")

    async def _get_messages_in_range(self, conversation_id: str, message_range: Dict[str, int]) -> List[Dict[str, Any]]:
        """Fetch messages within the specified range for a conversation."""
        try:
            # Import here to avoid circular imports
            from ..memory_service import get_memory_service

            # Get memory service which has the database pool
            memory_service = await get_memory_service()
            db_pool = getattr(memory_service, 'db_pool', None)

            if not db_pool:
                logger.error("Database pool not available for message retrieval")
                return []

            async with db_pool.acquire() as conn:
                # Fetch messages in the specified range, ordered by creation time
                records = await conn.fetch(
                    """
                    SELECT id, role, content, created_at
                    FROM messages
                    WHERE conversation_id = $1
                        AND is_deleted = FALSE
                        AND role IN ('user', 'assistant')
                    ORDER BY created_at ASC
                    LIMIT $2 OFFSET $3
                    """,
                    conversation_id,
                    message_range['end'] - message_range['start'] + 1,  # count of messages
                    max(0, message_range['start'] - 1)  # offset (0-indexed)
                )

                messages = []
                for record in records:
                    messages.append({
                        'id': str(record['id']),
                        'role': record['role'],
                        'content': record['content'],
                        'created_at': record['created_at']
                    })

                logger.info(f"Fetched {len(messages)} messages for conversation {conversation_id}")
                return messages

        except Exception as error:
            logger.error(f"Error fetching messages for conversation {conversation_id}: {error}")
            return []

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable conversation text."""
        formatted_messages = []

        for message in messages:
            role = message.get('role', 'unknown').title()
            content = message.get('content', '')
            created_at = message.get('created_at', datetime.utcnow())

            timestamp = created_at.strftime('%Y-%m-%d %H:%M:%S')
            formatted_message = f"[{timestamp}] {role}: {content}"
            formatted_messages.append(formatted_message)

        return '\n\n'.join(formatted_messages)

    async def _call_llm_summarization(self, conversation_text: str) -> Dict[str, Any]:
        """Call DeepSeek LLM for summarization with circuit breaker."""
        try:
            # Check circuit breaker status
            circuit_breaker = health_checker.get_circuit_breaker('litellm')
            if circuit_breaker and circuit_breaker.state == 'OPEN':
                raise ValueError("LiteLLM circuit breaker is OPEN - service unavailable")

            prompt = self.summary_prompt.format(conversation_text=conversation_text)

            # Use circuit breaker pattern if available
            if circuit_breaker:
                result = await circuit_breaker(self._make_llm_request)(prompt)
            else:
                result = await self._make_llm_request(prompt)

            return {
                'summary': result['summary'],
                'confidence': 0.9  # High confidence for auto-generated summaries
            }

        except Exception as error:
            logger.error(f"LLM summarization failed: {error}")
            raise ValueError(f"Failed to generate LLM summary: {error}")

    async def _make_llm_request(self, prompt: str) -> Dict[str, Any]:
        """Make actual LLM API request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.litellm_base_url}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
                )

                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"LLM API error: {response.status_code} {response.text}",
                        request=response.request,
                        response=response
                    )

                result = response.json()
                summary = result['choices'][0]['message']['content'].strip()

                return {'summary': summary}

        except httpx.TimeoutException:
            raise ValueError("LLM request timed out")
        except httpx.HTTPStatusError as error:
            raise ValueError(f"LLM API error: {error.response.status_code} {error.response.text}")
        except Exception as error:
            raise ValueError(f"Failed to generate LLM summary: {error}")

    def _validate_summary_length(self, summary: str, request: SummarizationRequest) -> bool:
        """Validate that summary meets length requirements."""
        length = len(summary)
        return request.min_length <= length <= request.max_length

    async def _extract_topics(self, summary: str) -> List[str]:
        """Extract key topics from a summary using LLM."""
        try:
            prompt = self.topics_prompt.format(summary=summary)

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.litellm_base_url}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,  # Low temperature for consistent extraction
                        "max_tokens": 100
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()

                    try:
                        topics = json.loads(content)
                        if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
                            # Validate and normalize topics
                            normalized_topics = []
                            for topic in topics[:5]:  # Max 5 topics
                                clean_topic = self._normalize_topic(topic)
                                if clean_topic and len(clean_topic) <= 50:
                                    normalized_topics.append(clean_topic)
                            return normalized_topics
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse topics JSON: {content}")

                # Fallback to simple keyword extraction
                return self._simple_keyword_extraction(summary)

        except Exception as error:
            logger.error(f"Topic extraction error: {error}")
            return self._simple_keyword_extraction(summary)

    def _normalize_topic(self, topic: str) -> str:
        """Normalize a topic by cleaning and standardizing it."""
        # Remove extra whitespace and special characters
        topic = re.sub(r'[^\w\s-]', '', topic.strip().lower())

        # Convert to title case
        topic = ' '.join(word.capitalize() for word in topic.split())

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [word for word in topic.split() if word.lower() not in stop_words and len(word) > 2]

        return ' '.join(words) if words else ''

    def _simple_keyword_extraction(self, text: str) -> List[str]:
        """Simple fallback topic extraction using keywords."""
        words = text.lower().split()

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

        # Filter and find unique words
        topics = []
        seen = set()

        for word in words:
            if (len(word) > 3 and
                word not in stop_words and
                word not in seen and
                word.isalpha()):

                topics.append(word.capitalize())
                seen.add(word)

                if len(topics) >= 5:  # Limit to 5 topics
                    break

        return topics

    async def _analyze_sentiment(self, messages: List[Dict[str, Any]]) -> float:
        """
        Analyze sentiment of conversation messages.

        Returns:
            Sentiment score from -1 (very negative) to 1 (very positive)
        """
        try:
            if not messages:
                return 0.0

            total_sentiment = 0.0
            message_count = 0

            # Positive and negative word lists
            positive_words = {
                'good', 'great', 'excellent', 'perfect', 'thanks', 'awesome', 'love',
                'fantastic', 'wonderful', 'amazing', 'brilliant', 'outstanding',
                'helpful', 'useful', 'effective', 'successful', 'positive', 'happy',
                'pleased', 'satisfied', 'impressed', 'delighted', 'thrilled'
            }

            negative_words = {
                'bad', 'terrible', 'awful', 'hate', 'wrong', 'problem', 'issue',
                'difficult', 'hard', 'frustrating', 'annoying', 'disappointing',
                'poor', 'weak', 'failed', 'failure', 'negative', 'unhappy',
                'dissatisfied', 'concerned', 'worried', 'troubled', 'stressed'
            }

            for message in messages:
                if message.get('role') == 'user':
                    content = message.get('content', '').lower()

                    # Count positive and negative words
                    pos_count = sum(1 for word in positive_words if word in content)
                    neg_count = sum(1 for word in negative_words if word in content)

                    # Simple sentiment calculation
                    if pos_count > 0 or neg_count > 0:
                        sentiment = (pos_count - neg_count) / max(pos_count + neg_count, 1)
                        total_sentiment += max(-1.0, min(1.0, sentiment))
                        message_count += 1

            if message_count > 0:
                return total_sentiment / message_count
            return 0.0

        except Exception as error:
            logger.error(f"Sentiment analysis error: {error}")
            return 0.0

    def _update_avg_processing_time(self, processing_time: int):
        """Update the average processing time metric."""
        current_avg = self.metrics['avg_processing_time']
        count = self.metrics['summaries_generated']

        if count == 1:
            self.metrics['avg_processing_time'] = processing_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics['avg_processing_time'] = int(
                alpha * processing_time + (1 - alpha) * current_avg
            )

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        return {
            **self.metrics,
            'updated_at': datetime.utcnow().isoformat()
        }

    async def test_connection(self) -> bool:
        """Test connection to LiteLLM proxy using health checker."""
        try:
            # Use health checker for comprehensive health status
            health_status = await health_checker.check_litellm_health()
            return health_status.is_healthy
        except Exception as error:
            logger.error(f"LiteLLM connection test failed: {error}")
            return False


# Factory function for easy instantiation
def create_conversation_summarizer(litellm_base_url: str = None) -> ConversationSummarizer:
    """Create and initialize ConversationSummarizer."""
    return ConversationSummarizer(litellm_base_url)