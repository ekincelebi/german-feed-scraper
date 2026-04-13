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

### Recommended Workflow (Most Users)

If you want the standard end-to-end pipeline (fetch -> clean -> enhance), run these in order:

```bash
# 1) Fetch full articles (yesterday's content)
venv/bin/python scripts/fetch_yesterday_articles.py

# 2) Clean content for language learners
venv/bin/python scripts/process_article_content.py --parallel --workers 10

# 3) Add learning annotations
venv/bin/python scripts/enhance_for_learning.py --parallel --workers 5
```

For a safer first run, use limits:

```bash
venv/bin/python scripts/process_article_content.py --limit 100 --parallel --workers 10
venv/bin/python scripts/enhance_for_learning.py --limit 10 --max-cost 1.0 --parallel --workers 5
```

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

### Step 2: Fetch Full Articles (Recommended)

Fetch complete article text from feeds (not just RSS summaries):

```bash
venv/bin/python scripts/fetch_yesterday_articles.py
```

This will:
- Load configured feeds from the database
- Fetch articles published yesterday
- Extract full webpage content (title, URL, body text, metadata)
- Save new records to `articles` (skips duplicates)

Common options:

```bash
# Increase parallelism
venv/bin/python scripts/fetch_yesterday_articles.py --workers 20 --max-per-domain 5

# Restrict to a single domain
venv/bin/python scripts/fetch_yesterday_articles.py --domain rss.dw.com

# Limit number of feeds (good for testing)
venv/bin/python scripts/fetch_yesterday_articles.py --limit 10

# Show all options
venv/bin/python scripts/fetch_yesterday_articles.py --help
```

### Step 3: Clean Article Content for Language Learners (Optional)

After scraping articles, clean and optimize article text for learners with `process_article_content.py` (Groq Llama 3.3 70B).

#### Get Groq API Key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up for a free account
3. Create a new API key
4. Add it to your `.env` file:
```env
GROQ_API_KEY=your-groq-api-key-here
```

#### Run Database Migrations

Before AI processing, run the migrations that create cleaned content and learning tables/views:

1. In Supabase, go to **SQL Editor**
2. Click "New query"
3. Run [supabase/migrations/003_processed_content.sql](supabase/migrations/003_processed_content.sql)
4. Run [supabase/migrations/007_simplify_processed_content.sql](supabase/migrations/007_simplify_processed_content.sql)
5. Run [supabase/migrations/008_learning_enhancements.sql](supabase/migrations/008_learning_enhancements.sql)
6. Run [supabase/migrations/009_cleanup_unused_tables.sql](supabase/migrations/009_cleanup_unused_tables.sql)
7. Run [supabase/migrations/010_recreate_learning_views.sql](supabase/migrations/010_recreate_learning_views.sql)

#### Process Articles

The content processor removes scraping noise while preserving article meaning and level:

**What Cleaning Does:**
- Removes HTML artifacts, boilerplate, and promotions
- Preserves vocabulary, grammar, and factual content
- Keeps text in German and improves readability

**Test with 100 articles (recommended first):**
```bash
python scripts/process_article_content.py --limit 100 --parallel --workers 10
```

**Process all articles:**
```bash
python scripts/process_article_content.py --parallel --workers 10
```

**Custom budget:**
```bash
# Process with $2.50 budget
python scripts/process_article_content.py --max-cost 2.50 --parallel --workers 10
```

**Cost Estimates (Groq Llama 3.3 70B):**
- Average: ~$0.0012 per article
- 100 articles: ~$0.12
- Default budget: $5.00

Expected output:
```
===============================================================================
CONTENT PROCESSOR FOR LANGUAGE LEARNING
===============================================================================
Model: Llama 3.3 70B (via Groq)
Budget: $5.00 USD
Rate limit: 0.5s between requests
Max retries: 3
Limit: 100 articles (testing mode)
===============================================================================

Processing article 1/100: ca8084fb-0357-4fcc-afb9-37c25a45b264
Processed article ca8084fb-0357-4fcc-afb9-37c25a45b264: 1300 chars, 1720 tokens, $0.0012

Progress: 10/100 (10.0%) | Cost: $0.0059 | Rate: 2.3 articles/sec | ETA: 38s
...
===============================================================================
CONTENT PROCESSING COMPLETE!
===============================================================================
✓ Successfully processed: 100
✗ Failed: 0

📊 Statistics:
  Total tokens: 123,456
  Avg tokens/article: 1,235

💰 Cost:
  Total: $0.1200
  Avg/article: $0.001200
  Remaining budget: $4.8800
===============================================================================
```

**Advanced Options:**
```bash
# Faster processing (less polite to API)
python scripts/process_article_content.py --rate-limit 0.2 --parallel --workers 10

# More retries for unstable connections
python scripts/process_article_content.py --max-retries 5 --parallel --workers 10

# See all options
python scripts/process_article_content.py --help
```

### Step 4: Enhance for Learning (Optional)

After content cleaning, enrich articles with vocabulary, grammar, and cultural annotations for learners.

#### What Learning Enhancement Adds:

✅ **Vocabulary annotations**: 10-15 key terms with context and CEFR level  
✅ **Grammar patterns**: 3-5 patterns with examples from the article  
✅ **Cultural notes**: short context explanations for German usage and institutions  
✅ **Comprehension questions**: 3-5 German questions to support active reading  
✅ **Difficulty estimation**: CEFR level + reading time estimate

**Test with 10 articles:**
```bash
python scripts/enhance_for_learning.py --limit 10 --max-cost 1.0 --parallel --workers 5
```

**Process all cleaned articles:**
```bash
python scripts/enhance_for_learning.py --parallel --workers 5
```

**Cost Estimates (Groq Llama 3.3 70B):**
- Average: ~$0.0017 per article
- 100 articles: ~$0.17
- Default budget: $5.00

Expected output:
```
===============================================================================
LEARNING ENHANCEMENT PROCESSOR
===============================================================================
Model: Llama 3.3 70B (via Groq)
Budget: $5.00 USD
Rate limit: 0.5s between requests
Max retries: 3
Limit: 100 articles (testing mode)
===============================================================================

Submitting article 1/100: Energiepreise in Deutschland...
Enhanced article ca8084fb-0357-4fcc-afb9-37c25a45b264: difficulty=B2, 12 vocab words, 2100 tokens, $0.0018

Progress: 10/100 (10.0%) | Cost: $0.0180 | Rate: 1.8 articles/sec | ETA: 0.8 min
...
===============================================================================
LEARNING ENHANCEMENT COMPLETE!
===============================================================================
✓ Successfully processed: 99
✗ Failed: 1

📊 Statistics:
  Total tokens: 170,234
  Avg tokens/article: 2,100

💰 Cost:
  Total: $0.1700
  Avg/article: $0.001700
  Remaining budget: $4.8300
===============================================================================
```

**Advanced Options:**
```bash
# Custom budget
python scripts/enhance_for_learning.py --max-cost 2.50 --parallel --workers 5

# Faster processing
python scripts/enhance_for_learning.py --rate-limit 0.05 --parallel --workers 5

# See all options
python scripts/enhance_for_learning.py --help
```

**View cleaned articles in Supabase:**
```sql
-- View cleaned content
SELECT a.title, pc.cleaned_content
FROM articles a
JOIN processed_content pc ON a.id = pc.article_id
LIMIT 5;
```

**Complete Pipeline:**
```sql
-- Join current learning pipeline tables
SELECT
    a.title,
    a.url,
    le.estimated_difficulty,
    le.vocabulary_annotations,
    le.grammar_patterns,
    pc.cleaned_content,
    le.comprehension_questions
FROM articles a
JOIN processed_content pc ON a.id = pc.article_id
JOIN learning_enhancements le ON a.id = le.article_id
WHERE le.estimated_difficulty = 'B1'
LIMIT 10;
```

### Step 5: View Statistics and Analytics

Use SQL views created by migrations for dashboard-style analytics:

```sql
-- High-level aggregate metrics
SELECT * FROM article_statistics;

-- Browse-ready list rows
SELECT * FROM article_list_view ORDER BY published_date DESC LIMIT 20;

-- Full learning payload rows
SELECT * FROM article_learning_view ORDER BY published_date DESC LIMIT 10;
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
│   ├── config/
│   │   └── feed_config.py     # Feed sources
│   ├── database.py            # Supabase connection
│   ├── settings.py            # Environment settings
│   ├── scrapers/
│   │   ├── content_extractors.py # Full-content extraction logic
│   │   └── ordering_strategy.py  # Feed ordering strategies
│   ├── processors/
│   │   ├── content_processor.py  # Content cleaning
│   │   └── learning_enhancer.py  # Learning annotations
│   └── utils/
│       └── logger.py          # Logging configuration
├── scripts/
│   ├── fetch_yesterday_articles.py # Fetch full articles from feeds
│   ├── process_article_content.py # Script to clean article content
│   └── enhance_for_learning.py    # Script to add learning annotations
├── docs/
│   └── SCRAPING_STRATEGIES.md # Detailed scraping strategy documentation
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql     # Initial database schema
│       ├── 003_processed_content.sql  # Cleaned content table
│       ├── 008_learning_enhancements.sql  # Learning enhancement table
│       ├── 009_cleanup_unused_tables.sql  # Remove deprecated analysis table/views
│       └── 010_recreate_learning_views.sql # Recreate frontend views on current schema
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
