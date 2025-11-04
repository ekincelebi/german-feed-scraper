# German Feed Scraper - Project Overview

A streamlined Python project for scraping, processing, and serving German language learning content from RSS feeds.

## 🎯 Project Purpose

This system collects German articles from news and learning sites, processes them with AI to make them suitable for language learners, and serves them via a Next.js frontend with Supabase backend.

---

## 📊 Current Statistics

- **13 Active Feeds** across 8 domains
- **Content Types**: Idioms, recipes, health, science, news, podcasts
- **Processing**: Parallel workers for 3-5x speedup
- **Cost**: ~$0.0014 per article for AI processing

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RSS FEEDS (13)                         │
│  DW Learn German, Chefkoch, Apotheken Umschau, etc.       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Parallel Fetch (15 workers)
                     │ Round-robin ordering
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SUPABASE DATABASE (PostgreSQL)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   articles   │  │article_analysis│  │processed_    │     │
│  │              │  │                │  │  content     │     │
│  │ • id         │  │ • article_id   │  │ • article_id │     │
│  │ • url        │  │ • language_lvl │  │ • cleaned_   │     │
│  │ • title      │  │ • topics       │  │   content    │     │
│  │ • content    │  │ • vocabulary   │  │ • tokens     │     │
│  │ • theme      │  │ • grammar      │  │ • cost       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Parallel Process (10 workers)
                     │ AI Content Cleaning (Groq Llama 3.3)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                         │
│  • Browse articles by level (A1-C2)                        │
│  • Filter by topic/theme/domain                            │
│  • Read cleaned content                                     │
│  • View vocabulary & grammar                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY

# Populate feeds table
python scripts/populate_feeds.py
```

### 2. Daily Pipeline

```bash
# Fetch yesterday's articles (parallel, ~30 seconds for 100 articles)
python scripts/fetch_yesterday_articles.py --workers 15 --max-per-domain 3

# Process content with AI (parallel, ~30 seconds for 100 articles)
python scripts/process_article_content.py --parallel --workers 10 --max-cost 5.0 --rate-limit 0.1

# View statistics
python scripts/show_stats.py
```

### 3. Testing New Feeds

```bash
# Edit app/config/feed_config.py (uncomment feeds)

# Test fetch
python scripts/fetch_latest_full_content.py
```

---

## 📁 Project Structure

```
german-feed-scraper/
├── app/
│   ├── config/
│   │   └── feed_config.py          # Feed sources (single source of truth)
│   ├── database.py                  # Supabase connection
│   ├── processors/
│   │   └── content_processor.py    # AI content cleaning (parallel)
│   ├── scrapers/
│   │   ├── parallel_scraper.py     # Parallel fetching base class
│   │   ├── ordering_strategy.py    # Round-robin ordering
│   │   └── content_extractor.py    # Full content extraction
│   └── utils/
│       └── logger.py                # Logging configuration
│
├── scripts/                         # CLI scripts
│   ├── fetch_yesterday_articles.py # MAIN: Parallel article fetching
│   ├── process_article_content.py  # MAIN: Parallel content processing
│   ├── fetch_latest_full_content.py# Testing: Latest from each feed
│   ├── populate_feeds.py           # Setup: Initialize feeds table
│   ├── show_stats.py               # Utility: View statistics
│   └── discover_feeds.py           # Utility: Find new feeds
│
├── supabase/
│   └── migrations/                 # Database schema
│       ├── 001_create_tables.sql
│       ├── 002_add_feeds_table.sql
│       ├── 003_processed_content.sql
│       ├── 004_frontend_views_and_rls.sql
│       ├── 005_article_analysis.sql
│       ├── 006_add_theme_to_articles.sql
│       └── 007_simplify_processed_content.sql
│
└── docs/                           # Documentation
    ├── PROJECT_OVERVIEW.md         # This file
    ├── PARALLEL_PROCESSING_GUIDE.md# Detailed parallel processing docs
    ├── FILE_STRUCTURE_CLEANUP.md   # Cleanup rationale
    ├── API_ROUTES_REFERENCE.md     # Frontend API reference
    ├── DATABASE_SCHEMA.md          # Database documentation
    └── FRONTEND_SPECIFICATION.md   # Frontend requirements
```

---

## 🔑 Key Features

### 1. Parallel Processing

**Article Fetching:**
- 15 workers processing feeds concurrently
- Round-robin domain ordering for diversity
- Domain-based rate limiting (max 3 per domain)
- **Performance**: 100 articles in 25 seconds (3x faster)

**Content Processing:**
- 5-10 workers processing articles concurrently
- Thread-safe statistics tracking
- Budget control (stops at cost limit)
- **Performance**: 100 articles in 30 seconds (3-5x faster)

### 2. Feed Configuration

Single source of truth in `app/config/feed_config.py`:

```python
FeedSource(
    url="https://rss.dw.com/xml/DKpodcast_dassagtmanso_de",
    domain="rss.dw.com",
    category="learning",
    theme="idioms",
    strategy="full_archive",
    description="Das sagt man so! - German idioms"
)
```

All scripts read from this config (not database).

### 3. Content Extraction

**Multi-strategy approach:**
1. Try domain-specific selectors (maintained per source)
2. Try common article selectors (`.article-content`, `article`, etc.)
3. Fallback to RSS content if page is JS-rendered
4. Clean HTML, remove ads/navigation/scripts

**Result**: High-quality, learner-friendly content

### 4. AI Processing

**Content Cleaning (Groq Llama 3.3 70B):**
- Removes ads, navigation, author bios
- Removes off-topic content
- Fixes formatting issues
- Preserves original language level
- **Cost**: ~$0.0014 per article

**No Analysis Dependency:**
- Previously required `article_analysis` table
- Now works directly with articles table
- Uses theme as topic, defaults to B1 level
- Simpler, faster, more maintainable

### 5. Database Views

**Frontend-optimized views:**
- `article_list_view` - Lightweight for browsing
- `article_detail_view` - Complete data for reading
- `article_statistics` - Aggregate counts by level/domain

**Row Level Security:**
- Public read access (anon/authenticated)
- Write access restricted to service_role
- Frontend can only read, scripts can write

---

## 📋 Database Schema

### Articles Table

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,                -- Full original content
    theme TEXT,                  -- From feed source
    published_date TIMESTAMP,
    author TEXT,
    source_domain TEXT,
    source_feed TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Processed Content Table

```sql
CREATE TABLE processed_content (
    id UUID PRIMARY KEY,
    article_id UUID REFERENCES articles(id),
    cleaned_content TEXT NOT NULL,  -- AI-cleaned content
    processing_tokens INTEGER,
    processing_cost_usd DECIMAL(10, 6),
    model_used VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Article Analysis Table (Optional)

```sql
CREATE TABLE article_analysis (
    id UUID PRIMARY KEY,
    article_id UUID REFERENCES articles(id),
    language_level VARCHAR(2),      -- A1, A2, B1, B2, C1, C2
    topics TEXT[],                  -- Array of topics
    vocabulary JSONB,               -- [{word, level, definition}]
    grammar_patterns TEXT[],        -- Array of grammar patterns
    processed_at TIMESTAMP
);
```

---

## 🎨 Frontend Integration

### Supabase Views (Read-Only)

```javascript
// Browse articles (list view)
const { data } = await supabase
  .from('article_list_view')
  .select('*')
  .eq('language_level', 'B1')
  .contains('topics', ['idioms'])
  .order('published_date', { ascending: false })
  .limit(20);

// Read article (detail view)
const { data } = await supabase
  .from('article_detail_view')
  .select('*')
  .eq('id', articleId)
  .single();

// Get statistics
const { data } = await supabase
  .from('article_statistics')
  .select('*')
  .single();
```

### Helper Functions

```javascript
// Get unique topics for filter dropdown
const { data } = await supabase.rpc('get_unique_topics');

// Get unique domains for filter dropdown
const { data } = await supabase.rpc('get_unique_domains');
```

---

## 🧪 Testing

### Test Feed Configuration

```bash
# Fetch latest from each configured feed
python scripts/fetch_latest_full_content.py
```

### Test Content Processing

```bash
# Process 10 articles with $1 budget
python scripts/process_article_content.py --limit 10 --max-cost 1.0
```

### Test Parallel Performance

```bash
# Parallel vs Sequential comparison
python scripts/process_article_content.py --limit 50 --parallel --workers 10
python scripts/process_article_content.py --limit 50  # Sequential
```

---

## 💡 Performance Tips

### Article Fetching

**Optimal Settings:**
```bash
--workers 15          # Sweet spot (10-15)
--max-per-domain 3    # Respectful rate limiting
```

**Troubleshooting:**
- "[Errno 35] Resource temporarily unavailable" → Reduce workers or increase rate limit
- Too slow → Increase workers (test incrementally)
- Feed failures → Check domain-specific selectors

### Content Processing

**Optimal Settings:**
```bash
--parallel --workers 10    # Sweet spot (5-10)
--rate-limit 0.1           # Fast, monitor for rate limits
--max-cost 5.0             # Budget control
```

**Troubleshooting:**
- Slow processing → Enable parallel mode
- Budget exceeded → Lower max-cost or increase budget
- API errors → Increase rate-limit delay

---

## 📊 Cost Analysis

### Content Processing Costs

| Articles | Sequential Time | Parallel Time | Cost | Cost/Article |
|----------|----------------|---------------|------|--------------|
| 10 | 15s | 5s | $0.014 | $0.0014 |
| 100 | 150s | 30s | $0.14 | $0.0014 |
| 1,000 | 1,500s (25m) | 300s (5m) | $1.40 | $0.0014 |

**Monthly Estimate:**
- 100 articles/day × 30 days = 3,000 articles
- Cost: ~$4.20/month
- Time: ~15 minutes/day (parallel)

---

## 🔄 Migration History

1. **001**: Initial tables (articles, feeds)
2. **002**: Feeds table structure
3. **003**: Processed content table
4. **004**: Frontend views and RLS
5. **005**: Article analysis table
6. **006**: Add theme field to articles
7. **007**: Simplify processed_content (remove word counts)

---

## 🚧 Recent Changes (Nov 2025)

### Completed

✅ Parallel processing for article fetching (3x speedup)
✅ Parallel processing for content processing (3-5x speedup)
✅ Removed analysis dependency from content processing
✅ Added theme field to articles
✅ Simplified processed_content schema
✅ Updated all views to include theme
✅ Streamlined file structure (removed 6 redundant scripts)
✅ Comprehensive documentation created

### File Structure Changes

**Removed (Redundant):**
- `scripts/fetch_latest_only.py`
- `scripts/scrape_full_content.py`
- `scripts/run_scraper.py`
- `scripts/run_strategy_scraper.py`
- `scripts/clean_content.py`
- `scripts/process_articles.py`

**Kept (Essential):**
- `scripts/fetch_yesterday_articles.py` (main fetching)
- `scripts/process_article_content.py` (main processing)
- `scripts/fetch_latest_full_content.py` (testing)
- `scripts/populate_feeds.py` (setup)
- `scripts/show_stats.py` (monitoring)
- `scripts/discover_feeds.py` (discovery)

---

## 📚 Documentation

- **[PARALLEL_PROCESSING_GUIDE.md](./PARALLEL_PROCESSING_GUIDE.md)** - Detailed parallel processing documentation
- **[FILE_STRUCTURE_CLEANUP.md](./FILE_STRUCTURE_CLEANUP.md)** - Cleanup rationale and comparison
- **[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)** - Database structure and relationships
- **[API_ROUTES_REFERENCE.md](./API_ROUTES_REFERENCE.md)** - Frontend API reference
- **[FRONTEND_SPECIFICATION.md](./FRONTEND_SPECIFICATION.md)** - Frontend requirements

---

## 🎓 Learning Resources

### Understanding the Codebase

1. **Start here**: Read this PROJECT_OVERVIEW.md
2. **Parallel processing**: Read PARALLEL_PROCESSING_GUIDE.md
3. **Run a test**: `python scripts/fetch_latest_full_content.py`
4. **Check the code**: `app/processors/content_processor.py` for parallel processing example

### Key Concepts

- **Round-robin ordering**: Ensures domain diversity early in scraping
- **Domain-based rate limiting**: Prevents overwhelming single sources
- **Thread safety**: Using Lock for shared statistics
- **Budget control**: Stop processing when cost limit reached
- **as_completed()**: Process results as they finish (not in order)

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Groq API (required for content processing)
GROQ_API_KEY=your-groq-api-key

# Optional
LOG_LEVEL=INFO
```

### Feed Configuration (app/config/feed_config.py)

```python
FEED_SOURCES: List[FeedSource] = [
    FeedSource(
        url="...",
        domain="...",
        category="...",
        theme="...",
        strategy="full_archive",  # or "daily_updates"
        description="...",
        priority=2
    ),
    # ... more feeds
]
```

---

## 🤝 Contributing

### Adding New Feeds

1. Edit `app/config/feed_config.py`
2. Add new FeedSource with metadata
3. Test: `python scripts/fetch_latest_full_content.py`
4. Add domain-specific selector if needed in `content_extractor.py`

### Improving Performance

1. Adjust worker counts in scripts
2. Monitor statistics with `show_stats.py`
3. Check for rate limiting errors
4. Balance speed vs. respectful scraping

---

## 📞 Support

For issues or questions:
1. Check documentation in `docs/` folder
2. Review script help: `python scripts/xxx.py --help`
3. Check logs for errors
4. Verify environment variables are set

---

## 📈 Future Improvements

### Potential Enhancements

- [ ] Add more German learning feeds
- [ ] Implement article difficulty scoring
- [ ] Add user authentication and favorites
- [ ] Implement vocabulary flashcard generation
- [ ] Add audio pronunciation support
- [ ] Create mobile app

### Performance Optimizations

- [ ] Implement connection pooling for database
- [ ] Add caching layer (Redis)
- [ ] Optimize database queries with better indexes
- [ ] Implement incremental content processing

---

## 🏁 Success Metrics

**Current Performance:**
- ✅ Fetching: 100 articles in 25 seconds
- ✅ Processing: 100 articles in 30 seconds
- ✅ Total pipeline: < 1 minute for 100 articles
- ✅ Cost: $0.0014 per article
- ✅ Success rate: >95% for fetching

**Goals Achieved:**
- ✅ 3-5x speedup through parallel processing
- ✅ Simplified codebase (6 fewer scripts)
- ✅ Clear documentation
- ✅ Maintainable architecture
- ✅ Cost-effective AI processing

---

*Last updated: November 4, 2025*
