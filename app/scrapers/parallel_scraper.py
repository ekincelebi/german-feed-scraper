"""
Parallel scraping with domain-based rate limiting.

Implements the Parallel + Round-Robin strategy for fast, diverse scraping
while respecting rate limits.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict

from app.utils.logger import get_logger
from app.scrapers.feed_fetcher import FeedFetcher
from app.scrapers.ordering_strategy import FeedOrderingStrategy
from app.database import get_db

logger = get_logger(__name__)


class ParallelScraper:
    """
    Parallel feed scraper with domain-based rate limiting.

    Features:
    - Concurrent scraping with configurable worker count
    - Domain-based semaphores to prevent overwhelming single servers
    - Round-robin domain ordering for diversity
    - Progress tracking and error handling
    - Retry logic for failed feeds
    """

    def __init__(
        self,
        max_workers: int = 15,
        max_per_domain: int = 3,
        feed_timeout: int = 30,
        delay_between_requests: float = 0.5,
        retry_failed: bool = True,
        max_retries: int = 2
    ):
        """
        Initialize parallel scraper.

        Args:
            max_workers: Total concurrent feeds across all domains
            max_per_domain: Max concurrent requests per domain
            feed_timeout: Timeout for feed fetching in seconds
            delay_between_requests: Delay between requests to same domain
            retry_failed: Whether to retry failed feeds
            max_retries: Maximum retry attempts per feed
        """
        self.max_workers = max_workers
        self.max_per_domain = max_per_domain
        self.feed_timeout = feed_timeout
        self.delay_between_requests = delay_between_requests
        self.retry_failed = retry_failed
        self.max_retries = max_retries

        self.feed_fetcher = FeedFetcher()
        self.db_client = get_db()

        # Domain-based semaphores for rate limiting
        self.domain_semaphores: Dict[str, Semaphore] = {}
        self.domain_last_request: Dict[str, float] = {}

        # Progress tracking
        self.progress_lock = Lock()
        self.feeds_processed = 0
        self.feeds_successful = 0
        self.feeds_failed = 0
        self.articles_saved = 0
        self.start_time: Optional[float] = None

        # Statistics by domain
        self.domain_stats = defaultdict(lambda: {"processed": 0, "articles": 0, "errors": 0})

    def get_domain_semaphore(self, domain: str) -> Semaphore:
        """
        Get or create semaphore for domain.

        Args:
            domain: Domain name

        Returns:
            Semaphore for the domain
        """
        if domain not in self.domain_semaphores:
            self.domain_semaphores[domain] = Semaphore(self.max_per_domain)
        return self.domain_semaphores[domain]

    def wait_for_rate_limit(self, domain: str):
        """
        Enforce rate limiting delay for domain.

        Args:
            domain: Domain name
        """
        if domain in self.domain_last_request:
            elapsed = time.time() - self.domain_last_request[domain]
            if elapsed < self.delay_between_requests:
                time.sleep(self.delay_between_requests - elapsed)

        self.domain_last_request[domain] = time.time()

    def extract_article_data(self, entry: Any, feed_url: str, source_domain: str) -> Dict[str, Any]:
        """
        Extract article data from a feed entry.

        Args:
            entry: Feed entry object
            feed_url: URL of the source feed
            source_domain: Domain of the source

        Returns:
            Dictionary with article data
        """
        # Get article URL
        url = entry.get("link", "")

        # Get title
        title = entry.get("title", "Untitled")

        # Get content (try multiple fields)
        content = ""
        if hasattr(entry, "content"):
            content = entry.content[0].value if entry.content else ""
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        # Get published date
        published_date = self.feed_fetcher.get_entry_date(entry)

        # Get author
        author = entry.get("author", None)

        return {
            "url": url,
            "title": title,
            "content": content,
            "published_date": published_date.isoformat() if published_date else None,
            "author": author,
            "source_feed": feed_url,
            "source_domain": source_domain,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    def save_article(self, article_data: Dict[str, Any]) -> bool:
        """
        Save an article to the database (upsert by URL).

        Args:
            article_data: Article data dictionary

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Check if article already exists
            existing = self.db_client.table("articles").select("id").eq("url", article_data["url"]).execute()

            if existing.data:
                return False

            # Insert new article
            self.db_client.table("articles").insert(article_data).execute()
            return True

        except Exception as e:
            logger.error(f"Error saving article {article_data.get('url')}: {e}")
            return False

    def scrape_single_feed(
        self,
        feed: Dict[str, Any],
        strategy: str = "full_archive"
    ) -> Dict[str, Any]:
        """
        Scrape a single feed with rate limiting.

        Args:
            feed: Feed dictionary with 'url' and 'domain' keys
            strategy: Fetch strategy ('full_archive' or 'daily_updates')

        Returns:
            Dictionary with scraping results
        """
        feed_url = feed.get("url")
        domain = feed.get("domain", "unknown")
        semaphore = self.get_domain_semaphore(domain)

        result = {
            "feed_url": feed_url,
            "domain": domain,
            "success": False,
            "articles_saved": 0,
            "error": None
        }

        try:
            # Acquire domain semaphore (limit concurrent requests per domain)
            with semaphore:
                # Enforce rate limit delay
                self.wait_for_rate_limit(domain)

                # Fetch feed entries
                entries = self.feed_fetcher.fetch_feed(feed_url, strategy=strategy)

                if entries is None:
                    result["error"] = "Failed to fetch feed"
                    return result

                if not entries:
                    result["success"] = True  # No error, just no entries
                    return result

                # Process and save articles
                saved_count = 0
                for entry in entries:
                    try:
                        article_data = self.extract_article_data(entry, feed_url, domain)

                        if not article_data["url"]:
                            continue

                        if self.save_article(article_data):
                            saved_count += 1

                    except Exception as e:
                        logger.debug(f"Error processing entry: {e}")
                        continue

                result["success"] = True
                result["articles_saved"] = saved_count

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error scraping feed {feed_url}: {e}")

        return result

    def update_progress(self, result: Dict[str, Any]):
        """
        Update progress statistics.

        Args:
            result: Scraping result dictionary
        """
        with self.progress_lock:
            self.feeds_processed += 1
            domain = result.get("domain", "unknown")

            if result["success"]:
                self.feeds_successful += 1
                articles = result["articles_saved"]
                self.articles_saved += articles
                self.domain_stats[domain]["processed"] += 1
                self.domain_stats[domain]["articles"] += articles
            else:
                self.feeds_failed += 1
                self.domain_stats[domain]["errors"] += 1

    def log_progress(self, total_feeds: int):
        """
        Log current progress.

        Args:
            total_feeds: Total number of feeds being processed
        """
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_min = elapsed / 60

            with self.progress_lock:
                percentage = (self.feeds_processed / total_feeds) * 100 if total_feeds > 0 else 0
                logger.info(
                    f"Progress: {self.feeds_processed}/{total_feeds} ({percentage:.1f}%) | "
                    f"Articles: {self.articles_saved} | "
                    f"Elapsed: {elapsed_min:.1f}m"
                )

    def scrape_feeds_parallel(
        self,
        feeds: List[Dict[str, Any]],
        strategy: str = "full_archive",
        use_round_robin: bool = True,
        progress_interval: int = 50
    ) -> Dict[str, Any]:
        """
        Scrape multiple feeds in parallel with round-robin ordering.

        Args:
            feeds: List of feed dictionaries
            strategy: Fetch strategy to use
            use_round_robin: Whether to use round-robin ordering
            progress_interval: Log progress every N feeds

        Returns:
            Dictionary with scraping statistics
        """
        if not feeds:
            logger.warning("No feeds provided for scraping")
            return self.get_statistics()

        # Order feeds for diversity
        if use_round_robin:
            logger.info("Applying round-robin ordering by domain...")
            feeds = FeedOrderingStrategy.round_robin_by_domain(feeds, domain_key="domain")

        total_feeds = len(feeds)
        self.start_time = time.time()

        logger.info(f"Starting parallel scraper...")
        logger.info(f"Total feeds: {total_feeds}")
        logger.info(f"Strategy: {strategy}")
        logger.info(f"Configuration: {self.max_workers} workers, {self.max_per_domain} max per domain")
        logger.info(f"{'=' * 60}")

        # Execute parallel scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_feed = {
                executor.submit(self.scrape_single_feed, feed, strategy): feed
                for feed in feeds
            }

            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_feed), 1):
                try:
                    result = future.result(timeout=self.feed_timeout)
                    self.update_progress(result)

                    # Log progress periodically
                    if i % progress_interval == 0:
                        self.log_progress(total_feeds)

                except Exception as e:
                    logger.error(f"Task failed with exception: {e}")
                    self.feeds_failed += 1

        # Final statistics
        stats = self.get_statistics()
        self.log_final_statistics(stats)

        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current scraping statistics.

        Returns:
            Dictionary with statistics
        """
        elapsed = time.time() - self.start_time if self.start_time else 0

        return {
            "total_feeds": self.feeds_processed,
            "successful_feeds": self.feeds_successful,
            "failed_feeds": self.feeds_failed,
            "total_articles": self.articles_saved,
            "elapsed_seconds": elapsed,
            "elapsed_minutes": elapsed / 60,
            "domains_covered": len(self.domain_stats),
            "domain_stats": dict(self.domain_stats)
        }

    def log_final_statistics(self, stats: Dict[str, Any]):
        """
        Log final scraping statistics.

        Args:
            stats: Statistics dictionary
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"SCRAPING COMPLETE!")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total feeds processed: {stats['total_feeds']}")
        logger.info(f"Successful: {stats['successful_feeds']}")
        logger.info(f"Failed: {stats['failed_feeds']}")
        logger.info(f"Total articles saved: {stats['total_articles']}")
        logger.info(f"Duration: {stats['elapsed_minutes']:.1f} minutes")
        logger.info(f"Domains covered: {stats['domains_covered']}")
        logger.info(f"{'=' * 60}")

        # Log per-domain statistics
        logger.info("\nDomain Statistics:")
        for domain, domain_stat in sorted(stats['domain_stats'].items()):
            logger.info(
                f"  {domain}: {domain_stat['processed']} feeds, "
                f"{domain_stat['articles']} articles, "
                f"{domain_stat['errors']} errors"
            )
        logger.info(f"{'=' * 60}\n")
