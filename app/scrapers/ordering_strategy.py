"""
Feed ordering strategies for optimal diversity and coverage.

Implements various strategies including round-robin domain distribution.
"""

from typing import List, Dict, Any
from collections import defaultdict
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeedOrderingStrategy:
    """Strategies for ordering feeds before scraping."""

    @staticmethod
    def round_robin_by_domain(feeds: List[Dict[str, Any]], domain_key: str = "domain") -> List[Dict[str, Any]]:
        """
        Order feeds using round-robin strategy by domain.

        This ensures maximum domain diversity - all domains are represented
        early in the scraping process. Useful when scraping might be interrupted.

        Algorithm:
        1. Group all feeds by domain
        2. Iterate through domains in rotation
        3. Take one feed from each domain per cycle
        4. Repeat until all feeds are ordered

        Example:
            Input:  [spiegel#1, spiegel#2, dw#1, dw#2, tagesschau#1]
            Output: [spiegel#1, dw#1, tagesschau#1, spiegel#2, dw#2]

        Args:
            feeds: List of feed dictionaries
            domain_key: Key to use for domain grouping (default: "domain")

        Returns:
            Reordered list of feeds with domain diversity
        """
        if not feeds:
            return []

        # Group feeds by domain
        feeds_by_domain = defaultdict(list)
        for feed in feeds:
            domain = feed.get(domain_key, "unknown")
            feeds_by_domain[domain].append(feed)

        domains = list(feeds_by_domain.keys())
        logger.info(f"Round-robin ordering: {len(feeds)} feeds across {len(domains)} domains")

        # Track statistics
        for domain, domain_feeds in feeds_by_domain.items():
            logger.debug(f"  {domain}: {len(domain_feeds)} feeds")

        # Round-robin through domains
        ordered_feeds = []
        domain_index = 0

        while any(feeds_by_domain.values()):  # While any domain still has feeds
            # Get next domain with feeds
            domain = domains[domain_index % len(domains)]

            if feeds_by_domain[domain]:
                # Take one feed from this domain
                feed = feeds_by_domain[domain].pop(0)
                ordered_feeds.append(feed)

            domain_index += 1

        logger.info(f"Round-robin complete: ordered {len(ordered_feeds)} feeds")
        return ordered_feeds

    @staticmethod
    def random_shuffle(feeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Randomly shuffle feeds.

        Simple strategy that provides some diversity through randomization.

        Args:
            feeds: List of feed dictionaries

        Returns:
            Randomly shuffled list of feeds
        """
        import random

        shuffled = feeds.copy()
        random.shuffle(shuffled)
        logger.info(f"Random shuffle: {len(shuffled)} feeds")
        return shuffled

    @staticmethod
    def priority_sort(
        feeds: List[Dict[str, Any]],
        priority_key: str = "priority",
        ascending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sort feeds by priority level.

        Args:
            feeds: List of feed dictionaries
            priority_key: Key to use for priority (default: "priority")
            ascending: If True, lower priority values come first (default: True)

        Returns:
            Priority-sorted list of feeds
        """
        sorted_feeds = sorted(
            feeds,
            key=lambda f: f.get(priority_key, 999),
            reverse=not ascending
        )
        logger.info(f"Priority sort: {len(sorted_feeds)} feeds")
        return sorted_feeds

    @staticmethod
    def stratified_sample(
        feeds: List[Dict[str, Any]],
        domain_key: str = "domain",
        samples_per_domain: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Take N feeds from each domain (stratified sampling).

        Useful for testing or quick analysis with balanced representation.

        Args:
            feeds: List of feed dictionaries
            domain_key: Key to use for domain grouping (default: "domain")
            samples_per_domain: Number of feeds to take per domain

        Returns:
            Stratified sample of feeds
        """
        if not feeds:
            return []

        # Group feeds by domain
        feeds_by_domain = defaultdict(list)
        for feed in feeds:
            domain = feed.get(domain_key, "unknown")
            feeds_by_domain[domain].append(feed)

        # Take N samples from each domain
        sampled_feeds = []
        for domain, domain_feeds in feeds_by_domain.items():
            sample_size = min(samples_per_domain, len(domain_feeds))
            sampled_feeds.extend(domain_feeds[:sample_size])
            logger.debug(f"Sampled {sample_size} feeds from {domain}")

        logger.info(f"Stratified sampling: {len(sampled_feeds)} feeds from {len(feeds_by_domain)} domains")
        return sampled_feeds

    @staticmethod
    def hybrid_priority_roundrobin(
        feeds: List[Dict[str, Any]],
        domain_key: str = "domain",
        priority_key: str = "priority"
    ) -> List[Dict[str, Any]]:
        """
        Combine priority sorting with round-robin for optimal ordering.

        Algorithm:
        1. Group feeds by priority level
        2. Within each priority level, apply round-robin by domain
        3. Concatenate results (high priority first)

        This ensures:
        - High-priority feeds are scraped first
        - Within each priority, all domains are represented

        Args:
            feeds: List of feed dictionaries
            domain_key: Key to use for domain grouping
            priority_key: Key to use for priority sorting

        Returns:
            Optimally ordered list of feeds
        """
        if not feeds:
            return []

        # Group by priority
        feeds_by_priority = defaultdict(list)
        for feed in feeds:
            priority = feed.get(priority_key, 999)
            feeds_by_priority[priority].append(feed)

        # Sort priorities (lower = higher priority)
        priorities = sorted(feeds_by_priority.keys())

        # Apply round-robin within each priority level
        ordered_feeds = []
        for priority in priorities:
            priority_feeds = feeds_by_priority[priority]
            roundrobin_feeds = FeedOrderingStrategy.round_robin_by_domain(priority_feeds, domain_key)
            ordered_feeds.extend(roundrobin_feeds)
            logger.debug(f"Priority {priority}: {len(roundrobin_feeds)} feeds")

        logger.info(
            f"Hybrid ordering: {len(ordered_feeds)} feeds across "
            f"{len(priorities)} priority levels"
        )
        return ordered_feeds
