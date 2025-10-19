#!/usr/bin/env python3
"""
Script to discover RSS feeds from target websites and save them to the database.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers.feed_discovery import FeedDiscovery
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Target websites for RSS discovery
TARGET_WEBSITES = [
    "https://www.nachrichtenleicht.de",
    "https://rss.dw.com",
    "https://www.geo.de",
    "https://rss.sueddeutsche.de",
    "https://www.tagesschau.de",
    "https://newsfeed.zeit.de",
    "https://www.spiegel.de",
    "https://www.apotheken-umschau.de",
    "https://www.chefkoch.de",
    "https://www.brigitte.de",
    "https://www.heise.de",
    "https://t3n.de",
    "https://www.sport1.de/rss",
]


def main():
    """Discover feeds from all target websites."""
    logger.info("Starting feed discovery process...")

    total_feeds_saved = 0

    with FeedDiscovery() as discovery:
        for website in TARGET_WEBSITES:
            try:
                separator = "=" * 60
                logger.info(f"\n{separator}")
                logger.info(f"Processing: {website}")
                logger.info(separator)

                feeds_saved = discovery.discover_and_save(website)
                total_feeds_saved += feeds_saved

                logger.info(f"Saved {feeds_saved} feeds from {website}")

            except Exception as e:
                logger.error(f"Error processing {website}: {e}")
                continue

    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info("Feed discovery complete!")
    logger.info(f"Total feeds saved: {total_feeds_saved}")
    logger.info(separator)


if __name__ == "__main__":
    main()
