#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhance German articles with educational annotations for B1-B2 learners.

This script adds vocabulary, grammar, and cultural annotations to cleaned articles
without modifying the original text. Supports parallel processing for speed.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from app.processors.learning_enhancer import LearningEnhancer
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main function to enhance articles with learning annotations."""
    parser = argparse.ArgumentParser(
        description="Enhance German articles with educational annotations for B1-B2 learners",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10 articles and $1 budget
  python scripts/enhance_for_learning.py --limit 10 --max-cost 1.0

  # Process 50 articles in parallel with 10 workers
  python scripts/enhance_for_learning.py --limit 50 --parallel --workers 10 --max-cost 5.0

  # Process all unenhanced articles with default budget
  python scripts/enhance_for_learning.py --parallel --workers 10

  # Fast processing with minimal rate limiting
  python scripts/enhance_for_learning.py --limit 100 --parallel --workers 10 --rate-limit 0.05

Cost Estimation (Groq Llama 3.3 70B):
  • Average cost per article: ~$0.003-0.005
  • 10 articles: ~$0.04
  • 100 articles: ~$0.40
  • Default budget: $5.00 (covers ~1,000-1,500 articles)

What it adds:
  • 10-15 B1-B2 vocabulary words with definitions
  • 3-5 grammar patterns with examples
  • 2-3 cultural context notes
  • 3-5 comprehension questions in German
  • Difficulty level (B1/B2/C1) and reading time estimate
        """
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of articles to enhance"
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
        default=0.1,
        help="Delay between API requests in seconds (default: 0.1)"
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
        help="Enable parallel processing (faster, recommended)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5, only used with --parallel)"
    )

    args = parser.parse_args()

    try:
        # Initialize learning enhancer
        logger.info("Initializing LearningEnhancer...")
        enhancer = LearningEnhancer(max_retries=args.max_retries)

        # Enhance articles
        if args.parallel:
            logger.info(
                f"Starting PARALLEL enhancement with {args.workers} workers, "
                f"budget ${args.max_cost:.2f}"
            )
            stats = enhancer.enhance_articles_parallel(
                limit=args.limit,
                max_cost_usd=args.max_cost,
                rate_limit_delay=args.rate_limit,
                max_workers=args.workers
            )
        else:
            logger.warning(
                "Sequential mode not yet implemented. "
                "Please use --parallel flag for parallel processing."
            )
            logger.info("Run with --parallel flag: --parallel --workers 10")
            sys.exit(1)

        # Display summary
        logger.info("\n" + "=" * 80)
        logger.info("ENHANCEMENT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total enhanced: {stats['total_processed']}")
        logger.info(f"Total failed: {stats['total_failed']}")
        logger.info(f"Total tokens: {stats['total_tokens']:,}")
        logger.info(f"Total cost: ${stats['total_cost_usd']:.4f}")
        logger.info(f"Average tokens/article: {stats['average_tokens_per_article']:.0f}")
        logger.info(f"Average cost/article: ${stats['average_cost_per_article']:.6f}")

        if stats['failed_article_ids']:
            logger.warning(f"\nFailed article IDs: {stats['failed_article_ids'][:10]}")
            if len(stats['failed_article_ids']) > 10:
                logger.warning(f"... and {len(stats['failed_article_ids']) - 10} more")

        logger.info("=" * 80 + "\n")

        # Next steps
        if stats['total_processed'] > 0:
            logger.info("✅ Articles enhanced successfully!")
            logger.info("\nEnhanced articles now have:")
            logger.info("  • Vocabulary annotations (B1-B2 words with definitions)")
            logger.info("  • Grammar pattern explanations")
            logger.info("  • Cultural context notes")
            logger.info("  • Comprehension questions in German")
            logger.info("  • Difficulty level and reading time estimates")
            logger.info("\nQuery the learning_enhancements table or article_learning_view to see results.")
        else:
            logger.info("ℹ️  No articles were enhanced.")
            logger.info("Possible reasons:")
            logger.info("  • All articles are already enhanced")
            logger.info("  • No cleaned articles available (run process_article_content.py first)")
            logger.info("  • Budget limit reached immediately")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("\nMake sure GROQ_API_KEY is set in your .env file")
        logger.info("Get your API key from: https://console.groq.com/keys")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
