# German Feed Scraper

A Python backend service that discovers and scrapes articles from German RSS feeds and stores them in a Supabase PostgreSQL database.

## Features

- Automatic RSS feed discovery using feedsearch.dev API
- Article scraping from multiple German news sources
- Supabase PostgreSQL database storage
- Duplicate article prevention
- Error handling and logging
- Support for 13 major German websites

## Prerequisites

- Python 3.8 or higher
- A Supabase account (free tier available)
- pip package manager

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Set Up Supabase Database

#### Create a Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in your project details:
   - Project name: Choose any name (e.g., "german-feed-scraper")
   - Database password: Create a strong password (save this!)
   - Region: Choose closest to you
4. Click "Create new project" and wait for setup to complete

#### Get Your Supabase Keys

1. Once your project is ready, go to **Settings** (gear icon in sidebar)
2. Click on **API** in the settings menu
3. You'll need two values:
   - **Project URL**: Copy the URL under "Project URL" (looks like `https://xxxxx.supabase.co`)
   - **Service Role Key**: Copy the key under "Project API keys" > "service_role" (click to reveal)

**IMPORTANT**: Use the `service_role` key (not the `anon` key) as it has full database access needed for the scraper.

#### Run Database Migration

1. In your Supabase project, go to **SQL Editor** (in the sidebar)
2. Click "New query"
3. Copy the contents of [supabase/migrations/001_initial_schema.sql](supabase/migrations/001_initial_schema.sql)
4. Paste it into the SQL editor
5. Click "Run" to execute the migration
6. You should see "Success. No rows returned" message

This will create:
- `feeds` table for storing RSS feed URLs
- `articles` table for storing scraped articles
- Indexes for better performance
- Triggers for automatic timestamp updates

### 3. Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file and add your Supabase credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key-here
LOG_LEVEL=INFO
SCRAPE_INTERVAL=60
```

Replace:
- `your-project-id.supabase.co` with your actual Supabase Project URL
- `your-service-role-key-here` with your actual service_role key

### 4. Verify Database Setup (Optional)

You can verify the tables were created correctly:

1. In Supabase, go to **Table Editor**
2. You should see two tables: `feeds` and `articles`
3. Click on each to see their structure

## Usage

### Step 1: Discover RSS Feeds

Run the feed discovery script to find RSS feeds from the target German websites:

```bash
python scripts/discover_feeds.py
```

This will:
- Query feedsearch.dev for each target website
- Discover available RSS feeds
- Save them to the Supabase `feeds` table

Expected output:
```
Found X feeds for https://www.tagesschau.de
Saved Y new feeds from https://www.tagesschau.de
...
Total feeds saved: Z
```

### Step 2: Scrape Articles (RSS Summary Only)

Run the basic scraper to fetch article summaries from RSS feeds:

```bash
python scripts/run_scraper.py
```

This will:
- Fetch all active feeds from the database
- Parse each RSS feed
- Extract article metadata (title, URL, summary from RSS)
- Save new articles to the `articles` table (skips duplicates)

**Note:** This only gets the RSS feed summary, not the full article content.

Expected output:
```
Found X active feeds to scrape
Saved Y new articles from feed...
...
Total feeds processed: X
Total new articles saved: Y
Failed feeds: Z
```

### Step 3: Scrape Full Article Content (Recommended)

The full content scraper extracts complete article text from webpages. It supports two modes:

#### Option A: Parallel + Round-Robin (RECOMMENDED - 10-50x Faster)

This is the **recommended approach** for scraping 698 feeds efficiently with guaranteed domain diversity:

```bash
# Default: Parallel mode with 15 workers, 3 max per domain
python scripts/scrape_full_content.py
```

**Why Parallel + Round-Robin?**
- **Speed:** 10-50x faster than sequential (completes in 30-60 minutes instead of hours)
- **Diversity:** Guarantees articles from all 12 domains, even if interrupted
- **Respectful:** Limits concurrent requests per domain to avoid overwhelming servers
- **Smart ordering:** Round-robin ensures first 100 feeds span all domains

**How it works:**
1. Groups feeds by domain (spiegel.de, tagesschau.de, dw.com, etc.)
2. Orders feeds in round-robin fashion (1 from each domain, repeat)
3. Processes 15 feeds concurrently with max 3 requests per domain
4. Provides real-time progress updates with ETA

Expected output:
```
===============================================================================
PARALLEL + ROUND-ROBIN FULL CONTENT SCRAPER
===============================================================================
Total feeds: 698
Max workers: 15
Max per domain: 3
===============================================================================
Grouping feeds across 12 domains:
  www.spiegel.de: 189 feeds
  www.tagesschau.de: 179 feeds
  rss.dw.com: 145 feeds
  ...
Ordered 698 feeds using round-robin strategy
Starting parallel scraping...

Progress: 10/698 (1.4%) | Articles: 156 | Rate: 2.3 feeds/sec | ETA: 42 min
Progress: 50/698 (7.2%) | Articles: 782 | Rate: 2.8 feeds/sec | ETA: 35 min
...
===============================================================================
SCRAPING COMPLETE!
===============================================================================
Total feeds: 698
Successful: 691
Failed: 7
Total articles: 8,934
Domains covered: 12
Duration: 42m 18s
Average: 2.75 feeds/sec
===============================================================================

Domains covered:
  ✓ rss.dw.com
  ✓ t3n.de
  ✓ www.apotheken-umschau.de
  ✓ www.brigitte.de
  ✓ www.geo.de
  ✓ www.heise.de
  ✓ www.nachrichtenleicht.de
  ✓ www.spiegel.de
  ✓ www.tagesschau.de
  ...
```

**Advanced Options:**

```bash
# Test with stratified sampling (5 feeds per domain = 60 feeds total)
python scripts/scrape_full_content.py --stratified --feeds-per-domain 5

# Scrape single domain only
python scripts/scrape_full_content.py --domain rss.dw.com

# Custom worker configuration for faster scraping
python scripts/scrape_full_content.py --workers 20 --max-per-domain 5

# See all options
python scripts/scrape_full_content.py --help
```

#### Option B: Sequential Mode (Original - Slow)

For testing or if you prefer the original sequential approach:

```bash
python scripts/scrape_full_content.py --sequential
```

**Note:** Sequential mode processes feeds one-by-one and takes 12-23 hours for 698 feeds. Only use this for testing or debugging.

**Benefits of Full Content Scraping:**
- Gets the complete article text, not just RSS summaries
- Removes HTML tags and formatting
- Provides clean, readable content
- Better for analysis and language learning
- Parallel mode ensures diverse dataset from all domains quickly

**For detailed comparison of scraping strategies, see:** [docs/SCRAPING_STRATEGIES.md](docs/SCRAPING_STRATEGIES.md)

### Step 4: Process Articles with AI for Language Learning (Optional)

After scraping articles, you can enhance them with AI-powered analysis for language learning purposes using Groq's Llama 3.1 70B model.

#### Get Groq API Key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up for a free account
3. Create a new API key
4. Add it to your `.env` file:
```env
GROQ_API_KEY=your-groq-api-key-here
```

#### Run Database Migration

Before processing, create the `article_analysis` table:

1. In Supabase, go to **SQL Editor**
2. Click "New query"
3. Copy the contents of [supabase/migrations/002_article_analysis.sql](supabase/migrations/002_article_analysis.sql)
4. Paste and click "Run"

This creates the `article_analysis` table with foreign key to `articles`.

#### Process Articles

The AI processor extracts language learning features from articles:

**Features Analyzed:**
- **Language Level (CEFR)**: A1-C2 classification
- **Topics**: Main topics covered (politics, technology, health, etc.)
- **Vocabulary**: 5-15 key words with artikel (der/die/das), English translation, and plural form
- **Grammar Patterns**: Key grammar structures worth learning

**Test with 100 articles (recommended first):**
```bash
python scripts/process_articles.py --limit 100
```

**Process all articles:**
```bash
python scripts/process_articles.py
```

**Custom budget:**
```bash
# Process with $2.50 budget
python scripts/process_articles.py --max-cost 2.50
```

**Cost Estimates (Groq Llama 3.1 70B):**
- Average: ~$0.0006 per article
- 100 articles: ~$0.06
- 1,444 articles: ~$0.91
- Default budget: $5.00

Expected output:
```
===============================================================================
AI ARTICLE PROCESSOR FOR LANGUAGE LEARNING
===============================================================================
Model: Llama 3.1 70B (via Groq)
Budget: $5.00 USD
Rate limit: 0.5s between requests
Max retries: 3
Limit: 100 articles (testing mode)
===============================================================================

Processing article 1/100: 12345
Processed article 12345: B2, 8 words, 1234 tokens, $0.0006

Progress: 10/100 (10.0%) | Cost: $0.0059 | Rate: 2.3 articles/sec | ETA: 38s
...
===============================================================================
PROCESSING COMPLETE!
===============================================================================
✓ Successfully processed: 100
✗ Failed: 0

📊 Statistics:
  Total tokens: 123,456
  Avg tokens/article: 1,235

💰 Cost:
  Total: $0.0598
  Avg/article: $0.000598
  Remaining budget: $4.9402
===============================================================================
```

**Advanced Options:**
```bash
# Faster processing (less polite to API)
python scripts/process_articles.py --rate-limit 0.2

# More retries for unstable connections
python scripts/process_articles.py --max-retries 5

# See all options
python scripts/process_articles.py --help
```

**Benefits for Language Learners:**
- **Difficulty filtering**: Find articles matching your level (A1-C2)
- **Topic-based learning**: Focus on subjects you care about
- **Vocabulary building**: Learn words with proper grammar (artikel + plural)
- **Contextual grammar**: See grammar patterns in real usage
- **Smart recommendations**: Build recommendation systems based on analysis

### Step 5: View Statistics and Analytics

Use the built-in statistics tool to analyze your scraped data:

```bash
# Show complete statistics report
python scripts/show_stats.py

# Show recent articles from specific domain
python scripts/show_stats.py --recent 10 --domain www.spiegel.de

# Export statistics to JSON
python scripts/show_stats.py --export-json stats.json

# Export domain breakdown to CSV
python scripts/show_stats.py --export-csv domains.csv

# Show only feed statistics
python scripts/show_stats.py --feeds-only

# Show only article statistics
python scripts/show_stats.py --articles-only
```

### Viewing Your Data

To view the scraped articles:

1. Go to your Supabase project
2. Click on **Table Editor**
3. Select the `articles` table
4. You'll see all scraped articles with their metadata

You can also query the data using SQL Editor:

```sql
-- Get latest 10 articles
SELECT title, source_domain, published_date, url
FROM articles
ORDER BY published_date DESC
LIMIT 10;

-- Count articles by source
SELECT source_domain, COUNT(*) as article_count
FROM articles
GROUP BY source_domain
ORDER BY article_count DESC;
```

## Project Structure

```
german-feed-scraper/
├── app/
│   ├── config.py              # Environment configuration
│   ├── database.py            # Supabase connection
│   ├── models/
│   │   └── article.py         # Data models
│   ├── scrapers/
│   │   ├── feed_discovery.py  # Feed discovery using feedsearch.dev
│   │   └── rss_scraper.py     # RSS feed scraping
│   ├── processors/            # AI processing modules
│   │   └── ai_processor.py    # AI article analysis with Groq
│   ├── analytics/             # Statistics and analytics
│   │   └── statistics.py      # Database statistics module
│   └── utils/
│       └── logger.py          # Logging configuration
├── scripts/
│   ├── discover_feeds.py      # Script to discover feeds
│   ├── run_scraper.py         # Script to scrape articles (RSS only)
│   ├── scrape_full_content.py # Script to scrape full content
│   ├── process_articles.py    # Script to process articles with AI
│   └── show_stats.py          # Script to display statistics
├── docs/
│   └── SCRAPING_STRATEGIES.md # Detailed scraping strategy documentation
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql     # Initial database schema
│       └── 002_article_analysis.sql   # AI analysis table
├── .env                       # Your environment variables (not in git)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Target Websites

The scraper is configured to discover feeds from these German websites:

1. nachrichtenleicht.de
2. rss.dw.com
3. geo.de
4. rss.sueddeutsche.de
5. tagesschau.de
6. newsfeed.zeit.de
7. spiegel.de
8. apotheken-umschau.de
9. chefkoch.de
10. brigitte.de
11. heise.de
12. t3n.de
13. sport1.de/rss

## Troubleshooting

### Error: "Failed to connect to Supabase"

- Verify your `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Make sure you're using the `service_role` key, not the `anon` key
- Check that your Supabase project is active

### Error: "relation 'feeds' does not exist"

- Run the database migration SQL script in Supabase SQL Editor
- Verify the tables were created in Table Editor

### No feeds discovered

- Some websites may not have RSS feeds
- feedsearch.dev may not find feeds for all domains
- Check the logs for specific errors

### No articles scraped

- Make sure you ran `discover_feeds.py` first
- Check that feeds are marked as 'active' in the feeds table
- Some feeds may be temporarily unavailable

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | Your Supabase project URL | - | Yes |
| `SUPABASE_KEY` | Supabase service role key | - | Yes |
| `GROQ_API_KEY` | Groq API key for AI processing | - | For AI features |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, ERROR) | INFO | No |
| `SCRAPE_INTERVAL` | Minutes between scrapes (for future scheduling) | 60 | No |

## Scraping Strategies

The project supports multiple scraping approaches optimized for different use cases:

### 1. Parallel + Round-Robin (Default & Recommended)
- **Speed:** 10-50x faster than sequential
- **Diversity:** Guarantees coverage of all 12 domains
- **Time:** Completes 698 feeds in 30-60 minutes
- **Use case:** Production scraping, diverse datasets

### 2. Sequential
- **Speed:** Slow (12-23 hours for 698 feeds)
- **Diversity:** Poor (may only get 1-2 domains before timeout)
- **Use case:** Testing, debugging

### 3. Stratified Sampling
- **Speed:** Very fast (scrapes subset, not all feeds)
- **Diversity:** Excellent (balanced across domains)
- **Use case:** Quick testing, proof-of-concept

For detailed comparison and implementation details, see [docs/SCRAPING_STRATEGIES.md](docs/SCRAPING_STRATEGIES.md)

## Notes

- **Parallel scraper** respects rate limits with domain-based semaphores (max 3 concurrent per domain)
- **Sequential scraper** uses 1-2 second delays between feeds
- Duplicate articles are automatically prevented using URL uniqueness
- Failed feeds are automatically retried (up to 2 attempts with exponential backoff)
- All timestamps are stored in UTC
- The feedsearch.dev API is free and requires no API key

## Performance Benchmarks

Based on scraping 698 feeds across 12 German domains:

| Metric | Sequential | Parallel + Round-Robin |
|--------|-----------|------------------------|
| **Time to complete** | 12-23 hours | 30-60 minutes |
| **Speed improvement** | 1x (baseline) | 10-50x faster |
| **Domains after 100 feeds** | 1-2 domains | All 12 domains |
| **Articles per minute** | ~3-5 | ~50-150 |
| **Respectful scraping** | ✓ (1-2s delays) | ✓ (domain semaphores) |
| **Error handling** | ✓ Retries | ✓ Retries + parallel recovery |

## Future Enhancements

- Scheduled scraping with cron jobs or task scheduler
- FastAPI endpoints for querying articles
- Full-text search capabilities
- Admin dashboard for monitoring scraping progress
- Real-time updates using Supabase subscriptions
- Adaptive rate limiting based on server response times

## License

This project is provided as-is for educational and personal use.
