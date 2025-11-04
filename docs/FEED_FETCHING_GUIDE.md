# Feed Fetching and Scraping Strategy Guide

This guide explains how to use the feed fetching and scraping system that supports two modes: **full archive** for beginners and **daily updates** for advanced learners.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup](#setup)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [Strategies](#strategies)
7. [Examples](#examples)
8. [Monitoring](#monitoring)

## Overview

The system implements intelligent feed fetching with:

- **Two Modes:**
  - `full_archive`: Fetch entire feed archive (for beginners familiarizing with German)
  - `daily_updates`: Fetch only recent articles (for advanced learners wanting fresh content)

- **Parallel Processing:** Uses ThreadPoolExecutor for 10-50x faster scraping
- **Round-Robin Domain Distribution:** Ensures diversity across all sources
- **Domain-Based Rate Limiting:** Prevents overwhelming individual servers
- **Priority System:** High-priority learning feeds are processed first

## Architecture

### Components

1. **Feed Configuration** ([app/config/feed_config.py](../app/config/feed_config.py))
   - Defines all RSS feed sources
   - Assigns strategies and priorities to each feed

2. **Feed Fetcher** ([app/scrapers/feed_fetcher.py](../app/scrapers/feed_fetcher.py))
   - Fetches and filters RSS feeds
   - Implements date filtering for daily updates mode

3. **Ordering Strategy** ([app/scrapers/ordering_strategy.py](../app/scrapers/ordering_strategy.py))
   - Round-robin domain ordering
   - Priority-based sorting
   - Stratified sampling for testing

4. **Parallel Scraper** ([app/scrapers/parallel_scraper.py](../app/scrapers/parallel_scraper.py))
   - Concurrent feed processing
   - Domain-based rate limiting
   - Progress tracking and statistics

### Database Schema

The `feeds` table includes:
- `strategy`: 'full_archive' or 'daily_updates'
- `category`: learning, news_simple, news_mainstream, lifestyle, specialized
- `theme`: vocabulary, idioms, general_news, etc.
- `priority`: 1 (High), 2 (Medium), 3 (Low)

## Setup

### 1. Apply Database Migration

```bash
# Apply the feed metadata migration (005_feed_metadata.sql)
# This adds strategy, category, theme, priority columns to feeds table
```

### 2. Populate Feeds

```bash
# Show feed statistics
python scripts/populate_feeds.py --stats

# Populate feeds from configuration
python scripts/populate_feeds.py

# Update existing feeds with new metadata
python scripts/populate_feeds.py --update
```

### 3. Verify Setup

```bash
# Check database connection and feeds
python -c "from app.database import get_db; db = get_db(); \
  result = db.table('feeds').select('*').limit(5).execute(); \
  print('Feeds loaded:', len(result.data))"
```

## Usage

### Basic Commands

#### 1. Full Archive Mode (Beginners)

Fetch entire feed archives for familiarization with German content:

```bash
# Scrape all full_archive feeds
python scripts/run_strategy_scraper.py --mode full_archive

# Scrape with custom parallelism
python scripts/run_strategy_scraper.py --mode full_archive --workers 10 --max-per-domain 2
```

#### 2. Daily Updates Mode (Advanced Learners)

Fetch only recent articles (previous day):

```bash
# Scrape all daily_updates feeds
python scripts/run_strategy_scraper.py --mode daily_updates

# Use 24-hour window instead of previous day
python scripts/run_strategy_scraper.py --mode daily_updates --24h
```

#### 3. All Feeds Mode

Scrape all feeds using their configured strategies:

```bash
# Scrape all feeds (respects individual strategies)
python scripts/run_strategy_scraper.py --mode all
```

### Filtering Options

#### Filter by Priority

```bash
# Only high-priority feeds (learning content)
python scripts/run_strategy_scraper.py --mode all --priority 1

# Medium priority (mainstream news)
python scripts/run_strategy_scraper.py --mode all --priority 2

# Low priority (specialized topics)
python scripts/run_strategy_scraper.py --mode all --priority 3
```

#### Filter by Domain

```bash
# Only DW (Deutsche Welle) feeds
python scripts/run_strategy_scraper.py --mode all --domain rss.dw.com

# Only Nachrichtenleicht (easy German)
python scripts/run_strategy_scraper.py --mode all --domain www.nachrichtenleicht.de
```

#### Limit Number of Feeds

```bash
# Test with just 5 feeds
python scripts/run_strategy_scraper.py --mode all --limit 5
```

### Performance Tuning

#### Adjust Worker Count

```bash
# More workers = faster (use on good internet)
python scripts/run_strategy_scraper.py --mode all --workers 20

# Fewer workers = more stable (use on slow connection)
python scripts/run_strategy_scraper.py --mode all --workers 5
```

#### Adjust Per-Domain Limit

```bash
# More aggressive (use with permission)
python scripts/run_strategy_scraper.py --mode all --max-per-domain 5

# More polite (use for third-party sites)
python scripts/run_strategy_scraper.py --mode all --max-per-domain 1
```

## Configuration

### Feed Configuration

Edit [app/config/feed_config.py](../app/config/feed_config.py) to:

- Add new feed sources
- Change fetch strategies
- Adjust priorities
- Update categories and themes

Example:

```python
FeedSource(
    url="https://example.de/feed.rss",
    domain="example.de",
    category="news_mainstream",
    theme="politics",
    strategy="daily_updates",  # or "full_archive"
    description="Example Feed",
    priority=2  # 1=High, 2=Medium, 3=Low
)
```

After modifying, update the database:

```bash
python scripts/populate_feeds.py --update
```

### Current Feed Statistics

```
Total Feeds: 22

By Strategy:
  - daily_updates: 18 feeds
  - full_archive: 4 feeds

By Priority:
  - High (1): 6 feeds (learning content)
  - Medium (2): 13 feeds (mainstream news)
  - Low (3): 3 feeds (specialized topics)

By Domain:
  - rss.dw.com: 6 feeds
  - rss.sueddeutsche.de: 5 feeds
  - www.spiegel.de: 3 feeds
  - www.nachrichtenleicht.de: 2 feeds
  - www.brigitte.de: 2 feeds
  - Others: 4 feeds
```

## Strategies

### Full Archive Strategy

**Use for:**
- Beginner learning content (idioms, vocabulary)
- Audio lessons with transcripts
- Recipe collections
- One-time archive fetches

**Behavior:**
- Fetches all available entries in the feed
- No date filtering
- Ideal for building comprehensive learning library

**Example Feeds:**
- Das sagt man so! (German idioms)
- Alltagsdeutsch (Everyday German with transcripts)
- Chefkoch recipes

### Daily Updates Strategy

**Use for:**
- News feeds (current events)
- Advanced learning content
- Regularly updated content
- Scheduled daily scraping

**Behavior:**
- Fetches only entries from previous day
- Can use 24-hour window with `--24h` flag
- Ideal for staying current with German news

**Example Feeds:**
- Tagesschau (main German news)
- Nachrichtenleicht (easy German news)
- Süddeutsche Zeitung sections

## Examples

### Example 1: Initial Setup for Beginners

```bash
# 1. Populate feeds
python scripts/populate_feeds.py

# 2. Fetch all learning content archives
python scripts/run_strategy_scraper.py --mode full_archive --priority 1

# 3. Fetch simplified news archives
python scripts/run_strategy_scraper.py --mode full_archive --category news_simple
```

### Example 2: Daily Updates for Advanced Learners

```bash
# Fetch yesterday's news from all sources
python scripts/run_strategy_scraper.py --mode daily_updates

# Or use cron job (6 AM daily):
# 0 6 * * * cd /path/to/scraper && python scripts/run_strategy_scraper.py --mode daily_updates
```

### Example 3: Testing Before Production

```bash
# Test with 2 high-priority feeds
python scripts/run_strategy_scraper.py --mode all --priority 1 --limit 2 --workers 2

# Test specific domain
python scripts/run_strategy_scraper.py --mode all --domain rss.dw.com --limit 3

# Test with low concurrency
python scripts/run_strategy_scraper.py --mode all --workers 3 --max-per-domain 1 --limit 5
```

### Example 4: Full Production Run

```bash
# Run all feeds with optimal settings
python scripts/run_strategy_scraper.py --mode all --workers 15 --max-per-domain 3

# Expected results:
# - full_archive feeds: 4 feeds, ~200 articles
# - daily_updates feeds: 18 feeds, varies by day (0-100 articles)
# - Duration: 5-15 minutes depending on feed availability
```

## Monitoring

### Output Example

```
============================================================
ALL FEEDS MODE
============================================================
Scraping all feeds with their configured strategies
============================================================

Found 22 active feeds
  - 4 with full_archive strategy
  - 18 with daily_updates strategy

--- Processing full_archive feeds ---
Applying round-robin ordering by domain...
Round-robin ordering: 4 feeds across 2 domains
Starting parallel scraper...
Total feeds: 4
Strategy: full_archive
Configuration: 15 workers, 3 max per domain
============================================================

Progress: 4/4 (100.0%) | Articles: 196 | Elapsed: 0.7m

============================================================
SCRAPING COMPLETE!
============================================================
Total feeds processed: 4
Successful: 4
Failed: 0
Total articles saved: 196
Duration: 0.7 minutes
Domains covered: 2
============================================================

Domain Statistics:
  rss.dw.com: 3 feeds, 148 articles, 0 errors
  www.chefkoch.de: 1 feeds, 48 articles, 0 errors
============================================================
```

### Troubleshooting

#### No articles found in daily_updates mode

This is normal if:
- The feeds don't have articles from yesterday
- Article dates are in the future (timezone issues)
- Feed doesn't include publish dates

**Solution:** Use `--24h` flag for a wider time window

#### Connection errors or timeouts

**Solutions:**
- Reduce `--workers` (e.g., to 5-10)
- Reduce `--max-per-domain` (e.g., to 1-2)
- Check internet connection
- Check if source site is accessible

#### Some feeds marked as failed

This is normal. Common reasons:
- Feed temporarily unavailable
- Server timeout
- Invalid RSS format
- Rate limiting

**Solution:** Re-run the scraper; failed feeds will be retried

## Performance Guidelines

### Recommended Settings by Use Case

| Use Case | Workers | Max Per Domain | Expected Duration |
|----------|---------|----------------|-------------------|
| Testing | 2-5 | 1-2 | Fast (seconds) |
| Daily Updates | 10-15 | 3 | Medium (5-10 min) |
| Full Archive | 15-20 | 3-5 | Long (10-30 min) |
| Respectful Scraping | 5 | 1 | Slower (20-40 min) |

### Rate Limiting

The system automatically:
- Limits concurrent requests per domain
- Adds delays between requests
- Respects server response times
- Retries failed requests with backoff

## Next Steps

### Implementing Cron Job (After Testing)

Once you've thoroughly tested the scraping:

1. **Create cron job for daily updates:**

```bash
# Edit crontab
crontab -e

# Add line (runs at 6 AM daily):
0 6 * * * cd /path/to/german-feed-scraper && source venv/bin/activate && python scripts/run_strategy_scraper.py --mode daily_updates >> logs/scraper.log 2>&1
```

2. **Create cron job for weekly archive updates:**

```bash
# Add line (runs Sunday at 2 AM):
0 2 * * 0 cd /path/to/german-feed-scraper && source venv/bin/activate && python scripts/run_strategy_scraper.py --mode full_archive >> logs/scraper.log 2>&1
```

### Monitoring and Maintenance

- Check logs regularly
- Monitor failed feed rates
- Update feed URLs as needed
- Adjust priorities based on user needs
- Add new feeds to configuration as discovered

## Related Documentation

- [API Routes Reference](./API_ROUTES_REFERENCE.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Scraping Strategies](./SCRAPING_STRATEGIES.md)
- [Feed Fetching Strategies](../feed_fetching_strategies.txt)
