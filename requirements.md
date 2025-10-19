# German Feed Scraper - Requirements

## Project Overview
A backend service that scrapes articles from German RSS feeds and stores them in a Supabase PostgreSQL database. Uses feedsearch.dev to discover RSS feeds from target websites.

## Technology Stack
- **Backend Framework**: Python with FastAPI (modern, async, easy to use)
- **Database**: Supabase (PostgreSQL with additional features)
- **Feed Discovery**: feedsearch.dev API
- **RSS Parsing**: feedparser library
- **HTTP Client**: httpx (async support)
- **Database Client**: supabase-py

## Target Websites for RSS Discovery
1. www.nachrichtenleicht.de
2. https://rss.dw.com
3. https://www.geo.de
4. https://rss.sueddeutsche.de
5. https://www.tagesschau.de
6. https://newsfeed.zeit.de
7. https://www.spiegel.de
8. https://www.apotheken-umschau.de
9. https://www.chefkoch.de
10. https://www.brigitte.de
11. https://www.heise.de
12. https://t3n.de
13. https://www.sport1.de/rss

## Database Schema

### Articles Table
- `id` (UUID, Primary Key, Default: uuid_generate_v4())
- `url` (TEXT, Unique, Not Null) - Article URL
- `title` (TEXT, Not Null) - Article title
- `content` (TEXT) - Article content/description
- `published_date` (TIMESTAMPTZ) - Publication date
- `author` (TEXT) - Article author (if available)
- `source_feed` (TEXT) - Origin RSS feed URL
- `source_domain` (TEXT) - Domain of the source
- `created_at` (TIMESTAMPTZ, Default: now()) - When scraped
- `updated_at` (TIMESTAMPTZ, Default: now()) - Last update

### Feeds Table
- `id` (UUID, Primary Key, Default: uuid_generate_v4())
- `url` (TEXT, Unique, Not Null) - Feed URL
- `domain` (TEXT) - Source domain
- `last_fetched` (TIMESTAMPTZ) - Last successful fetch
- `status` (TEXT) - active/inactive/error
- `error_message` (TEXT) - Last error if any
- `created_at` (TIMESTAMPTZ, Default: now())
- `updated_at` (TIMESTAMPTZ, Default: now())

## Core Features

### 1. RSS Feed Discovery using feedsearch.dev
- Use feedsearch.dev API (https://feedsearch.dev/api/v1/search?url={domain}) to discover RSS feeds
- Query each target website to find available RSS feeds
- Store discovered feeds in the Supabase database
- Handle cases where multiple feeds are found per domain

### 2. Article Scraping
- Fetch articles from all discovered RSS feeds
- Parse article metadata (title, URL, content, date, author)
- Handle duplicate articles (check by URL)
- Support incremental updates

### 3. Data Storage
- Store articles in Supabase PostgreSQL with proper indexing
- Prevent duplicate entries using URL as unique constraint
- Track scraping history and errors

### 4. API Endpoints (Optional for v1)
- GET /articles - List articles with pagination
- GET /articles/{id} - Get specific article
- POST /scrape - Trigger manual scrape
- GET /feeds - List configured feeds
- GET /health - Health check

## Technical Requirements

### Supabase Setup
- Supabase project with PostgreSQL database
- Connection via Supabase client library
- Environment variables for Supabase URL and keys
- Database migrations using SQL scripts

### feedsearch.dev Integration
- API endpoint: `https://feedsearch.dev/api/v1/search?url={domain}`
- No API key required (public API)
- Returns JSON with discovered feeds
- Handle API rate limits and errors gracefully

### Error Handling
- Graceful handling of feed fetch failures
- Graceful handling of feedsearch.dev API failures
- Retry logic with exponential backoff
- Logging of all errors and scraping activities

### Configuration
- Environment-based configuration
- Configurable scrape intervals
- Maximum article age to fetch
- Connection pool settings

## Project Structure
```
german-feed-scraper/
├── requirements.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── article.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── feed_discovery.py  # Uses feedsearch.dev
│   │   └── rss_scraper.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
└── scripts/
    ├── discover_feeds.py  # Initial feed discovery
    └── run_scraper.py     # Scrape articles from feeds
```

## Environment Variables
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase service role key (for backend)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)
- `SCRAPE_INTERVAL` - Minutes between scrapes (optional)

## Workflow
1. **Feed Discovery Phase**
   - Query feedsearch.dev for each target website
   - Parse response to extract RSS feed URLs
   - Store feeds in Supabase `feeds` table

2. **Article Scraping Phase**
   - Fetch all active feeds from database
   - Parse each feed using feedparser
   - Extract article data
   - Insert/update articles in database (upsert by URL)

## Success Criteria
1. Successfully discover RSS feeds from all provided websites using feedsearch.dev
2. Scrape and store articles with all required fields
3. Supabase PostgreSQL database properly configured
4. No duplicate articles in database
5. Proper error handling and logging
6. Clean, maintainable code structure

## Advantages of Using feedsearch.dev
- Automatic feed discovery without manual configuration
- Finds multiple feeds per domain if available
- No need to manually maintain feed URLs
- Supports various feed formats (RSS, Atom, JSON Feed)

## Advantages of Using Supabase
- No Docker setup needed for database
- Built-in authentication (if needed later)
- Real-time subscriptions capability
- Automatic API generation
- Built-in admin dashboard
- Easy backups and scaling
- Free tier available for development

## Future Enhancements (Out of Scope for v1)
- Scheduled scraping with cron/celery
- Full-text search capabilities
- Article content extraction (beyond RSS description)
- RESTful API for querying articles
- Admin dashboard using Supabase Auth
- Article categorization/tagging
- Support for multiple languages
- Real-time updates using Supabase subscriptions
