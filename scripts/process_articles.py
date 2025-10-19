#!/usr/bin/env python3
"""
Script to process articles with AI for language learning features.
Uses Groq API with Llama 3.1 70B model.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.processors.ai_processor import ArticleProcessor
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Process articles with AI analysis."""
    parser = argparse.ArgumentParser(
        description='Process articles with AI for language learning features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10 articles
  python scripts/process_articles.py --limit 10

  # Process 100 articles (recommended for testing)
  python scripts/process_articles.py --limit 100

  # Process all articles with default $5 budget
  python scripts/process_articles.py

  # Process with custom budget
  python scripts/process_articles.py --max-cost 2.50

  # Process with faster rate (less polite to API)
  python scripts/process_articles.py --rate-limit 0.2

Cost Estimation (Groq Llama 3.1 70B):
  - Average cost per article: ~$0.0006
  - 100 articles: ~$0.06
  - 1,444 articles: ~$0.91
  - Default budget: $5.00 (covers all articles with margin)
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        help='Limit processing to N articles (for testing)'
    )
    parser.add_argument(
        '--max-cost',
        type=float,
        default=5.0,
        metavar='USD',
        help='Maximum cost budget in USD (default: 5.0)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.5,
        metavar='SECONDS',
        help='Delay between API requests in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        metavar='N',
        help='Maximum retry attempts for failed requests (default: 3)'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=2,
        metavar='SECONDS',
        help='Delay between retry attempts in seconds (default: 2)'
    )

    args = parser.parse_args()

    # Print configuration
    print("=" * 80)
    print("AI ARTICLE PROCESSOR FOR LANGUAGE LEARNING")
    print("=" * 80)
    print(f"Model: Llama 3.1 70B (via Groq)")
    print(f"Budget: ${args.max_cost:.2f} USD")
    print(f"Rate limit: {args.rate_limit}s between requests")
    print(f"Max retries: {args.max_retries}")
    if args.limit:
        print(f"Limit: {args.limit} articles (testing mode)")
    else:
        print(f"Limit: None (process all unanalyzed articles)")
    print("=" * 80)
    print()

    # Warning for budget
    if args.limit and args.limit > 100 and args.max_cost < 0.10:
        logger.warning(f"Budget ${args.max_cost:.2f} may be insufficient for {args.limit} articles")
        print(f"⚠️  Warning: Budget ${args.max_cost:.2f} may only cover ~{int(args.max_cost / 0.0006)} articles")
        print()

    # Initialize processor
    try:
        processor = ArticleProcessor(
            max_retries=args.max_retries,
            retry_delay=args.retry_delay
        )
    except ValueError as e:
        logger.error(f"Failed to initialize processor: {e}")
        print(f"❌ Error: {e}")
        print("\nMake sure GROQ_API_KEY is set in your .env file")
        print("Get your API key from: https://console.groq.com/keys")
        return 1

    # Process articles
    try:
        stats = processor.process_batch(
            limit=args.limit,
            max_cost_usd=args.max_cost,
            rate_limit_delay=args.rate_limit
        )

        # Print final statistics
        print()
        print("=" * 80)
        print("PROCESSING COMPLETE!")
        print("=" * 80)
        print(f"✓ Successfully processed: {stats['total_processed']}")
        print(f"✗ Failed: {stats['total_failed']}")
        if stats['failed_article_ids']:
            print(f"  Failed article IDs: {stats['failed_article_ids'][:10]}{'...' if len(stats['failed_article_ids']) > 10 else ''}")
        print()
        print(f"📊 Statistics:")
        print(f"  Total tokens: {stats['total_tokens']:,}")
        print(f"  Avg tokens/article: {stats['average_tokens_per_article']:,.0f}")
        print()
        print(f"💰 Cost:")
        print(f"  Total: ${stats['total_cost_usd']:.4f}")
        print(f"  Avg/article: ${stats['average_cost_per_article']:.6f}")
        print(f"  Remaining budget: ${args.max_cost - stats['total_cost_usd']:.4f}")
        print("=" * 80)

        # Check article_analysis table
        print()
        print("To view processed articles, run:")
        print("  python scripts/show_stats.py --articles-only")
        print()
        print("Or query the article_analysis table in Supabase")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        stats = processor.get_statistics()
        print(f"Processed {stats['total_processed']} articles before interruption")
        print(f"Total cost: ${stats['total_cost_usd']:.4f}")
        return 1
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
