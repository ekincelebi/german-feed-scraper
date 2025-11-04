#!/usr/bin/env python3
"""
Fetch all articles published yesterday from configured feeds.

This script uses parallel scraping with round-robin ordering for optimal performance.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import feedparser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock
from typing import Dict, List, Optional
from app.database import get_db
from app.utils.logger import get_logger
from app.scrapers.content_extractors import ContentExtractor
from app.config.feed_config import FEED_SOURCES
from app.scrapers.ordering_strategy import FeedOrderingStrategy

logger = get_logger(__name__)


def is_from_yesterday(entry_date: datetime, reference_date: datetime = None) -> bool:
    """Check if an entry was published yesterday."""
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    yesterday_start = (reference_date - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday_end = yesterday_start + timedelta(days=1)

    return yesterday_start <= entry_date < yesterday_end


class ParallelYesterdayFetcher:
    """Parallel fetcher for yesterday's articles with domain-based rate limiting."""

    def __init__(self, max_workers: int = 15, max_per_domain: int = 3):
        self.max_workers = max_workers
        self.max_per_domain = max_per_domain
        self.domain_semaphores: Dict[str, Semaphore] = {}
        self.stats_lock = Lock()
        self.stats = {
            "feeds_processed": 0,
            "total_found": 0,
            "total_saved": 0,
            "total_existed": 0,
            "total_chars": 0,
            "successful_feeds": 0,
            "failed_feeds": 0
        }

    def _get_domain_semaphore(self, domain: str) -> Semaphore:
        """Get or create semaphore for domain."""
        if domain not in self.domain_semaphores:
            self.domain_semaphores[domain] = Semaphore(self.max_per_domain)
        return self.domain_semaphores[domain]

    def _update_stats(self, **kwargs):
        """Thread-safe stats update."""
        with self.stats_lock:
            for key, value in kwargs.items():
                self.stats[key] += value

    def fetch_feed_articles(self, feed_source, feed_index: int, total_feeds: int) -> dict:
        """Fetch yesterday's articles from a single feed."""
        feed_url = feed_source.url
        domain = feed_source.domain
        description = feed_source.description
        theme = feed_source.theme

        result = {
            "feed_url": feed_url,
            "domain": domain,
            "description": description,
            "success": False,
            "articles_found": 0,
            "articles_saved": 0,
            "articles_existed": 0,
            "total_chars": 0,
            "error": None
        }

        # Acquire domain semaphore
        semaphore = self._get_domain_semaphore(domain)
        semaphore.acquire()

        try:
            logger.info(f"[{feed_index}/{total_feeds}] {description}")
            logger.info(f"  Domain: {domain}")

            # Parse RSS feed
            feed = feedparser.parse(feed_url)

            if not feed.entries:
                logger.warning(f"  ⊘ No entries in feed")
                result["error"] = "No entries found"
                return result

            # Filter entries from yesterday
            yesterday_entries = []
            reference_date = datetime.now(timezone.utc)

            for entry in feed.entries:
                published_date = None
                if hasattr(entry, "published"):
                    try:
                        published_date = parsedate_to_datetime(entry.published)
                    except:
                        pass
                elif hasattr(entry, "updated"):
                    try:
                        published_date = parsedate_to_datetime(entry.updated)
                    except:
                        pass

                if published_date and is_from_yesterday(published_date, reference_date):
                    yesterday_entries.append(entry)

            if not yesterday_entries:
                logger.info(f"  ⊘ No articles from yesterday")
                result["success"] = True
                return result

            logger.info(f"  Found {len(yesterday_entries)} articles from yesterday")
            result["articles_found"] = len(yesterday_entries)

            # Process articles
            extractor = ContentExtractor(timeout=30)
            db_client = get_db()

            for i, entry in enumerate(yesterday_entries, 1):
                article_url = entry.get("link", "")
                if not article_url:
                    continue

                title = entry.get("title", "Untitled")

                # Check if exists
                existing = db_client.table("articles").select("id").eq("url", article_url).execute()
                if existing.data:
                    result["articles_existed"] += 1
                    continue

                # Extract content
                extraction_result = extractor.extract(article_url)

                full_content = None

                if extraction_result.get("error"):
                    if extraction_result.get("skip"):
                        continue
                    elif extraction_result.get("use_rss_content"):
                        rss_content = entry.get("summary") or entry.get("description") or ""
                        if rss_content and len(rss_content) > 50:
                            full_content = rss_content
                        else:
                            continue
                    else:
                        continue
                else:
                    full_content = extraction_result.get("content", "")

                # Fallback to RSS
                if not full_content or len(full_content) < 100:
                    rss_content = entry.get("summary") or entry.get("description") or ""
                    if rss_content and len(rss_content) > 50:
                        full_content = rss_content
                    else:
                        continue

                # Get metadata
                published_date = None
                if hasattr(entry, "published"):
                    try:
                        published_date = parsedate_to_datetime(entry.published)
                    except:
                        pass

                author = entry.get("author", None)

                # Save article
                article_data = {
                    "url": article_url,
                    "title": extraction_result.get("title") or title,
                    "content": full_content,
                    "published_date": published_date.isoformat() if published_date else None,
                    "author": author,
                    "source_feed": feed_url,
                    "source_domain": domain,
                    "theme": theme,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                db_client.table("articles").insert(article_data).execute()

                result["articles_saved"] += 1
                result["total_chars"] += len(full_content)

            extractor.close()

            logger.info(f"  ✓ Saved {result['articles_saved']}/{result['articles_found']} articles ({result['total_chars']:,} chars)")
            result["success"] = True

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            result["error"] = str(e)

        finally:
            semaphore.release()

        return result

    def fetch_all_parallel(self, feed_sources: List) -> dict:
        """Fetch articles from all feeds in parallel with round-robin ordering."""
        if not feed_sources:
            return self.stats

        # Convert to dict format for round_robin function
        feeds_dict = [
            {
                "source": feed_source,
                "domain": feed_source.domain,
                "description": feed_source.description
            }
            for feed_source in feed_sources
        ]

        # Apply round-robin ordering
        ordered_feeds = FeedOrderingStrategy.round_robin_by_domain(feeds_dict, domain_key="domain")

        total_feeds = len(ordered_feeds)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"FETCHING YESTERDAY'S ARTICLES FROM {total_feeds} FEEDS")

        reference_date = datetime.now(timezone.utc)
        yesterday_start = (reference_date - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday_end = yesterday_start + timedelta(days=1)

        logger.info(f"Date range: {yesterday_start.strftime('%Y-%m-%d %H:%M')} to {yesterday_end.strftime('%Y-%m-%d %H:%M')} UTC")
        logger.info(f"Parallel workers: {self.max_workers}")
        logger.info(f"Max per domain: {self.max_per_domain}")
        logger.info(f"{'=' * 80}\n")

        # Process feeds in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.fetch_feed_articles,
                    feed_dict["source"],
                    i,
                    total_feeds
                ): feed_dict
                for i, feed_dict in enumerate(ordered_feeds, 1)
            }

            for future in as_completed(futures):
                feed_dict = futures[future]
                try:
                    result = future.result()

                    self._update_stats(feeds_processed=1)

                    if result["success"]:
                        self._update_stats(
                            successful_feeds=1,
                            total_found=result["articles_found"],
                            total_saved=result["articles_saved"],
                            total_existed=result["articles_existed"],
                            total_chars=result["total_chars"]
                        )
                    else:
                        self._update_stats(failed_feeds=1)

                except Exception as e:
                    logger.error(f"Error processing {feed_dict['description']}: {e}")
                    self._update_stats(failed_feeds=1, feeds_processed=1)

        return self.stats


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch all articles published yesterday with parallel processing"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=15,
        help="Number of parallel workers (default: 15)"
    )
    parser.add_argument(
        "--max-per-domain",
        type=int,
        default=3,
        help="Max concurrent requests per domain (default: 3)"
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Filter by specific domain"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of feeds to process"
    )

    args = parser.parse_args()

    try:
        # Get feeds from config
        feeds = list(FEED_SOURCES)

        # Apply filters
        if args.domain:
            feeds = [f for f in feeds if f.domain == args.domain]

        if args.limit:
            feeds = feeds[:args.limit]

        if not feeds:
            logger.warning("No feeds found")
            return

        # Initialize parallel fetcher
        fetcher = ParallelYesterdayFetcher(
            max_workers=args.workers,
            max_per_domain=args.max_per_domain
        )

        # Fetch all articles in parallel
        start_time = datetime.now()
        stats = fetcher.fetch_all_parallel(feeds)
        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Print summary
        avg_chars = stats["total_chars"] / stats["total_saved"] if stats["total_saved"] > 0 else 0

        logger.info(f"\n{'=' * 80}")
        logger.info(f"SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Feeds processed: {stats['feeds_processed']}")
        logger.info(f"Successful: {stats['successful_feeds']}")
        logger.info(f"Failed: {stats['failed_feeds']}")
        logger.info(f"Total articles found: {stats['total_found']}")
        logger.info(f"New articles saved: {stats['total_saved']}")
        logger.info(f"Already existed: {stats['total_existed']}")
        logger.info(f"Total content: {stats['total_chars']:,} characters")
        logger.info(f"Average per article: {avg_chars:,.0f} characters")
        logger.info(f"Time elapsed: {elapsed_time:.1f} seconds")
        logger.info(f"{'=' * 80}\n")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
