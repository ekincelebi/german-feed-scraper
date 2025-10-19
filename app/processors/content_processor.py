"""
Content processor for cleaning and optimizing articles for language learners.
Works with analyzed articles to produce clean, focused versions.
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from groq import Groq
from app.database import get_db
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class ContentProcessor:
    """Process article content to make it cleaner and more focused for learners."""

    # Groq pricing (per 1M tokens)
    INPUT_COST_PER_1M = 0.59
    OUTPUT_COST_PER_1M = 0.79

    # Model configuration
    MODEL = "llama-3.3-70b-versatile"
    MAX_TOKENS = 4000  # Higher limit for content output

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the content processor.

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
        self.total_words_removed = 0

    def _create_cleaning_prompt(
        self,
        content: str,
        topics: List[str],
        language_level: str,
        title: str
    ) -> str:
        """
        Create the prompt for content cleaning.

        Args:
            content: Original article content
            topics: Main topics from analysis
            language_level: CEFR level
            title: Article title

        Returns:
            Formatted prompt string
        """
        return f"""You are a professional content editor preparing German news articles for language learners at {language_level} level.

Article Title: {title}
Main Topics: {', '.join(topics) if topics else 'general'}

Original Content:
{content[:8000]}

Your task: Clean this article to produce a focused, readable version for language learners.

REMOVE THESE COMPLETELY:
✗ HTML artifacts (e.g., "MuseumLouvreist" → fix spacing: "Museum Louvre ist")
✗ Website navigation ("Startseite", "Menü", "Suche", etc.)
✗ Author bylines, "Von [Name]", publication dates at start
✗ Social media prompts ("Teilen", "Folgen Sie uns", "Newsletter")
✗ Article recommendations ("Lesen Sie mehr", "Lesen Sie auch", "Das könnte Sie interessieren")
✗ Related article teasers and headlines at the end
✗ Copyright notices, disclaimers, legal text
✗ Advertisement text, promotional content
✗ English text mixed in (unless it's a proper quote)
✗ Repeated information or redundant paragraphs
✗ Off-topic tangents not related to: {', '.join(topics) if topics else 'the main story'}
✗ Source citations at the end (e.g., "Quelle: dpa", "Mit Material von...")

FIX FORMATTING:
→ Fix words merged together (no spaces)
→ Fix excessive line breaks or spacing
→ Ensure proper punctuation spacing
→ Remove special characters that are HTML artifacts

KEEP AS-IS:
✓ All core information related to the main story
✓ Original vocabulary and grammar at {language_level} level
✓ Direct quotes from people
✓ Important facts, dates, numbers
✓ Proper paragraph structure
✓ 100% German language

RULES:
1. NO simplification - keep {language_level} level vocabulary/grammar
2. NO summarization - keep all important details
3. NO translation or explanations
4. NO new content - only remove and fix

OUTPUT FORMAT:
Return ONLY the cleaned German article text. Start directly with the article content, no metadata, no notes."""

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

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split()) if text else 0

    def process_article_content(
        self,
        article_id: str,
        content: str,
        title: str,
        topics: List[str],
        language_level: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single article's content.

        Args:
            article_id: Article database ID
            content: Original article content
            title: Article title
            topics: Main topics from analysis
            language_level: CEFR level from analysis

        Returns:
            Processing result dictionary or None if processing fails
        """
        if not content or len(content) < 100:
            logger.warning(f"Article {article_id} has insufficient content, skipping")
            return None

        # Check if already processed
        existing = self.db_client.table("processed_content").select("id").eq("article_id", article_id).execute()
        if existing.data:
            logger.info(f"Article {article_id} already processed, skipping")
            return None

        original_word_count = self._count_words(content)

        for attempt in range(self.max_retries):
            try:
                # Call Groq API
                prompt = self._create_cleaning_prompt(content, topics, language_level, title)

                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional content editor specializing in educational materials. You clean and focus content while preserving its original language level and meaning."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=self.MAX_TOKENS,
                    temperature=0.2,  # Low temperature for consistent cleaning
                )

                # Extract response
                cleaned_content = response.choices[0].message.content.strip()
                usage = response.usage

                # Validate cleaned content
                if not cleaned_content or len(cleaned_content) < 50:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Cleaned content too short for article {article_id}, retrying...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"Failed to clean article {article_id} after {self.max_retries} attempts")
                        self.failed_articles.append(article_id)
                        return None

                cleaned_word_count = self._count_words(cleaned_content)
                words_removed = original_word_count - cleaned_word_count

                # Calculate cost
                total_tokens = usage.total_tokens
                cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

                # Update statistics
                self.total_articles_processed += 1
                self.total_tokens_used += total_tokens
                self.total_cost_usd += cost
                self.total_words_removed += words_removed

                # Save to database
                result = {
                    'article_id': article_id,
                    'original_content': content,
                    'cleaned_content': cleaned_content,
                    'word_count_before': original_word_count,
                    'word_count_after': cleaned_word_count,
                    'words_removed': words_removed,
                    'processing_tokens': total_tokens,
                    'processing_cost_usd': cost,
                    'model_used': self.MODEL
                }

                self.db_client.table("processed_content").insert(result).execute()

                reduction_pct = (words_removed / original_word_count * 100) if original_word_count > 0 else 0

                logger.info(
                    f"Processed article {article_id}: "
                    f"{original_word_count}→{cleaned_word_count} words (-{reduction_pct:.1f}%), "
                    f"{total_tokens} tokens, ${cost:.4f}"
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

    def process_analyzed_articles(
        self,
        limit: Optional[int] = None,
        max_cost_usd: float = 5.0,
        rate_limit_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process content for articles that have been analyzed.

        Args:
            limit: Maximum number of articles to process (None for all)
            max_cost_usd: Maximum cost budget in USD
            rate_limit_delay: Delay between requests in seconds

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting content processing (limit={limit}, max_cost=${max_cost_usd})")

        # Reset statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []
        self.total_words_removed = 0

        # Fetch analyzed articles that haven't been content-processed yet
        # Join articles with article_analysis to get analysis data
        query = """
            SELECT
                a.id,
                a.title,
                a.content,
                aa.topics,
                aa.language_level
            FROM articles a
            JOIN article_analysis aa ON a.id = aa.article_id
            LEFT JOIN processed_content pc ON a.id = pc.article_id
            WHERE pc.id IS NULL
            AND a.content IS NOT NULL
        """

        # For now, use simpler approach: get analyzed articles, check if processed
        analyzed = self.db_client.table("article_analysis").select(
            "article_id, topics, language_level"
        ).execute()

        if not analyzed.data:
            logger.info("No analyzed articles found")
            return self.get_statistics()

        # Get already processed article IDs
        processed = self.db_client.table("processed_content").select("article_id").execute()
        processed_ids = {item['article_id'] for item in processed.data}

        # Filter out already processed
        articles_to_process = [
            item for item in analyzed.data
            if item['article_id'] not in processed_ids
        ]

        if limit:
            articles_to_process = articles_to_process[:limit]

        if not articles_to_process:
            logger.info("No articles to process")
            return self.get_statistics()

        total_to_process = len(articles_to_process)
        logger.info(f"Found {total_to_process} analyzed articles to process")

        start_time = time.time()

        # Process each article
        for i, analysis_item in enumerate(articles_to_process, 1):
            # Check budget
            if self.total_cost_usd >= max_cost_usd:
                logger.warning(f"Reached budget limit of ${max_cost_usd:.2f}, stopping")
                break

            article_id = analysis_item['article_id']
            topics = analysis_item.get('topics', [])
            language_level = analysis_item.get('language_level', 'B1')

            # Fetch article content
            article = self.db_client.table("articles").select(
                "content, title"
            ).eq("id", article_id).execute()

            if not article.data:
                logger.warning(f"Article {article_id} not found, skipping")
                continue

            content = article.data[0].get('content', '')
            title = article.data[0].get('title', 'Untitled')

            logger.info(f"Processing article {i}/{total_to_process}: {article_id}")

            # Process article content
            self.process_article_content(
                article_id=article_id,
                content=content,
                title=title,
                topics=topics,
                language_level=language_level
            )

            # Rate limiting
            if i < total_to_process:
                time.sleep(rate_limit_delay)

            # Progress update every 10 articles
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta_seconds = (total_to_process - i) / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60
                avg_reduction = self.total_words_removed / self.total_articles_processed if self.total_articles_processed > 0 else 0

                logger.info(
                    f"Progress: {i}/{total_to_process} ({i/total_to_process*100:.1f}%) | "
                    f"Cost: ${self.total_cost_usd:.4f} | "
                    f"Avg reduction: {avg_reduction:.0f} words | "
                    f"Rate: {rate:.2f} articles/sec | "
                    f"ETA: {eta_minutes:.1f} min"
                )

        elapsed_time = time.time() - start_time

        logger.info(
            f"\nContent processing complete!\n"
            f"Processed: {self.total_articles_processed}/{total_to_process}\n"
            f"Failed: {len(self.failed_articles)}\n"
            f"Total cost: ${self.total_cost_usd:.4f}\n"
            f"Total words removed: {self.total_words_removed:,}\n"
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
            'total_words_removed': self.total_words_removed,
            'average_tokens_per_article': round(self.total_tokens_used / self.total_articles_processed, 2) if self.total_articles_processed > 0 else 0,
            'average_cost_per_article': round(self.total_cost_usd / self.total_articles_processed, 6) if self.total_articles_processed > 0 else 0,
            'average_words_removed': round(self.total_words_removed / self.total_articles_processed, 2) if self.total_articles_processed > 0 else 0
        }
