#!/usr/bin/env python3
"""
Process articles to generate cleaned content for language learners.

This script uses the ContentProcessor to clean articles (no analysis required).
It removes ads, navigation, and irrelevant content while preserving the original language.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from app.processors.content_processor import ContentProcessor
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main function to process article content."""
    parser = argparse.ArgumentParser(
        description="Process articles to generate cleaned content for language learners"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of articles to process"
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=5.0,
        help="Maximum cost budget in USD (default: 5.0)"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        help="Delay between API requests in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retry attempts per article (default: 3)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing (faster)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5, only used with --parallel)"
    )

    args = parser.parse_args()

    try:
        # Initialize content processor
        logger.info("Initializing ContentProcessor...")
        processor = ContentProcessor(max_retries=args.max_retries)

        # Process articles (no analysis required)
        if args.parallel:
            logger.info(f"Starting PARALLEL content processing with {args.workers} workers, budget ${args.max_cost}")
            stats = processor.process_articles_parallel(
                limit=args.limit,
                max_cost_usd=args.max_cost,
                rate_limit_delay=args.rate_limit,
                max_workers=args.workers
            )
        else:
            logger.info(f"Starting sequential content processing with budget ${args.max_cost}")
            stats = processor.process_articles(
                limit=args.limit,
                max_cost_usd=args.max_cost,
                rate_limit_delay=args.rate_limit
            )

        # Display summary
        logger.info("\n" + "=" * 80)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total processed: {stats['total_processed']}")
        logger.info(f"Total failed: {stats['total_failed']}")
        logger.info(f"Total tokens: {stats['total_tokens']:,}")
        logger.info(f"Total cost: ${stats['total_cost_usd']:.4f}")
        logger.info(f"Average tokens/article: {stats['average_tokens_per_article']}")
        logger.info(f"Average cost/article: ${stats['average_cost_per_article']:.6f}")

        if stats['failed_article_ids']:
            logger.warning(f"\nFailed article IDs: {stats['failed_article_ids']}")

        logger.info("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
