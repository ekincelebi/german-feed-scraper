#!/usr/bin/env python3
"""
Script to scrape full article content from RSS feeds using BeautifulSoup.
This visits each article URL and extracts the complete content from the webpage.
"""

import sys
from pathlib import Path
import time

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

    def __init__(self):
        self.db_client = get_db()
        self.http_client = httpx.Client(timeout=30.0, follow_redirects=True)

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

    def scrape_feed_with_full_content(self, feed_url: str, source_domain: str) -> int:
        """
        Scrape articles from a feed and extract full content from each article URL.

        Args:
            feed_url: URL of the RSS feed
            source_domain: Domain of the source

        Returns:
            Number of new articles saved
        """
        try:
            logger.info(f"Processing feed: {feed_url}")

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

            logger.info(f"  Saved {saved_count} new articles from {feed_url}")
            return saved_count

        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {e}")
            return 0

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

    def scrape_all_feeds(self) -> dict:
        """
        Scrape all active feeds with full content extraction.

        Returns:
            Dictionary with statistics
        """
        try:
            # Get all active feeds
            response = self.db_client.table("feeds").select("*").eq("status", "active").execute()
            feeds = response.data

            if not feeds:
                logger.warning("No active feeds found in database")
                return {"total_feeds": 0, "total_articles": 0, "failed_feeds": 0}

            logger.info(f"Found {len(feeds)} active feeds to scrape")

            total_articles = 0
            failed_feeds = 0

            for i, feed in enumerate(feeds, 1):
                feed_url = feed["url"]
                domain = feed.get("domain", "")

                logger.info(f"\n[{i}/{len(feeds)}] Processing feed from {domain}")

                try:
                    articles_saved = self.scrape_feed_with_full_content(feed_url, domain)
                    total_articles += articles_saved
                    self.update_feed_status(feed_url, "active")

                except Exception as e:
                    logger.error(f"Failed to scrape feed {feed_url}: {e}")
                    self.update_feed_status(feed_url, "error", str(e))
                    failed_feeds += 1

                # Delay between feeds
                time.sleep(2)

            return {
                "total_feeds": len(feeds),
                "total_articles": total_articles,
                "failed_feeds": failed_feeds
            }

        except Exception as e:
            logger.error(f"Error in scrape_all_feeds: {e}")
            return {"total_feeds": 0, "total_articles": 0, "failed_feeds": 0}

    def close(self):
        """Close HTTP client."""
        self.http_client.close()


def main():
    """Scrape articles with full content from all active feeds."""
    logger.info("Starting full content scraping process...")
    logger.info("This will visit each article URL and extract complete content\n")

    scraper = FullContentScraper()

    try:
        stats = scraper.scrape_all_feeds()

        separator = "=" * 60
        logger.info(f"\n{separator}")
        logger.info("Full content scraping complete!")
        logger.info(f"Total feeds processed: {stats['total_feeds']}")
        logger.info(f"Total new articles saved: {stats['total_articles']}")
        logger.info(f"Failed feeds: {stats['failed_feeds']}")
        logger.info(separator)

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
