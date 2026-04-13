"""
Content processor for cleaning and optimizing articles for language learners.
Works with analyzed articles to produce clean, focused versions.
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from groq import Groq
from app.database import get_db
from app.utils.logger import get_logger
from app.settings import settings

logger = get_logger(__name__)


class ContentProcessor:
    """Process article content to make it cleaner and more focused for learners."""

    # Groq pricing (per 1M tokens)
    INPUT_COST_PER_1M = 0.59
    OUTPUT_COST_PER_1M = 0.79

    # Model configuration
    MODEL = "llama-3.3-70b-versatile"
    MAX_TOKENS = 4000  # Higher limit for content output
    ESTIMATED_COST_PER_ARTICLE_USD = 0.01
    FETCH_BATCH_SIZE = 250

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
        self.in_flight_tasks = 0

        # Thread safety for parallel processing
        self.stats_lock = Lock()

    @staticmethod
    def _is_duplicate_error(error: Exception) -> bool:
        error_text = str(error).lower()
        return "duplicate key value" in error_text or "23505" in error_text

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

Your task:  You are an AI text cleaning tool designed to prepare German-language articles for language learners. Your primary function is to refine articles by removing unnecessary elements and correcting formatting errors, all while preserving the original language level and core content.

Instructions:

Remove Completely:


HTML artifacts (e.g., fix spacing issues like "MuseumLouvreist" to "Museum Louvre ist").
Website navigation elements (e.g., "Startseite," "Menü," "Suche").
Author bylines ("Von [Name]") and publication dates at the beginning of the article.
Social media prompts (e.g., "Teilen," "Folgen Sie uns," "Newsletter").
Article recommendations (e.g., "Lesen Sie mehr," "Lesen Sie auch," "Das könnte Sie interessieren").
Related article teasers and headlines at the end of the article.
Copyright notices, disclaimers, and legal text.
Advertisement text and promotional content.
Non-German text.
Repeated information or redundant paragraphs.
Off-topic tangents unrelated to the article's main story. An off-topic tangent is defined as information outside of the core subject matter of the article.
Source citations at the end of the article (e.g., "Quelle: dpa," "Mit Material von...").

Correct the Following Formatting Issues:


Fix merged words (words without spaces).
Fix excessive line breaks (more than two consecutive line breaks should be reduced to one).
Fix excessive spacing.
Ensure proper punctuation spacing.
Remove special characters that are HTML artifacts.
Improve paragraph formatting for readability (add line breaks between paragraphs).

Preserve the Following:


All core information related to the main story.
Original vocabulary and grammar.
Direct quotes from people.
Important facts, dates, and numbers.
Proper paragraph structure.
100% German language content.

Rules:


Do NOT simplify the language. Maintain the original vocabulary and grammar.
Do NOT summarize the article. Keep all important details.
Do NOT translate or add explanations.
Do NOT add new content. Only remove and fix existing text.
If you are unsure whether a piece of information is core to the story or an off-topic tangent, err on the side of caution and keep the information.
The original text is German but may contain noise during web scraping, remove the non German text.

Output Format:


Return ONLY the cleaned article text in German. Start directly with the article content. Do not include any metadata or notes.

"""

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

    def _get_unprocessed_articles(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch unprocessed articles in paginated batches to avoid full-table scans."""
        collected: List[Dict[str, Any]] = []
        offset = 0

        while True:
            upper = offset + self.FETCH_BATCH_SIZE - 1
            articles_response = (
                self.db_client
                .table("articles")
                .select("id, title, content, theme")
                .order("created_at", desc=True)
                .range(offset, upper)
                .execute()
            )
            article_batch = articles_response.data or []
            if not article_batch:
                break

            article_ids = [item["id"] for item in article_batch if item.get("id")]
            processed_ids = set()
            if article_ids:
                processed_response = (
                    self.db_client
                    .table("processed_content")
                    .select("article_id")
                    .in_("article_id", article_ids)
                    .execute()
                )
                processed_ids = {item["article_id"] for item in (processed_response.data or [])}

            for item in article_batch:
                if item.get("content") and item["id"] not in processed_ids:
                    collected.append(item)
                    if limit and len(collected) >= limit:
                        return collected

            if len(article_batch) < self.FETCH_BATCH_SIZE:
                break
            offset += self.FETCH_BATCH_SIZE

        return collected

    def process_article_content(
        self,
        article_id: str,
        content: str,
        title: str,
        topics: List[str] = None,
        language_level: str = "B1"
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single article's content.

        Args:
            article_id: Article database ID
            content: Original article content
            title: Article title
            topics: Main topics (optional, will use generic if not provided)
            language_level: CEFR level (optional, defaults to B1)

        Returns:
            Processing result dictionary or None if processing fails
        """
        if not content or len(content) < 100:
            logger.warning(f"Article {article_id} has insufficient content, skipping")
            return None

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
                        with self.stats_lock:
                            self.failed_articles.append(article_id)
                        return None

                # Calculate cost
                total_tokens = usage.total_tokens
                cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

                # Save to database (simplified schema)
                result = {
                    'article_id': article_id,
                    'cleaned_content': cleaned_content,
                    'processing_tokens': total_tokens,
                    'processing_cost_usd': cost,
                    'model_used': self.MODEL
                }

                try:
                    self.db_client.table("processed_content").insert(result).execute()
                except Exception as db_error:
                    if self._is_duplicate_error(db_error):
                        logger.info(f"Article {article_id} was processed concurrently, skipping")
                        return None
                    raise

                # Update statistics only after successful insert
                with self.stats_lock:
                    self.total_articles_processed += 1
                    self.total_tokens_used += total_tokens
                    self.total_cost_usd += cost

                logger.info(
                    f"Processed article {article_id}: "
                    f"{len(cleaned_content)} chars, "
                    f"{total_tokens} tokens, ${cost:.4f}"
                )

                return result

            except Exception as e:
                logger.error(f"Error processing article {article_id} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    with self.stats_lock:
                        self.failed_articles.append(article_id)
                    return None

        return None

    def process_articles_parallel(
        self,
        limit: Optional[int] = None,
        max_cost_usd: float = 5.0,
        rate_limit_delay: float = 0.1,
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Process content for articles in parallel (no analysis required).

        Args:
            limit: Maximum number of articles to process (None for all)
            max_cost_usd: Maximum cost budget in USD
            rate_limit_delay: Delay between batch submissions in seconds
            max_workers: Number of parallel workers (default: 5)

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting parallel content processing (workers={max_workers}, limit={limit}, max_cost=${max_cost_usd})")

        # Reset statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []
        self.in_flight_tasks = 0

        articles_to_process = self._get_unprocessed_articles(limit=limit)

        if not articles_to_process:
            logger.info("No articles to process (all already processed)")
            return self.get_statistics()

        total_to_process = len(articles_to_process)
        logger.info(f"Found {total_to_process} articles to process")

        start_time = time.time()

        # Process articles in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for i, article in enumerate(articles_to_process, 1):
                # Check budget before submitting new tasks
                with self.stats_lock:
                    projected_cost = self.total_cost_usd + (
                        (self.in_flight_tasks + 1) * self.ESTIMATED_COST_PER_ARTICLE_USD
                    )
                    if projected_cost >= max_cost_usd:
                        logger.warning(
                            f"Reached projected budget limit of ${max_cost_usd:.2f}, stopping submissions"
                        )
                        break
                    self.in_flight_tasks += 1

                article_id = article['id']
                content = article.get('content', '')
                title = article.get('title', 'Untitled')
                theme = article.get('theme', 'general')

                # Submit task
                future = executor.submit(
                    self.process_article_content,
                    article_id=article_id,
                    content=content,
                    title=title,
                    topics=[theme] if theme else [],
                    language_level='B1'
                )
                futures[future] = (i, title)

                # Small delay between submissions to avoid overwhelming API
                if rate_limit_delay > 0:
                    time.sleep(rate_limit_delay)

            # Process completed tasks
            completed_count = 0
            for future in as_completed(futures):
                completed_count += 1
                idx, title = futures[future]

                try:
                    result = future.result()
                    if result:
                        logger.info(f"✓ [{completed_count}/{len(futures)}] Completed: {title[:50]}...")
                    else:
                        logger.warning(f"⊘ [{completed_count}/{len(futures)}] Skipped/Failed: {title[:50]}...")
                except Exception as e:
                    logger.error(f"✗ [{completed_count}/{len(futures)}] Error processing {title[:50]}...: {e}")
                finally:
                    with self.stats_lock:
                        self.in_flight_tasks = max(0, self.in_flight_tasks - 1)

                # Progress update every 10 articles
                if completed_count % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed if elapsed > 0 else 0
                    eta_seconds = (len(futures) - completed_count) / rate if rate > 0 else 0
                    eta_minutes = eta_seconds / 60

                    logger.info(
                        f"Progress: {completed_count}/{len(futures)} ({completed_count/len(futures)*100:.1f}%) | "
                        f"Cost: ${self.total_cost_usd:.4f} | "
                        f"Rate: {rate:.2f} articles/sec | "
                        f"ETA: {eta_minutes:.1f} min"
                    )

        elapsed_time = time.time() - start_time

        logger.info(
            f"\nParallel content processing complete!\n"
            f"Processed: {self.total_articles_processed}/{total_to_process}\n"
            f"Failed: {len(self.failed_articles)}\n"
            f"Total cost: ${self.total_cost_usd:.4f}\n"
            f"Time: {elapsed_time/60:.1f} minutes\n"
            f"Rate: {self.total_articles_processed/elapsed_time:.2f} articles/sec"
        )

        return self.get_statistics()

    def process_articles(
        self,
        limit: Optional[int] = None,
        max_cost_usd: float = 5.0,
        rate_limit_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process content for articles (no analysis required).

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

        articles_to_process = self._get_unprocessed_articles(limit=limit)

        if not articles_to_process:
            logger.info("No articles to process (all already processed)")
            return self.get_statistics()

        total_to_process = len(articles_to_process)
        logger.info(f"Found {total_to_process} articles to process")

        start_time = time.time()

        # Process each article
        for i, article in enumerate(articles_to_process, 1):
            # Check budget
            if self.total_cost_usd >= max_cost_usd:
                logger.warning(f"Reached budget limit of ${max_cost_usd:.2f}, stopping")
                break

            article_id = article['id']
            content = article.get('content', '')
            title = article.get('title', 'Untitled')
            theme = article.get('theme', 'general')

            logger.info(f"Processing article {i}/{total_to_process}: {title[:50]}...")

            # Process article content (no analysis data needed)
            self.process_article_content(
                article_id=article_id,
                content=content,
                title=title,
                topics=[theme] if theme else [],  # Use theme as topic
                language_level='B1'  # Default level
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

                logger.info(
                    f"Progress: {i}/{total_to_process} ({i/total_to_process*100:.1f}%) | "
                    f"Cost: ${self.total_cost_usd:.4f} | "
                    f"Rate: {rate:.2f} articles/sec | "
                    f"ETA: {eta_minutes:.1f} min"
                )

        elapsed_time = time.time() - start_time

        logger.info(
            f"\nContent processing complete!\n"
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
