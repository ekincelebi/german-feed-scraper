"""
Statistics and analytics for scraped articles and feeds.
"""

from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime, timedelta
from app.database import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseStatistics:
    """Generate statistics and reports for scraped data."""

    def __init__(self):
        self.db_client = get_db()

    def get_feed_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive feed statistics.

        Returns:
            Dictionary with feed statistics
        """
        try:
            # Get all feeds
            feeds = self.db_client.table("feeds").select("*").execute()

            # Count by status
            status_counts = Counter(feed.get('status', 'unknown') for feed in feeds.data)

            # Count by domain
            domain_counts = Counter(feed.get('domain', 'unknown') for feed in feeds.data)

            return {
                'total_feeds': len(feeds.data),
                'by_status': dict(status_counts),
                'by_domain': dict(domain_counts),
                'unique_domains': len(domain_counts),
                'feeds': feeds.data
            }

        except Exception as e:
            logger.error(f"Error getting feed statistics: {e}")
            return {}

    def get_article_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive article statistics.

        Returns:
            Dictionary with article statistics
        """
        try:
            # Get total count
            total = self.db_client.table("articles").select("*", count='exact').execute()

            # Get all articles for detailed analysis
            articles = self.db_client.table("articles").select(
                "source_domain, content, title, created_at, published_date"
            ).execute()

            if not articles.data:
                return {'total_articles': 0}

            # Count by domain
            domain_counts = Counter(
                article.get('source_domain', 'Unknown')
                for article in articles.data
            )

            # Content length statistics
            content_lengths = [
                len(article.get('content', ''))
                for article in articles.data
                if article.get('content')
            ]

            # Date statistics
            created_dates = [
                article.get('created_at')
                for article in articles.data
                if article.get('created_at')
            ]

            stats = {
                'total_articles': total.count,
                'by_domain': dict(domain_counts),
                'unique_domains': len(domain_counts),
            }

            # Content statistics
            if content_lengths:
                stats['content'] = {
                    'average_length': sum(content_lengths) / len(content_lengths),
                    'min_length': min(content_lengths),
                    'max_length': max(content_lengths),
                    'total_characters': sum(content_lengths),
                    'substantial_articles': len([l for l in content_lengths if l > 500]),
                    'substantial_percentage': len([l for l in content_lengths if l > 500]) / len(content_lengths) * 100
                }

            # Date statistics
            if created_dates:
                sorted_dates = sorted(created_dates)
                stats['dates'] = {
                    'earliest': sorted_dates[0],
                    'latest': sorted_dates[-1],
                }

            return stats

        except Exception as e:
            logger.error(f"Error getting article statistics: {e}")
            return {}

    def get_domain_breakdown(self) -> List[Dict[str, Any]]:
        """
        Get detailed breakdown by domain.

        Returns:
            List of domain statistics
        """
        try:
            articles = self.db_client.table("articles").select(
                "source_domain, content"
            ).execute()

            if not articles.data:
                return []

            # Group by domain
            domain_data = {}
            for article in articles.data:
                domain = article.get('source_domain', 'Unknown')
                if domain not in domain_data:
                    domain_data[domain] = {
                        'domain': domain,
                        'count': 0,
                        'total_characters': 0,
                        'content_lengths': []
                    }

                domain_data[domain]['count'] += 1
                content_length = len(article.get('content', ''))
                domain_data[domain]['total_characters'] += content_length
                domain_data[domain]['content_lengths'].append(content_length)

            # Calculate averages and sort
            breakdown = []
            for domain, data in domain_data.items():
                lengths = data['content_lengths']
                breakdown.append({
                    'domain': domain,
                    'article_count': data['count'],
                    'total_characters': data['total_characters'],
                    'average_length': data['total_characters'] / data['count'] if data['count'] > 0 else 0,
                    'min_length': min(lengths) if lengths else 0,
                    'max_length': max(lengths) if lengths else 0,
                })

            # Sort by article count descending
            breakdown.sort(key=lambda x: x['article_count'], reverse=True)

            return breakdown

        except Exception as e:
            logger.error(f"Error getting domain breakdown: {e}")
            return []

    def get_recent_articles(self, limit: int = 10, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent articles.

        Args:
            limit: Number of articles to return
            domain: Optional domain filter

        Returns:
            List of recent articles
        """
        try:
            query = self.db_client.table("articles").select(
                "title, source_domain, content, created_at, url"
            ).order("created_at", desc=True).limit(limit)

            if domain:
                query = query.eq("source_domain", domain)

            result = query.execute()

            return [{
                'title': article.get('title', 'Untitled'),
                'domain': article.get('source_domain', 'Unknown'),
                'content_length': len(article.get('content', '')),
                'created_at': article.get('created_at', ''),
                'url': article.get('url', '')
            } for article in result.data]

        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []

    def get_scraping_summary(self) -> Dict[str, Any]:
        """
        Get complete scraping summary.

        Returns:
            Dictionary with complete summary
        """
        feed_stats = self.get_feed_statistics()
        article_stats = self.get_article_statistics()
        domain_breakdown = self.get_domain_breakdown()

        return {
            'feeds': feed_stats,
            'articles': article_stats,
            'domain_breakdown': domain_breakdown,
            'generated_at': datetime.utcnow().isoformat()
        }

    def print_summary_report(self):
        """Print a formatted summary report to console."""
        print("=" * 80)
        print("DATABASE STATISTICS REPORT")
        print("=" * 80)

        # Feed Statistics
        feed_stats = self.get_feed_statistics()
        print(f"\n📡 FEEDS")
        print("-" * 80)
        print(f"Total Feeds: {feed_stats.get('total_feeds', 0):,}")
        print(f"Unique Domains: {feed_stats.get('unique_domains', 0)}")

        if feed_stats.get('by_status'):
            print("\nBy Status:")
            for status, count in sorted(feed_stats['by_status'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count:,}")

        # Article Statistics
        article_stats = self.get_article_statistics()
        print(f"\n📰 ARTICLES")
        print("-" * 80)
        print(f"Total Articles: {article_stats.get('total_articles', 0):,}")
        print(f"Unique Domains: {article_stats.get('unique_domains', 0)}")

        if article_stats.get('content'):
            content = article_stats['content']
            print(f"\n📝 Content Statistics:")
            print(f"  Average Length: {content['average_length']:,.0f} characters")
            print(f"  Shortest Article: {content['min_length']:,} characters")
            print(f"  Longest Article: {content['max_length']:,} characters")
            print(f"  Total Content: {content['total_characters']:,} characters")
            print(f"  Substantial (>500 chars): {content['substantial_articles']:,} ({content['substantial_percentage']:.1f}%)")

        # Domain Breakdown
        breakdown = self.get_domain_breakdown()
        if breakdown:
            print(f"\n📊 DOMAIN BREAKDOWN")
            print("-" * 80)
            total_articles = article_stats.get('total_articles', 0)

            for item in breakdown:
                domain = item['domain']
                count = item['article_count']
                percentage = (count / total_articles * 100) if total_articles > 0 else 0
                avg_length = item['average_length']
                bar = "█" * int(percentage / 2)
                print(f"{domain:30s} {count:6,} ({percentage:5.1f}%) {bar}")
                print(f"{'':30s} Avg: {avg_length:,.0f} chars")

        # Recent Articles
        recent = self.get_recent_articles(limit=5)
        if recent:
            print(f"\n🕐 RECENT ARTICLES (Last 5)")
            print("-" * 80)
            for i, article in enumerate(recent, 1):
                title = article['title'][:60]
                domain = article['domain']
                content_len = article['content_length']
                print(f"{i}. [{domain:20s}] {title}...")
                print(f"   {content_len:,} characters")

        print("\n" + "=" * 80)

    def export_to_json(self, filepath: str):
        """
        Export statistics to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        import json

        summary = self.get_scraping_summary()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Statistics exported to {filepath}")

    def export_to_csv(self, filepath: str):
        """
        Export domain breakdown to CSV file.

        Args:
            filepath: Path to output CSV file
        """
        import csv

        breakdown = self.get_domain_breakdown()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if breakdown:
                writer = csv.DictWriter(f, fieldnames=breakdown[0].keys())
                writer.writeheader()
                writer.writerows(breakdown)

        logger.info(f"Domain breakdown exported to {filepath}")
