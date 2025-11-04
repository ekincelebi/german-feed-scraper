# Quick Start Guide

Fast guide to get started with the German Feed Scraper.

## Setup (First Time Only)

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Check configuration
python scripts/populate_feeds.py --stats

# 3. Populate feeds database
python scripts/populate_feeds.py
```

## Daily Usage

### For Beginners (Full Archive Mode)

Get entire feed archives to familiarize with German content:

```bash
# Scrape all learning content (high priority)
python scripts/run_strategy_scraper.py --mode full_archive --priority 1

# Scrape all full_archive feeds
python scripts/run_strategy_scraper.py --mode full_archive
```

### For Advanced Learners (Daily Updates Mode)

Get fresh content from yesterday:

```bash
# Scrape yesterday's articles
python scripts/run_strategy_scraper.py --mode daily_updates

# Or use 24-hour window
python scripts/run_strategy_scraper.py --mode daily_updates --24h
```

### Scrape Everything

```bash
# Scrape all feeds with their configured strategies
python scripts/run_strategy_scraper.py --mode all
```

## Common Commands

```bash
# Test with limited feeds first
python scripts/run_strategy_scraper.py --mode all --limit 5

# Scrape specific domain
python scripts/run_strategy_scraper.py --mode all --domain rss.dw.com

# Faster scraping (more workers)
python scripts/run_strategy_scraper.py --mode all --workers 20

# Slower, more polite scraping
python scripts/run_strategy_scraper.py --mode all --workers 5 --max-per-domain 1

# High-priority learning feeds only
python scripts/run_strategy_scraper.py --mode all --priority 1
```

## Understanding Modes

### Full Archive (`full_archive`)
- Fetches ALL articles in feed (50-100 articles)
- Best for learning content, recipes, idioms
- Run once or occasionally
- 4 feeds configured with this strategy

### Daily Updates (`daily_updates`)
- Fetches ONLY yesterday's articles (0-20 articles per feed)
- Best for news, current events
- Run daily via cron job
- 18 feeds configured with this strategy

## Feed Categories

| Priority | Category | Example Feeds | Strategy |
|----------|----------|---------------|----------|
| 1 (High) | Learning | DW German lessons, Nachrichtenleicht | Mixed |
| 2 (Medium) | Mainstream News | Tagesschau, Süddeutsche | Daily |
| 3 (Low) | Specialized | Tech news, Science | Daily |

## Typical Workflow

### Initial Setup
```bash
# Day 1: Get all learning archives
python scripts/run_strategy_scraper.py --mode full_archive

# This gives you ~200 learning articles to start with
```

### Daily Routine
```bash
# Every morning: Get yesterday's news
python scripts/run_strategy_scraper.py --mode daily_updates

# This gives you 0-100 fresh articles daily
```

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| No articles found | Normal for daily_updates if no recent articles |
| Connection errors | Reduce `--workers 5` and `--max-per-domain 1` |
| Some feeds failed | Normal, re-run to retry |
| Taking too long | Reduce `--workers` or use `--limit` |

## Performance

| Configuration | Duration | Use Case |
|---------------|----------|----------|
| `--workers 2 --limit 5` | < 1 min | Testing |
| `--workers 15` (default) | 5-10 min | Production |
| `--workers 5 --max-per-domain 1` | 20-30 min | Respectful scraping |

## Help

```bash
# See all available options
python scripts/run_strategy_scraper.py --help

# See feed statistics
python scripts/populate_feeds.py --stats
```

## Next Steps

1. Test with small sample: `--limit 5`
2. Run full_archive mode once for learning content
3. Set up daily cron job for daily_updates mode (after thorough testing)
4. Monitor logs and adjust as needed

See [FEED_FETCHING_GUIDE.md](./FEED_FETCHING_GUIDE.md) for detailed documentation.
