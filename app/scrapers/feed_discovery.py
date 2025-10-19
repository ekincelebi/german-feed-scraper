import httpx
from typing import List, Dict, Any
from urllib.parse import urlparse
from app.utils.logger import get_logger
from app.database import get_db
from app.models.article import Feed
from datetime import datetime

logger = get_logger(__name__)


class FeedDiscovery:
    """Discover RSS feeds using feedsearch.dev API."""

    FEEDSEARCH_API_URL = "https://feedsearch.dev/api/v1/search"

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    async def discover_feeds_async(self, url: str) -> List[Dict[str, Any]]:
        """
        Discover RSS feeds from a URL using feedsearch.dev API.

        Args:
            url: Website URL to search for feeds

        Returns:
            List of discovered feed dictionaries
        """
        try:
            logger.info(f"Discovering feeds for: {url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.FEEDSEARCH_API_URL,
                    params={"url": url}
                )
                response.raise_for_status()

                feeds = response.json()
                logger.info(f"Found {len(feeds)} feeds for {url}")
                return feeds

        except httpx.HTTPError as e:
            logger.error(f"HTTP error discovering feeds for {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error discovering feeds for {url}: {e}")
            return []

    def discover_feeds(self, url: str) -> List[Dict[str, Any]]:
        """
        Synchronous version: Discover RSS feeds from a URL.

        Args:
            url: Website URL to search for feeds

        Returns:
            List of discovered feed dictionaries
        """
        try:
            logger.info(f"Discovering feeds for: {url}")
            response = self.client.get(
                self.FEEDSEARCH_API_URL,
                params={"url": url}
            )
            response.raise_for_status()

            feeds = response.json()
            logger.info(f"Found {len(feeds)} feeds for {url}")
            return feeds

        except httpx.HTTPError as e:
            logger.error(f"HTTP error discovering feeds for {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error discovering feeds for {url}: {e}")
            return []

    def save_feeds_to_db(self, feeds: List[Dict[str, Any]], source_url: str) -> int:
        """
        Save discovered feeds to Supabase database.

        Args:
            feeds: List of feed dictionaries from feedsearch.dev
            source_url: Original URL that was searched

        Returns:
            Number of feeds saved
        """
        if not feeds:
            logger.warning(f"No feeds to save for {source_url}")
            return 0

        db_client = get_db()
        saved_count = 0

        for feed_data in feeds:
            try:
                feed_url = feed_data.get("url")
                if not feed_url:
                    continue

                # Extract domain from source URL
                domain = urlparse(source_url).netloc

                # Check if feed already exists
                existing = db_client.table("feeds").select("id").eq("url", feed_url).execute()

                if existing.data:
                    logger.info(f"Feed already exists: {feed_url}")
                    continue

                # Create feed object
                feed = {
                    "url": feed_url,
                    "domain": domain,
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                # Insert into database
                db_client.table("feeds").insert(feed).execute()
                logger.info(f"Saved feed: {feed_url}")
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving feed {feed_data.get('url')}: {e}")
                continue

        logger.info(f"Saved {saved_count} new feeds from {source_url}")
        return saved_count

    def discover_and_save(self, url: str) -> int:
        """
        Discover feeds from a URL and save them to the database.

        Args:
            url: Website URL to search for feeds

        Returns:
            Number of feeds saved
        """
        feeds = self.discover_feeds(url)
        return self.save_feeds_to_db(feeds, url)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
