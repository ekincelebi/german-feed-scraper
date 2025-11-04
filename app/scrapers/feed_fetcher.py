"""
Feed fetching module with strategy support and date filtering.

Handles different fetching strategies:
- full_archive: Fetch all available items (for beginners)
- daily_updates: Fetch only items from previous day (for advanced learners)
"""

import feedparser
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeedFetcher:
    """Fetch and filter RSS feed entries based on strategy."""

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
            dt = parsedate_to_datetime(date_string)
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        # Try ISO format
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        logger.warning(f"Could not parse date: {date_string}")
        return None

    def get_entry_date(self, entry) -> Optional[datetime]:
        """
        Extract published/updated date from feed entry.

        Args:
            entry: Feed entry object

        Returns:
            datetime object or None
        """
        # Try published date first
        if hasattr(entry, "published"):
            date = self.parse_date(entry.published)
            if date:
                return date

        # Try updated date
        if hasattr(entry, "updated"):
            date = self.parse_date(entry.updated)
            if date:
                return date

        # Try other date fields
        for field in ["pubDate", "date", "dc:date"]:
            if hasattr(entry, field):
                date = self.parse_date(getattr(entry, field))
                if date:
                    return date

        return None

    def is_from_previous_day(self, entry_date: datetime, reference_date: Optional[datetime] = None) -> bool:
        """
        Check if an entry is from the previous day relative to reference date.

        Args:
            entry_date: Date of the feed entry
            reference_date: Reference date to compare against (defaults to now)

        Returns:
            True if entry is from previous day, False otherwise
        """
        if not entry_date:
            return False

        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        # Ensure both dates are timezone-aware
        if entry_date.tzinfo is None:
            entry_date = entry_date.replace(tzinfo=timezone.utc)
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        # Calculate date boundaries for "previous day"
        # Previous day is from midnight yesterday to midnight today
        today_start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        return yesterday_start <= entry_date < today_start

    def is_from_last_24_hours(self, entry_date: datetime, reference_date: Optional[datetime] = None) -> bool:
        """
        Check if an entry is from the last 24 hours.

        Args:
            entry_date: Date of the feed entry
            reference_date: Reference date to compare against (defaults to now)

        Returns:
            True if entry is from last 24 hours, False otherwise
        """
        if not entry_date:
            return False

        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        # Ensure both dates are timezone-aware
        if entry_date.tzinfo is None:
            entry_date = entry_date.replace(tzinfo=timezone.utc)
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        # Check if within last 24 hours
        return (reference_date - entry_date) <= timedelta(hours=24)

    def fetch_feed(
        self,
        feed_url: str,
        strategy: str = "full_archive",
        use_24h_window: bool = False
    ) -> Optional[List]:
        """
        Fetch and filter feed entries based on strategy.

        Args:
            feed_url: URL of the RSS feed
            strategy: Fetch strategy ('full_archive' or 'daily_updates')
            use_24h_window: If True, use 24-hour window instead of previous day for daily_updates

        Returns:
            List of filtered feed entries or None if error
        """
        try:
            logger.info(f"Fetching feed: {feed_url} (strategy: {strategy})")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed has issues (bozo=True): {feed_url}")

            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return []

            all_entries = feed.entries
            logger.info(f"Found {len(all_entries)} total entries in {feed_url}")

            # If full archive strategy, return all entries
            if strategy == "full_archive":
                logger.info(f"Using full_archive strategy: returning all {len(all_entries)} entries")
                return all_entries

            # If daily_updates strategy, filter entries
            if strategy == "daily_updates":
                filtered_entries = []

                for entry in all_entries:
                    entry_date = self.get_entry_date(entry)

                    if entry_date is None:
                        # If no date available, include it (better to include than miss)
                        logger.debug(f"Entry has no date, including: {entry.get('title', 'Untitled')}")
                        filtered_entries.append(entry)
                        continue

                    # Check if entry matches time window
                    if use_24h_window:
                        if self.is_from_last_24_hours(entry_date):
                            filtered_entries.append(entry)
                    else:
                        if self.is_from_previous_day(entry_date):
                            filtered_entries.append(entry)

                logger.info(
                    f"Daily updates strategy: filtered {len(filtered_entries)}/{len(all_entries)} entries "
                    f"({'last 24h' if use_24h_window else 'previous day'})"
                )
                return filtered_entries

            # Unknown strategy, return all entries as fallback
            logger.warning(f"Unknown strategy '{strategy}', returning all entries")
            return all_entries

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return None

    def fetch_feed_full_archive(self, feed_url: str) -> Optional[List]:
        """
        Convenience method to fetch entire feed archive.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            List of all feed entries or None if error
        """
        return self.fetch_feed(feed_url, strategy="full_archive")

    def fetch_feed_daily_updates(self, feed_url: str, use_24h_window: bool = False) -> Optional[List]:
        """
        Convenience method to fetch only recent feed entries.

        Args:
            feed_url: URL of the RSS feed
            use_24h_window: If True, use 24-hour window instead of previous day

        Returns:
            List of recent feed entries or None if error
        """
        return self.fetch_feed(feed_url, strategy="daily_updates", use_24h_window=use_24h_window)
