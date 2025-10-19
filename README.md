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

Run the enhanced web scraper to fetch complete article content using BeautifulSoup:

```bash
python scripts/scrape_full_content.py
```

This will:
- Fetch all active feeds from the database
- Parse each RSS feed
- **Visit each article URL and extract full content from the webpage**
- Clean and extract main article text using BeautifulSoup
- Save complete articles to the `articles` table (skips duplicates)

Expected output:
```
Found X active feeds to scrape
Processing feed: https://www.tagesschau.de/xml/rss2
  - Extracting full content from: Article Title
  - Saved new article: Article Title (1234 characters)
...
Total feeds processed: X
Total new articles saved: Y
Failed feeds: Z
```

**Benefits of Full Content Scraping:**
- Gets the complete article text, not just summaries
- Removes HTML tags and formatting
- Provides clean, readable content
- Better for analysis and language learning

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
│   └── utils/
│       └── logger.py          # Logging configuration
├── scripts/
│   ├── discover_feeds.py      # Script to discover feeds
│   └── run_scraper.py         # Script to scrape articles
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql  # Database schema
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
| `LOG_LEVEL` | Logging level (DEBUG, INFO, ERROR) | INFO | No |
| `SCRAPE_INTERVAL` | Minutes between scrapes (for future scheduling) | 60 | No |

## Notes

- The scraper respects rate limits with 1-second delays between feeds
- Duplicate articles are automatically prevented using URL uniqueness
- Failed feeds are marked with error status in the database
- All timestamps are stored in UTC
- The feedsearch.dev API is free and requires no API key

## Future Enhancements

- Scheduled scraping with cron jobs or task scheduler
- FastAPI endpoints for querying articles
- Full-text search capabilities
- Article content extraction (beyond RSS description)
- Admin dashboard
- Real-time updates using Supabase subscriptions

## License

This project is provided as-is for educational and personal use.
