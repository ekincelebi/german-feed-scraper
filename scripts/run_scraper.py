#!/usr/bin/env python3
"""
Script to scrape articles from all discovered RSS feeds.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers.rss_scraper import RSScraper
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Scrape articles from all active feeds."""
    logger.info("Starting RSS scraping process...")

    scraper = RSScraper()

    try:
        stats = scraper.scrape_all_feeds()

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Scraping complete!")
        logger.info(f"Total feeds processed: {stats['total_feeds']}")
        logger.info(f"Total new articles saved: {stats['total_articles']}")
        logger.info(f"Failed feeds: {stats['failed_feeds']}")
        logger.info(f"{'=' * 60}")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
