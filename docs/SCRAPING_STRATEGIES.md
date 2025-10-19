# RSS Feed Scraping Strategies

This document outlines different approaches for scraping RSS feeds from multiple sources, with a focus on achieving dataset diversity and scraping efficiency.

## The Problem

When scraping 698 RSS feeds from 12 different German news domains:

- **Sequential scraping** processes feeds one-by-one in database order
- With delays between requests (1-2 seconds), this takes **hours** to complete
- If feeds are ordered by domain, you may scrape 100+ feeds from one domain before reaching others
- **Result:** After hours of scraping, you only have articles from 1-2 domains

## Distribution of Feeds by Domain

Based on our current dataset:

| Domain | Number of Feeds | Percentage |
|--------|----------------|------------|
| www.spiegel.de | 189 | 27.1% |
| www.tagesschau.de | 179 | 25.6% |
| rss.dw.com | 145 | 20.8% |
| www.heise.de | 106 | 15.2% |
| rss.sueddeutsche.de | 41 | 5.9% |
| Others (7 domains) | 38 | 5.4% |
| **TOTAL** | **698** | **100%** |

## Solution Strategies

### 1. Sequential Scraping (Current/Baseline) ❌

**How it works:**
```python
for feed in all_feeds:
    scrape_feed(feed)
    time.sleep(1)
```

**Pros:**
- Simple implementation
- Easy to understand and debug
- Low resource usage

**Cons:**
- Very slow (698 feeds × 1-2 seconds = hours)
- Poor diversity if feeds are grouped by domain
- If interrupted, may only have data from 1-2 domains

**Use case:** Small feed lists (<50 feeds), not time-sensitive

---

### 2. Random Shuffling ✅

**How it works:**
```python
import random
feeds = get_all_feeds()
random.shuffle(feeds)
for feed in feeds:
    scrape_feed(feed)
```

**Pros:**
- **Trivial to implement** (one line of code)
- Statistically distributes across domains
- Better diversity than ordered sequential

**Cons:**
- Still slow (sequential processing)
- No guarantee of domain coverage if interrupted
- Random order makes debugging harder

**Use case:** Quick fix for existing sequential scrapers

**Implementation complexity:** ⭐ Trivial (1 line)

---

### 3. Domain Round-Robin ⭐⭐

**How it works:**
1. Group all feeds by domain
2. Iterate through domains in rotation
3. Take one feed from each domain per cycle
4. Repeat until all feeds processed

```python
# Group feeds by domain
feeds_by_domain = {
    'spiegel.de': [feed1, feed2, ...],
    'tagesschau.de': [feed3, feed4, ...],
    ...
}

# Round-robin through domains
while any_feeds_remaining:
    for domain in domains:
        if feeds_by_domain[domain]:
            feed = feeds_by_domain[domain].pop(0)
            scrape_feed(feed)
```

**Pros:**
- **Guaranteed diversity** - all domains represented early
- If interrupted after 100 feeds, you have ~8 feeds per domain
- Predictable and debuggable
- Handles imbalanced domains gracefully

**Cons:**
- Still slow (sequential)
- Slightly more complex than random shuffle

**Use case:** When diversity is critical, no infrastructure changes possible

**Implementation complexity:** ⭐⭐ Easy (10-20 lines)

---

### 4. Parallel/Concurrent Scraping ⭐⭐⭐

**How it works:**
Use Python's `ThreadPoolExecutor` or `asyncio` to scrape multiple feeds simultaneously.

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(scrape_feed, feed) for feed in feeds]
    for future in as_completed(futures):
        result = future.result()
```

**Pros:**
- **10-50x faster** depending on worker count
- Can process 698 feeds in 30-60 minutes instead of hours
- I/O-bound operations benefit greatly from concurrency

**Cons:**
- More complex error handling
- Need to respect rate limits (don't hammer servers)
- Higher CPU/memory usage
- Random completion order (no diversity guarantee)

**Use case:** Large feed lists, time-sensitive scraping, production systems

**Implementation complexity:** ⭐⭐⭐ Medium (50-100 lines with proper error handling)

**Key considerations:**
- **Worker count:** 10-20 for web scraping (I/O bound)
- **Rate limiting:** Add delays or use domain-based semaphores
- **Error handling:** One failed feed shouldn't crash entire batch
- **Database connections:** Use connection pooling or per-thread connections

---

### 5. Parallel + Round-Robin ⭐⭐⭐⭐ RECOMMENDED

**How it works:**
1. Group feeds by domain (round-robin)
2. Order feeds to ensure domain diversity
3. Use parallel processing to scrape multiple feeds simultaneously
4. Use domain-based semaphores to prevent hammering single domains

```python
# 1. Round-robin order feeds by domain
ordered_feeds = round_robin_by_domain(feeds)

# 2. Parallel scraping with domain rate limiting
with ThreadPoolExecutor(max_workers=15) as executor:
    for feed in ordered_feeds:
        executor.submit(scrape_with_rate_limit, feed)
```

**Pros:**
- **Best of both worlds:** Speed + Diversity
- 10-50x faster than sequential
- Guaranteed domain distribution
- Respects per-domain rate limits

**Cons:**
- Most complex implementation
- Requires careful rate limit management

**Use case:** Production systems requiring fast, diverse scraping

**Implementation complexity:** ⭐⭐⭐⭐ Medium-High (100-150 lines)

---

### 6. Stratified Sampling ⭐⭐

**How it works:**
Take N feeds from each domain (proportional or equal sampling).

```python
# Equal sampling: 5 feeds per domain
for domain in domains:
    domain_feeds = feeds_by_domain[domain][:5]
    for feed in domain_feeds:
        scrape_feed(feed)

# Result: 12 domains × 5 feeds = 60 feeds total
```

**Pros:**
- Very fast (scrape subset, not all feeds)
- Guaranteed balanced representation
- Good for testing or quick analysis

**Cons:**
- Doesn't scrape all feeds
- Need to decide on sample size

**Use case:** Initial dataset creation, testing, quick analysis

**Implementation complexity:** ⭐⭐ Easy

---

### 7. Priority Queue by Domain ⭐⭐

**How it works:**
Assign priority scores to feeds/domains, scrape high-priority first.

```python
# Priority: domains with fewer feeds go first
domain_counts = count_feeds_per_domain()

def priority(feed):
    return domain_counts[feed.domain]  # Lower = higher priority

sorted_feeds = sorted(feeds, key=priority)
```

**Pros:**
- Ensures underrepresented domains get scraped first
- Customizable priority logic (recency, importance, etc.)

**Cons:**
- Still sequential (slow)
- Priority logic can be complex

**Use case:** When some sources are more important than others

**Implementation complexity:** ⭐⭐ Easy to Medium

---

## Performance Comparison

| Strategy | Time for 698 Feeds | Diversity After 100 Feeds | Complexity |
|----------|-------------------|---------------------------|------------|
| Sequential | 12-23 hours | 1-2 domains | ⭐ |
| Random Shuffle | 12-23 hours | ~8-10 domains | ⭐ |
| Round-Robin | 12-23 hours | All 12 domains | ⭐⭐ |
| Parallel (10 workers) | 1-2 hours | Random (5-8 domains) | ⭐⭐⭐ |
| **Parallel + Round-Robin** | **30-60 min** | **All 12 domains** | ⭐⭐⭐⭐ |
| Stratified (5/domain) | 5-10 minutes | All 12 domains | ⭐⭐ |

*Assumes 1 second per feed average*

---

## Recommended Approach by Use Case

### Quick Fix (Already Running Sequential)
→ **Random Shuffle** (1 line of code)

### Need Diversity, Can't Change Infrastructure
→ **Domain Round-Robin** (10 lines of code)

### Production System, Need Speed + Diversity
→ **Parallel + Round-Robin** ⭐ BEST

### Quick Testing/POC
→ **Stratified Sampling** (60 feeds instead of 698)

### One-Time Large Scrape
→ **Parallel Scraping** (simplest fast option)

---

## Implementation Details: Parallel + Round-Robin

### Architecture

```
┌─────────────────────────────────────────┐
│  1. Load all feeds from database        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. Group feeds by domain               │
│     spiegel.de: [189 feeds]             │
│     tagesschau.de: [179 feeds]          │
│     dw.com: [145 feeds]                 │
│     ...                                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. Round-robin order feeds             │
│     [spiegel.de #1,                     │
│      tagesschau.de #1,                  │
│      dw.com #1,                         │
│      heise.de #1,                       │
│      ...,                               │
│      spiegel.de #2,                     │
│      ...]                               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. Parallel processing                 │
│     ThreadPool (15 workers)             │
│                                         │
│     [Worker 1] → Feed 1                 │
│     [Worker 2] → Feed 2                 │
│     [Worker 3] → Feed 3                 │
│     ...                                 │
│     [Worker 15] → Feed 15               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5. Domain-based rate limiting          │
│     Semaphore per domain (max 3 at once)│
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  6. Save to database                    │
└─────────────────────────────────────────┘
```

### Key Components

1. **Feed Ordering:** Round-robin ensures first 100 feeds span all domains
2. **Thread Pool:** 15 workers process feeds concurrently
3. **Domain Semaphores:** Limit concurrent requests per domain (respect rate limits)
4. **Error Handling:** Failed feeds don't crash entire process
5. **Progress Tracking:** Real-time stats on completion

### Rate Limiting Strategy

```python
# Global: 15 concurrent feeds across all domains
ThreadPoolExecutor(max_workers=15)

# Per-domain: Max 3 concurrent requests to same domain
domain_semaphores = {
    'spiegel.de': Semaphore(3),
    'tagesschau.de': Semaphore(3),
    ...
}
```

This prevents:
- Overwhelming any single server
- Getting IP-banned for too many requests
- Network congestion

---

## Expected Results: Parallel + Round-Robin

### After 10 minutes of scraping (~150 feeds):
- Articles from **all 12 domains**
- Approximately:
  - spiegel.de: ~40 feeds (27%)
  - tagesschau.de: ~38 feeds (25%)
  - dw.com: ~31 feeds (21%)
  - heise.de: ~23 feeds (15%)
  - Others: ~18 feeds (12%)

### After complete scraping (~45 minutes):
- All 698 feeds processed
- Thousands of articles from all domains
- Balanced, diverse German language dataset

---

## Configuration Parameters

```python
# Scraper configuration
MAX_WORKERS = 15                    # Total concurrent feeds
MAX_PER_DOMAIN = 3                  # Max concurrent per domain
FEED_TIMEOUT = 30                   # Seconds
ARTICLE_SCRAPE_TIMEOUT = 30         # Seconds for full content
DELAY_BETWEEN_ARTICLES = 0.5        # Seconds (per-feed rate limit)
RETRY_FAILED_FEEDS = True           # Retry on error
MAX_RETRIES = 2                     # Retry attempts
```

### Tuning Guidelines

**Increase MAX_WORKERS** (20-30) if:
- You have good internet bandwidth
- Target sites are fast
- You want maximum speed

**Decrease MAX_WORKERS** (5-10) if:
- You have limited bandwidth
- Getting timeout errors
- Target sites are slow

**Increase MAX_PER_DOMAIN** (5-10) if:
- Target site can handle load
- It's your own infrastructure
- You have permission for heavy scraping

**Decrease MAX_PER_DOMAIN** (1-2) if:
- Getting rate-limited or blocked
- Scraping third-party sites respectfully
- Sites have strict rate limits

---

## Monitoring & Logging

The parallel scraper provides real-time progress updates:

```
[2025-01-19 10:00:00] Starting Parallel + Round-Robin scraper
[2025-01-19 10:00:00] Total feeds: 698 across 12 domains
[2025-01-19 10:00:00] Configuration: 15 workers, 3 max per domain

[2025-01-19 10:00:05] [1/698] Processing www.spiegel.de (189 total)
[2025-01-19 10:00:05] [2/698] Processing www.tagesschau.de (179 total)
[2025-01-19 10:00:05] [3/698] Processing rss.dw.com (145 total)
...
[2025-01-19 10:00:10] Progress: 15/698 (2.2%) | Articles: 234
[2025-01-19 10:01:00] Progress: 95/698 (13.6%) | Articles: 1,432
[2025-01-19 10:05:00] Progress: 350/698 (50.1%) | Articles: 4,287
...
[2025-01-19 10:42:00] COMPLETE!
                      Total feeds: 698
                      Successful: 691
                      Failed: 7
                      Total articles: 8,934
                      Duration: 42 minutes
                      Domains covered: 12/12
```

---

## Error Handling

### Retry Logic
Failed feeds are automatically retried up to 2 times with exponential backoff.

### Failed Feed Tracking
Feeds that fail after all retries are:
1. Marked with `status='error'` in database
2. Logged with error details
3. Reported in final statistics

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| Timeout | Slow server/network | Increase `FEED_TIMEOUT` |
| Connection refused | Too many requests | Decrease `MAX_PER_DOMAIN` |
| HTTP 429 | Rate limited | Add delays, reduce workers |
| HTTP 403/401 | Blocked/auth | Check user-agent, cookies |
| Parse error | Invalid RSS | Skip feed, mark as error |

---

## Testing Strategy

### 1. Test with Small Sample
```bash
# Test with 5 feeds per domain (60 feeds total)
python scripts/run_parallel_scraper.py --stratified --feeds-per-domain 5
```

### 2. Test Single Domain
```bash
# Test with one domain only
python scripts/run_parallel_scraper.py --domain rss.dw.com
```

### 3. Test with Low Concurrency
```bash
# Safe testing with 3 workers
python scripts/run_parallel_scraper.py --workers 3 --max-per-domain 1
```

### 4. Full Production Run
```bash
# Full speed, all feeds
python scripts/run_parallel_scraper.py --workers 15 --max-per-domain 3
```

---

## Best Practices

### 1. Respect Robots.txt
Check each domain's robots.txt before aggressive scraping.

### 2. Use Appropriate User-Agent
Identify your scraper clearly:
```python
headers = {
    'User-Agent': 'GermanFeedScraper/1.0 (Educational; contact@example.com)'
}
```

### 3. Implement Backoff on Errors
If a domain returns errors, slow down or pause scraping for that domain.

### 4. Monitor Resource Usage
- CPU usage
- Memory consumption
- Network bandwidth
- Database connection pool

### 5. Schedule Appropriately
Run during off-peak hours for target sites (e.g., late night EU time).

### 6. Keep Statistics
Track scraping efficiency to optimize over time:
- Articles per feed
- Success rate per domain
- Average scraping time
- Error patterns

---

## Conclusion

The **Parallel + Round-Robin** strategy provides the optimal balance of:
- ⚡ **Speed:** 10-50x faster than sequential
- 🎯 **Diversity:** Guaranteed coverage of all domains
- 🛡️ **Reliability:** Respects rate limits, handles errors gracefully
- 📊 **Visibility:** Real-time progress tracking

For a production German news scraper with 698 feeds across 12 domains, this is the recommended approach.
