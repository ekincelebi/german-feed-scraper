"""Configuration modules."""

from app.config.feed_config import (
    FEED_SOURCES,
    FeedSource,
    FetchStrategy,
    get_feeds_by_strategy,
    get_feeds_by_domain,
    get_feeds_by_priority,
    get_all_domains,
)

__all__ = [
    "FEED_SOURCES",
    "FeedSource",
    "FetchStrategy",
    "get_feeds_by_strategy",
    "get_feeds_by_domain",
    "get_feeds_by_priority",
    "get_all_domains",
]
