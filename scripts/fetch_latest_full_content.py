#!/usr/bin/env python3
"""
Fetch latest article from each feed with FULL CONTENT extraction.

Uses domain-specific content extractors to get complete article content,
not just RSS summaries.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import feedparser
from datetime import datetime, timezone
from app.database import get_db
from app.utils.logger import get_logger
from app.scrapers.content_extractors import ContentExtractor

logger = get_logger(__name__)


def fetch_latest_with_full_content(feed_url: str, domain: str, description: str, theme: str = None) -> dict:
    """
    Fetch latest entry from feed and extract full content.

    Args:
        feed_url: URL of the RSS feed
        domain: Domain of the source
        description: Human-readable feed description
        theme: Theme/category of the feed

    Returns:
        Dictionary with result
    """
    result = {
        "feed_url": feed_url,
        "domain": domain,
        "success": False,
        "articles_saved": 0,
        "latest_title": None,
        "content_length": 0,
        "error": None
    }

    extractor = None

    try:
        logger.info(f"Fetching latest from: {feed_url}")

        # Parse RSS feed
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            logger.warning(f"⊘ No entries found in feed")
            result["error"] = "No entries found"
            return result

        # Get the first (most recent) entry
        latest_entry = feed.entries[0]
        article_url = latest_entry.get("link", "")

        if not article_url:
            logger.warning(f"⊘ No URL in latest entry")
            result["error"] = "No URL"
            return result

        title = latest_entry.get("title", "Untitled")
        logger.info(f"Latest: {title}")
        logger.info(f"URL: {article_url}")

        # Check if article already exists
        db_client = get_db()
        existing = db_client.table("articles").select("id").eq("url", article_url).execute()

        if existing.data:
            logger.info(f"⊘ Already exists in database")
            result["success"] = True
            result["latest_title"] = title
            return result

        # Extract FULL content using domain-specific extractor
        extractor = ContentExtractor(timeout=30)
        logger.info(f"Extracting full content...")

        extraction_result = extractor.extract(article_url)

        # Check if extraction was successful
        if extraction_result.get("error"):
            if extraction_result.get("skip"):
                # Intentionally skipped (e.g., liveblog)
                logger.info(f"⊘ Skipped: {extraction_result['error']}")
                result["error"] = extraction_result["error"]
                return result
            elif extraction_result.get("use_rss_content"):
                # JavaScript-rendered page, use RSS content as fallback
                logger.info(f"⊘ JS-rendered page, using RSS content fallback")
                rss_content = latest_entry.get("summary") or latest_entry.get("description") or ""
                if rss_content and len(rss_content) > 50:
                    full_content = rss_content
                    logger.info(f"✓ Using RSS content: {len(full_content)} chars")
                else:
                    logger.warning(f"⊘ No usable RSS content")
                    result["error"] = "No content available"
                    return result
            else:
                logger.error(f"✗ Extraction error: {extraction_result['error']}")
                result["error"] = extraction_result["error"]
                return result
        else:
            full_content = extraction_result.get("content", "")

        if not full_content or len(full_content) < 100:
            # Try RSS content as fallback
            rss_content = latest_entry.get("summary") or latest_entry.get("description") or ""
            if rss_content and len(rss_content) > 50:
                full_content = rss_content
                logger.info(f"⊘ Using RSS content as fallback: {len(full_content)} chars")
            else:
                logger.warning(f"⊘ Insufficient content extracted ({len(full_content)} chars)")
                result["error"] = "Insufficient content"
                return result

        # Get published date
        published_date = None
        if hasattr(latest_entry, "published"):
            try:
                from email.utils import parsedate_to_datetime
                published_date = parsedate_to_datetime(latest_entry.published)
            except:
                pass

        # Get author
        author = latest_entry.get("author", None)

        # Prepare article data
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

        # Save to database
        db_client.table("articles").insert(article_data).execute()

        logger.info(f"✓ Saved: {len(full_content):,} characters")

        result["success"] = True
        result["articles_saved"] = 1
        result["latest_title"] = article_data["title"]
        result["content_length"] = len(full_content)

    except Exception as e:
        logger.error(f"✗ Error: {e}")
        result["error"] = str(e)

    finally:
        if extractor:
            extractor.close()

    return result


def main():
    """Main function."""
    import argparse
    from app.config.feed_config import FEED_SOURCES

    parser = argparse.ArgumentParser(
        description="Fetch latest article from each feed with FULL content extraction"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of feeds to process"
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Filter by specific domain"
    )

    args = parser.parse_args()

    try:
        # Get feeds from feed_config.py
        feeds = FEED_SOURCES

        # Apply filters
        if args.domain:
            feeds = [f for f in feeds if f.domain == args.domain]

        if args.limit:
            feeds = feeds[:args.limit]

        if not feeds:
            logger.warning("No feeds found")
            return

        logger.info(f"\n{'=' * 80}")
        logger.info(f"FETCHING LATEST FULL CONTENT FROM {len(feeds)} FEEDS")
        logger.info(f"Using domain-specific content extractors")
        logger.info(f"{'=' * 80}\n")

        successful = 0
        failed = 0
        skipped = 0
        total_saved = 0
        total_chars = 0

        for i, feed_source in enumerate(feeds, 1):
            feed_url = feed_source.url
            domain = feed_source.domain
            description = feed_source.description
            theme = feed_source.theme

            logger.info(f"\n{'─' * 80}")
            logger.info(f"[{i}/{len(feeds)}] {description}")
            logger.info(f"Domain: {domain}")

            result = fetch_latest_with_full_content(feed_url, domain, description, theme)

            if result["success"]:
                successful += 1
                total_saved += result["articles_saved"]
                total_chars += result.get("content_length", 0)
            elif result.get("error") and "skip" in result.get("error", "").lower():
                skipped += 1
            else:
                failed += 1

        # Summary
        avg_chars = total_chars / total_saved if total_saved > 0 else 0

        logger.info(f"\n{'=' * 80}")
        logger.info(f"SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total feeds processed: {len(feeds)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"New articles saved: {total_saved}")
        logger.info(f"Already existed: {successful - total_saved}")
        logger.info(f"Total content: {total_chars:,} characters")
        logger.info(f"Average per article: {avg_chars:,.0f} characters")
        logger.info(f"{'=' * 80}\n")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
