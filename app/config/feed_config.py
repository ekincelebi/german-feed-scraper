"""
Feed configuration and strategy definitions.

This module defines all RSS feeds to scrape and their fetching strategies.
"""

from typing import List, Dict, Literal
from dataclasses import dataclass

FetchStrategy = Literal["full_archive", "daily_updates"]


@dataclass
class FeedSource:
    """Configuration for a single RSS feed source."""

    url: str
    domain: str
    category: str
    theme: str
    strategy: FetchStrategy
    description: str
    priority: int = 2  # 1=High, 2=Medium, 3=Low


# Define all feed sources based on feed_fetching_strategies.txt
FEED_SOURCES: List[FeedSource] = [
    # ========================================================================
    # GERMAN LEARNING FEEDS (DW - Deutsche Welle)
    # ========================================================================

    # Vocabulary & Idioms (Beginner)
    # FeedSource(
    #     url="https://rss.dw.com/xml/DKpodcast_wortderwoche_de",
    #     domain="rss.dw.com",
    #     category="learning",
    #     theme="vocabulary",
    #     strategy="daily_updates",  # Fetch weekly - always get latest
    #     description="Wort der Woche - Word of the Week",
    #     priority=1
    # ),
    FeedSource(
        url="https://rss.dw.com/xml/DKpodcast_dassagtmanso_de",
        domain="rss.dw.com",
        category="learning",
        theme="idioms",
        strategy="full_archive",  # Fetch complete archive once
        description="Das sagt man so! - German idioms",
        priority=1
    ),

    # Audio Learning with Transcripts (Intermediate)
    # FeedSource(
    #     url="https://rss.dw.com/xml/DKpodcast_alltagsdeutsch_de",
    #     domain="rss.dw.com",
    #     category="learning",
    #     theme="audio_transcripts",
    #     strategy="full_archive",  # Extract manuscript text
    #     description="Alltagsdeutsch - Everyday German with transcripts",
    #     priority=1
    # ),
    # FeedSource(
    #     url="https://rss.dw.com/xml/DKpodcast_topthemamitvokabeln_de",
    #     domain="rss.dw.com",
    #     category="learning",
    #     theme="audio_transcripts",
    #     strategy="full_archive",  # Extract manuscript with vocabulary lists
    #     description="Top-Thema mit Vokabeln - Top topics with vocabulary",
    #     priority=1
    # ),

    # ========================================================================
    # SIMPLIFIED NEWS (Beginner Level)
    # ========================================================================

    # FeedSource(
    #     url="https://www.nachrichtenleicht.de/nachrichtenleicht-nachrichten-100.rss",
    #     domain="www.nachrichtenleicht.de",
    #     category="news_simple",
    #     theme="general_news",
    #     strategy="daily_updates",  # Only previous day items
    #     description="Nachrichtenleicht - Easy German news",
    #     priority=1
    # ),
    # FeedSource(
    #     url="https://www.nachrichtenleicht.de/nachrichtenleicht-sport-100.rss",
    #     domain="www.nachrichtenleicht.de",
    #     category="news_simple",
    #     theme="sports",
    #     strategy="daily_updates",  # Only previous day items
    #     description="Nachrichtenleicht Sport - Easy German sports news",
    #     priority=1
    # ),

    # ========================================================================
    # MAINSTREAM NEWS (Intermediate to Advanced)
    # ========================================================================

    # General News
    FeedSource(
        url="https://www.tagesschau.de/xml/rss2/",
        domain="www.tagesschau.de",
        category="news_mainstream",
        theme="general_news",
        strategy="daily_updates",
        description="Tagesschau - Main German news",
        priority=2
    ),
    FeedSource(
        url="https://rss.dw.com/xml/rss-de-all",
        domain="rss.dw.com",
        category="news_mainstream",
        theme="international_news",
        strategy="daily_updates",
        description="Deutsche Welle - International news",
        priority=2
    ),

    # Süddeutsche Zeitung
    # FeedSource(
    #     url="https://rss.sueddeutsche.de/rss/Politik",
    #     domain="rss.sueddeutsche.de",
    #     category="news_mainstream",
    #     theme="politics",
    #     strategy="daily_updates",
    #     description="Süddeutsche Zeitung - Politics",
    #     priority=2
    # ),
    FeedSource(
        url="https://rss.sueddeutsche.de/rss/Wirtschaft",
        domain="rss.sueddeutsche.de",
        category="news_mainstream",
        theme="business",
        strategy="daily_updates",
        description="Süddeutsche Zeitung - Business",
        priority=2
    ),
    FeedSource(
        url="https://rss.sueddeutsche.de/rss/Kultur",
        domain="rss.sueddeutsche.de",
        category="news_mainstream",
        theme="culture",
        strategy="daily_updates",
        description="Süddeutsche Zeitung - Culture",
        priority=2
    ),
    # FeedSource(
    #     url="https://rss.sueddeutsche.de/rss/Reise",
    #     domain="rss.sueddeutsche.de",
    #     category="news_mainstream",
    #     theme="travel",
    #     strategy="daily_updates",
    #     description="Süddeutsche Zeitung - Travel",
    #     priority=2
    # ),
    FeedSource(
        url="https://rss.sueddeutsche.de/rss/Gesundheit",
        domain="rss.sueddeutsche.de",
        category="news_mainstream",
        theme="health",
        strategy="daily_updates",
        description="Süddeutsche Zeitung - Health",
        priority=2
    ),

    # Der Spiegel
    FeedSource(
        url="https://www.spiegel.de/kultur/index.rss",
        domain="www.spiegel.de",
        category="news_mainstream",
        theme="culture",
        strategy="daily_updates",
        description="Der Spiegel - Culture",
        priority=2
    ),
    # FeedSource(
    #     url="https://www.spiegel.de/gesundheit/index.rss",
    #     domain="www.spiegel.de",
    #     category="news_mainstream",
    #     theme="health",
    #     strategy="daily_updates",
    #     description="Der Spiegel - Health",
    #     priority=2
    # ),
    # FeedSource(
    #     url="https://www.spiegel.de/familie/index.rss",
    #     domain="www.spiegel.de",
    #     category="news_mainstream",
    #     theme="family",
    #     strategy="daily_updates",
    #     description="Der Spiegel - Family",
    #     priority=2
    # ),

    # ========================================================================
    # LIFESTYLE & PRACTICAL GERMAN
    # ========================================================================

    # Recipes & Cooking
    FeedSource(
        url="https://www.chefkoch.de/recipe-of-the-day/rss",
        domain="www.chefkoch.de",
        category="lifestyle",
        theme="recipes",
        strategy="full_archive",  # Fetch entire archive once
        description="Chefkoch - Recipe of the day",
        priority=2
    ),
    FeedSource(
        url="https://www.brigitte.de/rezepte/feed.rss",
        domain="www.brigitte.de",
        category="lifestyle",
        theme="recipes",
        strategy="daily_updates",  # Previous day items
        description="BRIGITTE - Recipes",
        priority=2
    ),

    # Health & Wellness
    FeedSource(
        url="https://www.brigitte.de/gesund/feed.rss",
        domain="www.brigitte.de",
        category="lifestyle",
        theme="health",
        strategy="daily_updates",  # Previous day items
        description="BRIGITTE - Health & Wellness",
        priority=2
    ),

    # ========================================================================
    # SPECIALIZED TOPICS (Advanced)
    # ========================================================================

    # Science & Knowledge
    FeedSource(
        url="https://www.geo.de/feed/rss/wissen/",
        domain="www.geo.de",
        category="specialized",
        theme="science",
        strategy="daily_updates",
        description="GEO - Science & Knowledge",
        priority=3
    ),
    FeedSource(
        url="https://rss.dw.com/xml/rss-de-cul",
        domain="rss.dw.com",
        category="specialized",
        theme="culture",
        strategy="daily_updates",
        description="DW - Culture & Lifestyle",
        priority=3
    ),

    # # Technology & Digital
    FeedSource(
        url="https://t3n.de/rss.xml",
        domain="t3n.de",
        category="specialized",
        theme="technology",
        strategy="daily_updates",
        description="t3n - Tech news",
        priority=3
    ),
]


def get_feeds_by_strategy(strategy: FetchStrategy) -> List[FeedSource]:
    """
    Get all feeds that use a specific fetching strategy.

    Args:
        strategy: The fetch strategy to filter by

    Returns:
        List of feed sources matching the strategy
    """
    return [feed for feed in FEED_SOURCES if feed.strategy == strategy]


def get_feeds_by_domain() -> Dict[str, List[FeedSource]]:
    """
    Group all feeds by their domain.

    Returns:
        Dictionary mapping domains to their feed sources
    """
    feeds_by_domain: Dict[str, List[FeedSource]] = {}

    for feed in FEED_SOURCES:
        if feed.domain not in feeds_by_domain:
            feeds_by_domain[feed.domain] = []
        feeds_by_domain[feed.domain].append(feed)

    return feeds_by_domain


def get_feeds_by_priority() -> Dict[int, List[FeedSource]]:
    """
    Group all feeds by their priority level.

    Returns:
        Dictionary mapping priority levels to their feed sources
    """
    feeds_by_priority: Dict[int, List[FeedSource]] = {}

    for feed in FEED_SOURCES:
        if feed.priority not in feeds_by_priority:
            feeds_by_priority[feed.priority] = []
        feeds_by_priority[feed.priority].append(feed)

    return feeds_by_priority


def get_all_domains() -> List[str]:
    """
    Get a list of all unique domains.

    Returns:
        List of unique domain names
    """
    return list(set(feed.domain for feed in FEED_SOURCES))
