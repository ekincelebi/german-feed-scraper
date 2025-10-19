#!/usr/bin/env python3
"""
Script to scrape full article content from RSS feeds using BeautifulSoup.
This visits each article URL and extracts the complete content from the webpage.

Supports two scraping strategies:
1. Sequential: Process feeds one by one (slow but simple)
2. Parallel + Round-Robin: Process feeds concurrently with domain diversity (RECOMMENDED)
"""

import sys
from pathlib import Path
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock
from collections import defaultdict

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from app.database import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FullContentScraper:
    """Scraper that extracts full article content from webpages."""

    def __init__(
        self,
        max_workers: int = 15,
        max_per_domain: int = 3,
        feed_timeout: int = 30,
        article_timeout: int = 30,
        max_retries: int = 2
    ):
        """
        Initialize the scraper.

        Args:
            max_workers: Total number of concurrent workers (for parallel mode)
            max_per_domain: Max concurrent requests per domain (for parallel mode)
            feed_timeout: Timeout for RSS feed requests (seconds)
            article_timeout: Timeout for article content requests (seconds)
            max_retries: Number of retry attempts for failed feeds
        """
        self.max_workers = max_workers
        self.max_per_domain = max_per_domain
        self.feed_timeout = feed_timeout
        self.article_timeout = article_timeout
        self.max_retries = max_retries

        self.db_client = get_db()
        self.http_client = httpx.Client(timeout=30.0, follow_redirects=True)

        # Domain-based semaphores for rate limiting (parallel mode)
        self.domain_semaphores = {}
        self.semaphore_lock = Lock()

        # Statistics tracking
        self.stats = {
            'total_feeds': 0,
            'processed_feeds': 0,
            'successful_feeds': 0,
            'failed_feeds': 0,
            'total_articles': 0,
            'domains_covered': set(),
            'start_time': None,
            'end_time': None
        }
        self.stats_lock = Lock()

    def parse_date(self, date_string: str):
        """Parse various date formats from RSS feeds."""
        if not date_string:
            return None

        try:
            return parsedate_to_datetime(date_string)
        except Exception:
            pass

        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except Exception:
            pass

        return None

    def _get_domain_semaphore(self, domain: str) -> Semaphore:
        """Get or create a semaphore for the given domain (for parallel mode)."""
        with self.semaphore_lock:
            if domain not in self.domain_semaphores:
                self.domain_semaphores[domain] = Semaphore(self.max_per_domain)
            return self.domain_semaphores[domain]

    def _round_robin_order_feeds(self, feeds: list) -> list:
        """
        Order feeds using round-robin by domain for diversity.

        Args:
            feeds: List of feed dictionaries

        Returns:
            Reordered list of feeds
        """
        feeds_by_domain = defaultdict(list)
        for feed in feeds:
            domain = feed.get('domain', 'unknown')
            feeds_by_domain[domain].append(feed)

        logger.info(f"Grouping feeds across {len(feeds_by_domain)} domains:")
        for domain, domain_feeds in sorted(feeds_by_domain.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info(f"  {domain}: {len(domain_feeds)} feeds")

        # Round-robin through domains
        ordered_feeds = []
        domains = list(feeds_by_domain.keys())

        while any(feeds_by_domain.values()):
            for domain in domains:
                if feeds_by_domain[domain]:
                    ordered_feeds.append(feeds_by_domain[domain].pop(0))

        logger.info(f"Ordered {len(ordered_feeds)} feeds using round-robin strategy")
        return ordered_feeds

    def extract_full_content(self, url: str) -> str:
        """
        Visit article URL and extract full content using BeautifulSoup.

        Args:
            url: Article URL to scrape

        Returns:
            Cleaned article text content
        """
        try:
            logger.debug(f"  - Fetching full content from: {url}")

            # Fetch the webpage
            response = self.http_client.get(url)
            response.raise_for_status()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'lxml')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()

            # Strategy 1: Look for common article content containers
            article_content = None

            # Try common article selectors
            selectors = [
                'article',
                '.article-content',
                '.article-body',
                '.content',
                '.entry-content',
                '.post-content',
                'main',
                '[role="main"]',
                '.text',
                '.story-body',
            ]

            for selector in selectors:
                content = soup.select_one(selector)
                if content:
                    article_content = content
                    break

            # If no specific article container found, try to get main content
            if not article_content:
                article_content = soup.find('body')

            if not article_content:
                logger.warning(f"  - Could not find article content for: {url}")
                return ""

            # Extract text and clean it
            paragraphs = article_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

            # Get text from paragraphs
            text_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Filter out very short snippets
                    text_parts.append(text)

            full_text = '\n\n'.join(text_parts)

            # Clean up extra whitespace
            full_text = '\n'.join(line.strip() for line in full_text.split('\n') if line.strip())

            logger.debug(f"  - Extracted {len(full_text)} characters")
            return full_text

        except httpx.HTTPError as e:
            logger.error(f"  - HTTP error fetching {url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"  - Error extracting content from {url}: {e}")
            return ""

    def scrape_feed_with_full_content(self, feed_url: str, source_domain: str, retry_count: int = 0) -> dict:
        """
        Scrape articles from a feed and extract full content from each article URL.

        Args:
            feed_url: URL of the RSS feed
            source_domain: Domain of the source
            retry_count: Current retry attempt

        Returns:
            Dictionary with scraping results
        """
        try:
            logger.info(f"[{source_domain}] Processing feed: {feed_url}")

            # Parse RSS feed
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"  Feed has issues (bozo=True)")

            if not feed.entries:
                logger.warning(f"  No entries found in feed")
                return 0

            logger.info(f"  Found {len(feed.entries)} entries")

            saved_count = 0

            for entry in feed.entries:
                try:
                    # Get basic info from RSS
                    article_url = entry.get("link", "")
                    if not article_url:
                        continue

                    title = entry.get("title", "Untitled")

                    # Check if article already exists
                    existing = self.db_client.table("articles").select("id").eq("url", article_url).execute()
                    if existing.data:
                        logger.debug(f"  - Article already exists: {title}")
                        continue

                    # Extract full content from webpage
                    logger.info(f"  - Extracting: {title}")
                    full_content = self.extract_full_content(article_url)

                    if not full_content or len(full_content) < 50:
                        logger.warning(f"  - Insufficient content extracted, skipping")
                        continue

                    # Get published date
                    published_date = None
                    if hasattr(entry, "published"):
                        published_date = self.parse_date(entry.published)
                    elif hasattr(entry, "updated"):
                        published_date = self.parse_date(entry.updated)

                    # Get author
                    author = entry.get("author", None)

                    # Prepare article data
                    article_data = {
                        "url": article_url,
                        "title": title,
                        "content": full_content,
                        "published_date": published_date.isoformat() if published_date else None,
                        "author": author,
                        "source_feed": feed_url,
                        "source_domain": source_domain,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }

                    # Save to database
                    self.db_client.table("articles").insert(article_data).execute()
                    logger.info(f"  - Saved: {title} ({len(full_content)} chars)")
                    saved_count += 1

                    # Small delay to be polite
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"  - Error processing entry: {e}")
                    continue

            logger.info(f"[{source_domain}] Saved {saved_count} new articles from {feed_url}")
            return {
                'success': True,
                'feed_url': feed_url,
                'domain': source_domain,
                'articles_saved': saved_count,
                'error': None
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{source_domain}] Error processing feed {feed_url}: {error_msg}")

            # Retry logic
            if retry_count < self.max_retries:
                logger.info(f"[{source_domain}] Retrying feed (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self.scrape_feed_with_full_content(feed_url, source_domain, retry_count + 1)

            # Mark feed as failed
            self.update_feed_status(feed_url, "error", error_msg)

            return {
                'success': False,
                'feed_url': feed_url,
                'domain': source_domain,
                'articles_saved': 0,
                'error': error_msg
            }

    def update_feed_status(self, feed_url: str, status: str, error_message: str = None):
        """Update feed status in database."""
        try:
            update_data = {
                "status": status,
                "last_fetched": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if error_message:
                update_data["error_message"] = error_message

            self.db_client.table("feeds").update(update_data).eq("url", feed_url).execute()

        except Exception as e:
            logger.error(f"Error updating feed status: {e}")

    def _update_stats(self, result: dict):
        """Update scraping statistics."""
        with self.stats_lock:
            self.stats['processed_feeds'] += 1

            if result['success']:
                self.stats['successful_feeds'] += 1
                self.stats['total_articles'] += result['articles_saved']
                self.stats['domains_covered'].add(result['domain'])
            else:
                self.stats['failed_feeds'] += 1

    def _print_progress(self):
        """Print current progress."""
        with self.stats_lock:
            processed = self.stats['processed_feeds']
            total = self.stats['total_feeds']
            articles = self.stats['total_articles']
            percentage = (processed / total * 100) if total > 0 else 0

            elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            rate = processed / elapsed if elapsed > 0 else 0
            eta_seconds = (total - processed) / rate if rate > 0 else 0
            eta_minutes = int(eta_seconds / 60)

            logger.info(
                f"Progress: {processed}/{total} ({percentage:.1f}%) | "
                f"Articles: {articles:,} | "
                f"Rate: {rate:.1f} feeds/sec | "
                f"ETA: {eta_minutes} min"
            )

    def _print_final_report(self):
        """Print final scraping report."""
        elapsed = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        minutes = int(elapsed / 60)
        seconds = int(elapsed % 60)

        logger.info("\n" + "=" * 80)
        logger.info("SCRAPING COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"Total feeds: {self.stats['total_feeds']}")
        logger.info(f"Successful: {self.stats['successful_feeds']}")
        logger.info(f"Failed: {self.stats['failed_feeds']}")
        logger.info(f"Total articles: {self.stats['total_articles']:,}")
        logger.info(f"Domains covered: {len(self.stats['domains_covered'])}")
        logger.info(f"Duration: {minutes}m {seconds}s")
        if elapsed > 0:
            logger.info(f"Average: {self.stats['total_feeds'] / elapsed:.2f} feeds/sec")
        logger.info("=" * 80)

        if self.stats['domains_covered']:
            logger.info("\nDomains covered:")
            for domain in sorted(self.stats['domains_covered']):
                logger.info(f"  ✓ {domain}")

    def scrape_all_feeds_sequential(self) -> dict:
        """
        Scrape all active feeds sequentially (original method).

        Returns:
            Dictionary with statistics
        """
        self.stats['start_time'] = datetime.utcnow()

        try:
            # Get all active feeds
            response = self.db_client.table("feeds").select("*").eq("status", "active").execute()
            feeds = response.data

            if not feeds:
                logger.warning("No active feeds found in database")
                return {"total_feeds": 0, "total_articles": 0, "failed_feeds": 0}

            self.stats['total_feeds'] = len(feeds)
            logger.info(f"Found {len(feeds)} active feeds to scrape (SEQUENTIAL MODE)")

            for i, feed in enumerate(feeds, 1):
                feed_url = feed["url"]
                domain = feed.get("domain", "")

                logger.info(f"\n[{i}/{len(feeds)}] Processing feed from {domain}")

                result = self.scrape_feed_with_full_content(feed_url, domain)
                self._update_stats(result)

                if result['success']:
                    self.update_feed_status(feed_url, "active")

                # Delay between feeds
                time.sleep(2)

            self.stats['end_time'] = datetime.utcnow()
            self._print_final_report()

            return {
                "total_feeds": self.stats['total_feeds'],
                "total_articles": self.stats['total_articles'],
                "failed_feeds": self.stats['failed_feeds']
            }

        except Exception as e:
            logger.error(f"Error in scrape_all_feeds_sequential: {e}")
            self.stats['end_time'] = datetime.utcnow()
            return {"total_feeds": 0, "total_articles": 0, "failed_feeds": 0}

    def scrape_all_feeds_parallel(
        self,
        domain_filter: str = None,
        stratified: bool = False,
        feeds_per_domain: int = 5
    ) -> dict:
        """
        Scrape all active feeds using Parallel + Round-Robin strategy (RECOMMENDED).

        This method:
        - Orders feeds by domain using round-robin for diversity
        - Processes feeds in parallel for speed (10-50x faster)
        - Limits concurrent requests per domain (respectful scraping)

        Args:
            domain_filter: Optional domain to scrape exclusively
            stratified: If True, only scrape N feeds per domain
            feeds_per_domain: Number of feeds per domain for stratified sampling

        Returns:
            Dictionary with statistics
        """
        self.stats['start_time'] = datetime.utcnow()

        try:
            # Get all active feeds
            query = self.db_client.table("feeds").select("*").eq("status", "active")

            if domain_filter:
                query = query.eq("domain", domain_filter)

            response = query.execute()
            feeds = response.data

            if not feeds:
                logger.warning("No active feeds found in database")
                return self.stats

            # Apply stratified sampling if requested
            if stratified:
                feeds_by_domain = defaultdict(list)
                for feed in feeds:
                    domain = feed.get('domain', 'unknown')
                    feeds_by_domain[domain].append(feed)

                feeds = []
                for domain, domain_feeds in feeds_by_domain.items():
                    feeds.extend(domain_feeds[:feeds_per_domain])

                logger.info(f"Stratified sampling: {len(feeds)} feeds ({feeds_per_domain} per domain)")

            self.stats['total_feeds'] = len(feeds)

            logger.info("=" * 80)
            logger.info("PARALLEL + ROUND-ROBIN FULL CONTENT SCRAPER")
            logger.info("=" * 80)
            logger.info(f"Total feeds: {len(feeds)}")
            logger.info(f"Max workers: {self.max_workers}")
            logger.info(f"Max per domain: {self.max_per_domain}")
            logger.info("=" * 80)

            # Order feeds using round-robin
            ordered_feeds = self._round_robin_order_feeds(feeds)

            logger.info("Starting parallel scraping...\n")

            # Parallel processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all feeds
                future_to_feed = {}
                for feed in ordered_feeds:
                    feed_url = feed["url"]
                    domain = feed.get("domain", "")

                    # Get domain semaphore for rate limiting
                    semaphore = self._get_domain_semaphore(domain)

                    # Wrap scraping with semaphore
                    def scrape_with_limit(f_url, f_domain, sem):
                        with sem:
                            return self.scrape_feed_with_full_content(f_url, f_domain)

                    future = executor.submit(scrape_with_limit, feed_url, domain, semaphore)
                    future_to_feed[future] = feed

                # Process results as they complete
                for i, future in enumerate(as_completed(future_to_feed), 1):
                    feed = future_to_feed[future]

                    try:
                        result = future.result()
                        self._update_stats(result)

                        # Print progress every 10 feeds
                        if i % 10 == 0 or i == len(feeds):
                            self._print_progress()

                    except Exception as e:
                        logger.error(f"Unexpected error processing feed {feed['url']}: {e}")
                        self._update_stats({
                            'success': False,
                            'feed_url': feed['url'],
                            'domain': feed.get('domain', 'unknown'),
                            'articles_saved': 0,
                            'error': str(e)
                        })

            self.stats['end_time'] = datetime.utcnow()
            self._print_final_report()

            return self.stats

        except Exception as e:
            logger.error(f"Error in scrape_all_feeds_parallel: {e}")
            self.stats['end_time'] = datetime.utcnow()
            return self.stats

    def scrape_all_feeds(self, parallel: bool = True, **kwargs) -> dict:
        """
        Scrape all active feeds with full content extraction.

        Args:
            parallel: If True, use parallel round-robin (default). If False, use sequential.
            **kwargs: Additional arguments for parallel mode (domain_filter, stratified, feeds_per_domain)

        Returns:
            Dictionary with statistics
        """
        if parallel:
            return self.scrape_all_feeds_parallel(**kwargs)
        else:
            return self.scrape_all_feeds_sequential()

    def close(self):
        """Close HTTP client."""
        self.http_client.close()


def main():
    """Scrape articles with full content from all active feeds."""
    parser = argparse.ArgumentParser(
        description='Scrape full article content from RSS feeds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parallel mode (RECOMMENDED - 10-50x faster with diversity guarantee)
  python scripts/scrape_full_content.py

  # Sequential mode (original slow method)
  python scripts/scrape_full_content.py --sequential

  # Test with stratified sampling (5 feeds per domain)
  python scripts/scrape_full_content.py --stratified --feeds-per-domain 5

  # Scrape single domain only
  python scripts/scrape_full_content.py --domain rss.dw.com

  # Custom worker configuration
  python scripts/scrape_full_content.py --workers 20 --max-per-domain 5
        """
    )

    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Use sequential scraping instead of parallel (slower but simpler)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=15,
        help='Number of concurrent workers for parallel mode (default: 15)'
    )
    parser.add_argument(
        '--max-per-domain',
        type=int,
        default=3,
        help='Max concurrent requests per domain (default: 3)'
    )
    parser.add_argument(
        '--domain',
        type=str,
        help='Scrape only feeds from this domain'
    )
    parser.add_argument(
        '--stratified',
        action='store_true',
        help='Use stratified sampling (N feeds per domain)'
    )
    parser.add_argument(
        '--feeds-per-domain',
        type=int,
        default=5,
        help='Number of feeds per domain for stratified sampling (default: 5)'
    )

    args = parser.parse_args()

    logger.info("Starting full content scraping process...")
    logger.info("This will visit each article URL and extract complete content\n")

    scraper = FullContentScraper(
        max_workers=args.workers,
        max_per_domain=args.max_per_domain
    )

    try:
        if args.sequential:
            logger.info("Using SEQUENTIAL mode (slow)\n")
            stats = scraper.scrape_all_feeds(parallel=False)
        else:
            logger.info("Using PARALLEL + ROUND-ROBIN mode (RECOMMENDED)\n")
            stats = scraper.scrape_all_feeds(
                parallel=True,
                domain_filter=args.domain,
                stratified=args.stratified,
                feeds_per_domain=args.feeds_per_domain
            )

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
