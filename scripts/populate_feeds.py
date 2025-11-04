#!/usr/bin/env python3
"""
Script to populate feeds table from configuration.

Loads feed sources from config and inserts/updates them in the database.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.config.feed_config import FEED_SOURCES
from app.database import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def populate_feeds(update_existing: bool = False):
    """
    Populate feeds table from configuration.

    Args:
        update_existing: If True, update existing feeds with new metadata
    """
    db_client = get_db()

    logger.info(f"Populating feeds from configuration...")
    logger.info(f"Total feed sources: {len(FEED_SOURCES)}")

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    for feed_source in FEED_SOURCES:
        try:
            # Check if feed already exists
            existing = db_client.table("feeds").select("id").eq("url", feed_source.url).execute()

            feed_data = {
                "url": feed_source.url,
                "domain": feed_source.domain,
                "category": feed_source.category,
                "theme": feed_source.theme,
                "strategy": feed_source.strategy,
                "description": feed_source.description,
                "priority": feed_source.priority,
                "status": "active",
                "updated_at": datetime.utcnow().isoformat()
            }

            if existing.data:
                if update_existing:
                    # Update existing feed
                    db_client.table("feeds").update(feed_data).eq("url", feed_source.url).execute()
                    logger.info(f"Updated: {feed_source.description}")
                    updated_count += 1
                else:
                    logger.debug(f"Skipped (already exists): {feed_source.description}")
                    skipped_count += 1
            else:
                # Insert new feed
                feed_data["created_at"] = datetime.utcnow().isoformat()
                db_client.table("feeds").insert(feed_data).execute()
                logger.info(f"Inserted: {feed_source.description}")
                inserted_count += 1

        except Exception as e:
            logger.error(f"Error processing feed {feed_source.url}: {e}")
            continue

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Feed population complete!")
    logger.info(f"Inserted: {inserted_count}")
    logger.info(f"Updated: {updated_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Total: {inserted_count + updated_count + skipped_count}")
    logger.info(f"{'=' * 60}")


def show_feed_statistics():
    """Show statistics about configured feeds."""
    from collections import defaultdict

    logger.info(f"\n{'=' * 60}")
    logger.info(f"FEED CONFIGURATION STATISTICS")
    logger.info(f"{'=' * 60}")

    # Count by strategy
    by_strategy = defaultdict(int)
    for feed in FEED_SOURCES:
        by_strategy[feed.strategy] += 1

    logger.info(f"\nBy Strategy:")
    for strategy, count in sorted(by_strategy.items()):
        logger.info(f"  {strategy}: {count} feeds")

    # Count by domain
    by_domain = defaultdict(int)
    for feed in FEED_SOURCES:
        by_domain[feed.domain] += 1

    logger.info(f"\nBy Domain:")
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {domain}: {count} feeds")

    # Count by category
    by_category = defaultdict(int)
    for feed in FEED_SOURCES:
        by_category[feed.category] += 1

    logger.info(f"\nBy Category:")
    for category, count in sorted(by_category.items()):
        logger.info(f"  {category}: {count} feeds")

    # Count by priority
    by_priority = defaultdict(int)
    for feed in FEED_SOURCES:
        by_priority[feed.priority] += 1

    logger.info(f"\nBy Priority:")
    for priority, count in sorted(by_priority.items()):
        priority_label = {1: "High", 2: "Medium", 3: "Low"}.get(priority, "Unknown")
        logger.info(f"  {priority} ({priority_label}): {count} feeds")

    logger.info(f"\nTotal Feeds: {len(FEED_SOURCES)}")
    logger.info(f"{'=' * 60}\n")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Populate feeds table from configuration")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing feeds with new metadata"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show feed statistics without populating"
    )

    args = parser.parse_args()

    try:
        if args.stats:
            show_feed_statistics()
        else:
            show_feed_statistics()
            populate_feeds(update_existing=args.update)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
