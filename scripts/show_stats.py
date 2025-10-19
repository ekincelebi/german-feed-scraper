#!/usr/bin/env python3
"""
Script to display database statistics and analytics.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.analytics.statistics import DatabaseStatistics
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Display database statistics."""
    parser = argparse.ArgumentParser(
        description='Display statistics for scraped articles and feeds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show complete statistics report
  python scripts/show_stats.py

  # Show recent articles from specific domain
  python scripts/show_stats.py --recent 10 --domain www.spiegel.de

  # Export statistics to JSON
  python scripts/show_stats.py --export-json stats.json

  # Export domain breakdown to CSV
  python scripts/show_stats.py --export-csv domains.csv
        """
    )

    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Show N most recent articles'
    )
    parser.add_argument(
        '--domain',
        type=str,
        help='Filter by specific domain'
    )
    parser.add_argument(
        '--export-json',
        type=str,
        metavar='FILE',
        help='Export statistics to JSON file'
    )
    parser.add_argument(
        '--export-csv',
        type=str,
        metavar='FILE',
        help='Export domain breakdown to CSV file'
    )
    parser.add_argument(
        '--feeds-only',
        action='store_true',
        help='Show only feed statistics'
    )
    parser.add_argument(
        '--articles-only',
        action='store_true',
        help='Show only article statistics'
    )

    args = parser.parse_args()

    stats = DatabaseStatistics()

    # Export options
    if args.export_json:
        logger.info(f"Exporting statistics to {args.export_json}")
        stats.export_to_json(args.export_json)
        print(f"✓ Statistics exported to {args.export_json}")
        return

    if args.export_csv:
        logger.info(f"Exporting domain breakdown to {args.export_csv}")
        stats.export_to_csv(args.export_csv)
        print(f"✓ Domain breakdown exported to {args.export_csv}")
        return

    # Show recent articles
    if args.recent:
        print("=" * 80)
        print(f"RECENT ARTICLES" + (f" FROM {args.domain}" if args.domain else ""))
        print("=" * 80)

        articles = stats.get_recent_articles(limit=args.recent, domain=args.domain)

        if not articles:
            print("No articles found.")
            return

        for i, article in enumerate(articles, 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Domain: {article['domain']}")
            print(f"   Length: {article['content_length']:,} characters")
            print(f"   Date: {article['created_at']}")
            print(f"   URL: {article['url']}")

        print("\n" + "=" * 80)
        return

    # Show specific statistics
    if args.feeds_only:
        print("=" * 80)
        print("FEED STATISTICS")
        print("=" * 80)

        feed_stats = stats.get_feed_statistics()

        print(f"\nTotal Feeds: {feed_stats.get('total_feeds', 0):,}")
        print(f"Unique Domains: {feed_stats.get('unique_domains', 0)}")

        if feed_stats.get('by_status'):
            print("\nBy Status:")
            for status, count in sorted(feed_stats['by_status'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count:,}")

        if feed_stats.get('by_domain'):
            print("\nBy Domain:")
            for domain, count in sorted(feed_stats['by_domain'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {domain}: {count:,} feeds")

        print("\n" + "=" * 80)
        return

    if args.articles_only:
        print("=" * 80)
        print("ARTICLE STATISTICS")
        print("=" * 80)

        article_stats = stats.get_article_statistics()

        print(f"\nTotal Articles: {article_stats.get('total_articles', 0):,}")
        print(f"Unique Domains: {article_stats.get('unique_domains', 0)}")

        if article_stats.get('content'):
            content = article_stats['content']
            print(f"\nContent Statistics:")
            print(f"  Average Length: {content['average_length']:,.0f} characters")
            print(f"  Total Content: {content['total_characters']:,} characters")
            print(f"  Substantial (>500 chars): {content['substantial_articles']:,} ({content['substantial_percentage']:.1f}%)")

        print("\n" + "=" * 80)
        return

    # Default: show complete report
    stats.print_summary_report()


if __name__ == "__main__":
    main()
