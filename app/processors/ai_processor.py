"""
AI-powered article processing for language learning features.
Uses Groq API with Llama 3.1 70B model for analysis.
"""

import json
import time
from typing import Dict, List, Any, Optional
from groq import Groq
from app.database import get_db
from app.utils.logger import get_logger
from app.settings import settings

logger = get_logger(__name__)


class ArticleProcessor:
    """Process articles with AI to extract language learning features."""

    # Groq pricing (per 1M tokens)
    INPUT_COST_PER_1M = 0.59
    OUTPUT_COST_PER_1M = 0.79

    # Model configuration
    MODEL = "llama-3.3-70b-versatile"  # Updated from deprecated llama-3.1-70b-versatile
    MAX_TOKENS = 1000  # Limit output tokens for cost control

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the AI processor.

        Args:
            api_key: Groq API key (defaults to environment variable)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=self.api_key)
        self.db_client = get_db()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []

    def _create_analysis_prompt(self, title: str, content: str) -> str:
        """
        Create the prompt for AI analysis.

        Args:
            title: Article title
            content: Article content

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this German article for language learning purposes. Provide a structured JSON response.

Article Title: {title}

Article Content:
{content[:4000]}  # Limit content to avoid excessive tokens

Provide analysis in this exact JSON format:
{{
  "language_level": "A1|A2|B1|B2|C1|C2",
  "topics": ["topic1", "topic2", "topic3"],
  "vocabulary": [
    {{
      "word": "example",
      "artikel": "der|die|das",
      "english": "translation",
      "plural": "plural_form"
    }}
  ],
  "grammar_patterns": [
    "Pattern 1: Brief explanation",
    "Pattern 2: Brief explanation"
  ]
}}

Guidelines:
1. Language Level (CEFR): Assess vocabulary complexity, sentence structure, and topic sophistication
2. Topics: Identify 2-4 main topics (e.g., "politics", "technology", "health", "culture")
3. Vocabulary: Extract 5-15 most important topic-related words with:
   - The German word
   - The artikel (der/die/das)
   - English translation
   - Plural form
4. Grammar Patterns: Identify 2-4 key grammar structures worth learning (e.g., "Passive voice: werden + past participle")

Return ONLY the JSON, no additional text."""

    def _parse_ai_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse AI response into structured data.

        Args:
            response_text: Raw response from AI

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Extract JSON from response (in case there's extra text)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                logger.error("No JSON found in AI response")
                return None

            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)

            # Validate required fields
            required_fields = ['language_level', 'topics', 'vocabulary', 'grammar_patterns']
            if not all(field in parsed for field in required_fields):
                logger.error(f"Missing required fields in AI response: {parsed.keys()}")
                return None

            # Validate language level
            valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
            if parsed['language_level'] not in valid_levels:
                logger.warning(f"Invalid language level: {parsed['language_level']}, defaulting to B2")
                parsed['language_level'] = 'B2'

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost

    def process_article(self, article_id: int, title: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Process a single article with AI analysis.

        Args:
            article_id: Article database ID
            title: Article title
            content: Article content

        Returns:
            Analysis dictionary or None if processing fails
        """
        if not content or len(content) < 100:
            logger.warning(f"Article {article_id} has insufficient content, skipping")
            return None

        # Check if already processed
        existing = self.db_client.table("article_analysis").select("id").eq("article_id", article_id).execute()
        if existing.data:
            logger.info(f"Article {article_id} already analyzed, skipping")
            return None

        for attempt in range(self.max_retries):
            try:
                # Call Groq API
                prompt = self._create_analysis_prompt(title, content)

                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a German language expert specializing in CEFR level assessment and language learning. Provide accurate, structured analysis."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=self.MAX_TOKENS,
                    temperature=0.3,  # Lower temperature for more consistent output
                )

                # Extract response
                response_text = response.choices[0].message.content
                usage = response.usage

                # Parse response
                analysis = self._parse_ai_response(response_text)
                if not analysis:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Failed to parse response for article {article_id}, retrying...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"Failed to parse response for article {article_id} after {self.max_retries} attempts")
                        self.failed_articles.append(article_id)
                        return None

                # Calculate cost
                total_tokens = usage.total_tokens
                cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

                # Update statistics
                self.total_articles_processed += 1
                self.total_tokens_used += total_tokens
                self.total_cost_usd += cost

                # Save to database
                result = {
                    'article_id': article_id,
                    'language_level': analysis['language_level'],
                    'topics': analysis['topics'],
                    'vocabulary': analysis['vocabulary'],
                    'grammar_patterns': analysis['grammar_patterns'],
                    'processing_tokens': total_tokens,
                    'processing_cost_usd': cost,
                    'model_used': self.MODEL
                }

                self.db_client.table("article_analysis").insert(result).execute()

                logger.info(
                    f"Processed article {article_id}: {analysis['language_level']}, "
                    f"{len(analysis['vocabulary'])} words, {total_tokens} tokens, ${cost:.4f}"
                )

                return result

            except Exception as e:
                logger.error(f"Error processing article {article_id} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    self.failed_articles.append(article_id)
                    return None

        return None

    def process_batch(
        self,
        limit: Optional[int] = None,
        max_cost_usd: float = 5.0,
        rate_limit_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process multiple articles in batch.

        Args:
            limit: Maximum number of articles to process (None for all)
            max_cost_usd: Maximum cost budget in USD
            rate_limit_delay: Delay between requests in seconds

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting batch processing (limit={limit}, max_cost=${max_cost_usd})")

        # Reset statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []

        # Fetch articles that haven't been analyzed yet
        query = self.db_client.table("articles").select("id, title, content").not_.is_("content", "null")

        # Exclude already processed articles
        processed_ids = self.db_client.table("article_analysis").select("article_id").execute()
        processed_id_list = [item['article_id'] for item in processed_ids.data]

        if processed_id_list:
            query = query.not_.in_("id", processed_id_list)

        if limit:
            query = query.limit(limit)

        articles = query.execute()

        if not articles.data:
            logger.info("No articles to process")
            return self.get_statistics()

        total_to_process = len(articles.data)
        logger.info(f"Found {total_to_process} articles to process")

        start_time = time.time()

        # Process each article
        for i, article in enumerate(articles.data, 1):
            # Check budget
            if self.total_cost_usd >= max_cost_usd:
                logger.warning(f"Reached budget limit of ${max_cost_usd:.2f}, stopping")
                break

            article_id = article['id']
            title = article.get('title', 'Untitled')
            content = article.get('content', '')

            logger.info(f"Processing article {i}/{total_to_process}: {article_id}")

            # Process article
            self.process_article(article_id, title, content)

            # Rate limiting
            if i < total_to_process:
                time.sleep(rate_limit_delay)

            # Progress update every 10 articles
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta_seconds = (total_to_process - i) / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60

                logger.info(
                    f"Progress: {i}/{total_to_process} ({i/total_to_process*100:.1f}%) | "
                    f"Cost: ${self.total_cost_usd:.4f} | "
                    f"Rate: {rate:.2f} articles/sec | "
                    f"ETA: {eta_minutes:.1f} min"
                )

        elapsed_time = time.time() - start_time

        logger.info(
            f"\nBatch processing complete!\n"
            f"Processed: {self.total_articles_processed}/{total_to_process}\n"
            f"Failed: {len(self.failed_articles)}\n"
            f"Total cost: ${self.total_cost_usd:.4f}\n"
            f"Time: {elapsed_time/60:.1f} minutes"
        )

        return self.get_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_processed': self.total_articles_processed,
            'total_failed': len(self.failed_articles),
            'failed_article_ids': self.failed_articles,
            'total_tokens': self.total_tokens_used,
            'total_cost_usd': round(self.total_cost_usd, 4),
            'average_tokens_per_article': round(self.total_tokens_used / self.total_articles_processed, 2) if self.total_articles_processed > 0 else 0,
            'average_cost_per_article': round(self.total_cost_usd / self.total_articles_processed, 6) if self.total_articles_processed > 0 else 0
        }
