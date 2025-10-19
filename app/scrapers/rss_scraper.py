import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import time
from email.utils import parsedate_to_datetime
from app.utils.logger import get_logger
from app.database import get_db

logger = get_logger(__name__)


class RSScraper:
    """Scrape articles from RSS feeds."""

    def __init__(self):
        self.db_client = get_db()

    def parse_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Parse an RSS feed.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            Parsed feed object or None if error
        """
        try:
            logger.info(f"Parsing feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed has issues (bozo=True): {feed_url}")

            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return None

            logger.info(f"Found {len(feed.entries)} entries in {feed_url}")
            return feed

        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            return None

    def parse_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse various date formats from RSS feeds.

        Args:
            date_string: Date string from RSS feed

        Returns:
            datetime object or None
        """
        if not date_string:
            return None

        try:
            # Try parsing RFC 2822 format (common in RSS)
            return parsedate_to_datetime(date_string)
        except Exception:
            pass

        # Try ISO format
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except Exception:
            pass

        logger.warning(f"Could not parse date: {date_string}")
        return None

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
        published_date = None
        if hasattr(entry, "published"):
            published_date = self.parse_date(entry.published)
        elif hasattr(entry, "updated"):
            published_date = self.parse_date(entry.updated)

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
                logger.debug(f"Article already exists: {article_data['url']}")
                return False

            # Insert new article
            self.db_client.table("articles").insert(article_data).execute()
            logger.info(f"Saved new article: {article_data['title']}")
            return True

        except Exception as e:
            logger.error(f"Error saving article {article_data.get('url')}: {e}")
            return False

    def scrape_feed(self, feed_url: str, source_domain: str) -> int:
        """
        Scrape articles from a single feed.

        Args:
            feed_url: URL of the RSS feed
            source_domain: Domain of the source

        Returns:
            Number of new articles saved
        """
        feed = self.parse_feed(feed_url)
        if not feed:
            return 0

        saved_count = 0

        for entry in feed.entries:
            try:
                article_data = self.extract_article_data(entry, feed_url, source_domain)

                if not article_data["url"]:
                    logger.warning(f"Entry missing URL, skipping")
                    continue

                if self.save_article(article_data):
                    saved_count += 1

            except Exception as e:
                logger.error(f"Error processing entry: {e}")
                continue

        logger.info(f"Saved {saved_count} new articles from {feed_url}")
        return saved_count

    def update_feed_status(self, feed_url: str, status: str, error_message: Optional[str] = None):
        """
        Update feed status in database.

        Args:
            feed_url: URL of the feed
            status: New status (active/error)
            error_message: Error message if status is error
        """
        try:
            update_data = {
                "status": status,
                "last_fetched": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if error_message:
                update_data["error_message"] = error_message

            self.db_client.table("feeds").update(update_data).eq("url", feed_url).execute()
            logger.debug(f"Updated feed status: {feed_url} -> {status}")

        except Exception as e:
            logger.error(f"Error updating feed status for {feed_url}: {e}")

    def scrape_all_feeds(self) -> Dict[str, int]:
        """
        Scrape articles from all active feeds in the database.

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

            for feed in feeds:
                feed_url = feed["url"]
                domain = feed.get("domain", "")

                try:
                    articles_saved = self.scrape_feed(feed_url, domain)
                    total_articles += articles_saved
                    self.update_feed_status(feed_url, "active")

                except Exception as e:
                    logger.error(f"Failed to scrape feed {feed_url}: {e}")
                    self.update_feed_status(feed_url, "error", str(e))
                    failed_feeds += 1

                # Small delay to be polite
                time.sleep(1)

            return {
                "total_feeds": len(feeds),
                "total_articles": total_articles,
                "failed_feeds": failed_feeds
            }

        except Exception as e:
            logger.error(f"Error in scrape_all_feeds: {e}")
            return {"total_feeds": 0, "total_articles": 0, "failed_feeds": 0}
