# Supabase Database Schema Documentation

**Project:** German Feed Scraper - Language Learning Platform
**Database:** PostgreSQL (via Supabase)
**Last Updated:** 2025-10-27

---

## Table of Contents
1. [Overview](#overview)
2. [Database Tables](#database-tables)
3. [Table Relationships](#table-relationships)
4. [Data Flow](#data-flow)
5. [Indexes](#indexes)
6. [Triggers](#triggers)

---

## Overview

The database consists of **4 main tables** that store articles and their analysis for German language learning:

```
feeds → articles → article_analysis
                 → processed_content
```

### Quick Stats
- **feeds**: 698 RSS feed sources
- **articles**: ~8,934 German articles
- **article_analysis**: AI-generated metadata (CEFR level, topics, vocabulary)
- **processed_content**: Cleaned versions optimized for learners

---

## Database Tables

### 1. `feeds` Table

**Purpose:** Store RSS feed sources for article discovery

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique feed identifier |
| `url` | TEXT | UNIQUE, NOT NULL | RSS feed URL |
| `domain` | TEXT | | Source domain (e.g., "www.spiegel.de") |
| `last_fetched` | TIMESTAMPTZ | | Last time this feed was scraped |
| `status` | TEXT | DEFAULT 'active' | 'active' or 'error' |
| `error_message` | TEXT | | Error details if status = 'error' |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | When feed was discovered |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Auto-updated on changes |

**Indexes:**
- `idx_feeds_url` on `url`
- `idx_feeds_domain` on `domain`
- `idx_feeds_status` on `status`

**Example Record:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://www.spiegel.de/schlagzeilen/index.rss",
  "domain": "www.spiegel.de",
  "last_fetched": "2025-10-27T10:30:00Z",
  "status": "active",
  "error_message": null,
  "created_at": "2025-10-15T08:00:00Z",
  "updated_at": "2025-10-27T10:30:00Z"
}
```

---

### 2. `articles` Table

**Purpose:** Store scraped article content (the core data)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique article identifier |
| `url` | TEXT | UNIQUE, NOT NULL | Article URL (prevents duplicates) |
| `title` | TEXT | NOT NULL | Article headline |
| `content` | TEXT | | Full article text (HTML-cleaned) |
| `published_date` | TIMESTAMPTZ | | When article was published |
| `author` | TEXT | | Article author (if available) |
| `source_feed` | TEXT | | Which RSS feed this came from |
| `source_domain` | TEXT | | Source domain for filtering |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | When scraped into our system |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Auto-updated on changes |

**Indexes:**
- `idx_articles_url` on `url`
- `idx_articles_published_date` on `published_date DESC`
- `idx_articles_source_domain` on `source_domain`
- `idx_articles_created_at` on `created_at DESC`

**Important Notes:**
- `content` is initially NULL (from RSS scraping)
- Full content is populated later by `scrape_full_content.py`
- Only articles with `content IS NOT NULL` are processed further

**Example Record:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "url": "https://www.spiegel.de/politik/deutschland/bundestag-neue-gesetze-a-1234567.html",
  "title": "Bundestag beschließt neue Gesetze",
  "content": "Der Deutsche Bundestag hat heute...",
  "published_date": "2025-10-25T14:30:00Z",
  "author": "Max Mustermann",
  "source_feed": "https://www.spiegel.de/schlagzeilen/index.rss",
  "source_domain": "www.spiegel.de",
  "created_at": "2025-10-25T15:00:00Z",
  "updated_at": "2025-10-25T16:45:00Z"
}
```

---

### 3. `article_analysis` Table

**Purpose:** Store AI-generated metadata for language learning

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique analysis identifier |
| `article_id` | UUID | FOREIGN KEY, UNIQUE | References `articles.id` |
| `language_level` | VARCHAR(2) | CHECK (A1/A2/B1/B2/C1/C2) | CEFR language level |
| `topics` | TEXT[] | DEFAULT '{}' | Array of topics |
| `vocabulary` | JSONB | DEFAULT '[]' | Key vocabulary with translations |
| `grammar_patterns` | TEXT[] | DEFAULT '{}' | Grammar structures found |
| `processed_at` | TIMESTAMPTZ | DEFAULT NOW() | When AI analysis ran |
| `processing_tokens` | INTEGER | | Tokens used by AI model |
| `processing_cost_usd` | DECIMAL(10,6) | | Cost in USD (~$0.0006/article) |
| `model_used` | VARCHAR(100) | | AI model version |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Auto-updated on changes |

**Foreign Key:**
- `article_id` → `articles.id` (ON DELETE CASCADE)

**Indexes:**
- `idx_article_analysis_article_id` on `article_id`
- `idx_article_analysis_language_level` on `language_level`
- `idx_article_analysis_topics` (GIN) on `topics` for array queries
- `idx_article_analysis_processed_at` on `processed_at`

**Vocabulary JSONB Structure:**
```json
[
  {
    "word": "Bundestag",
    "artikel": "der",
    "english": "German parliament",
    "plural": "Bundestage"
  },
  {
    "word": "Gesetz",
    "artikel": "das",
    "english": "law",
    "plural": "Gesetze"
  }
]
```

**Example Record:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "article_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "language_level": "B2",
  "topics": ["politics", "government", "legislation"],
  "vocabulary": [
    {
      "word": "Bundestag",
      "artikel": "der",
      "english": "German parliament",
      "plural": "Bundestage"
    },
    {
      "word": "beschließen",
      "artikel": null,
      "english": "to decide, to pass",
      "plural": null
    }
  ],
  "grammar_patterns": [
    "Passive voice: werden + past participle",
    "Present perfect tense: haben + past participle",
    "Subordinate clauses with 'dass'"
  ],
  "processed_at": "2025-10-25T17:00:00Z",
  "processing_tokens": 1234,
  "processing_cost_usd": 0.000617,
  "model_used": "llama-3.3-70b-versatile",
  "created_at": "2025-10-25T17:00:00Z",
  "updated_at": "2025-10-25T17:00:00Z"
}
```

---

### 4. `processed_content` Table

**Purpose:** Store cleaned, learner-optimized article versions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique processing identifier |
| `article_id` | UUID | FOREIGN KEY, UNIQUE | References `articles.id` |
| `original_content` | TEXT | NOT NULL | Original scraped content |
| `cleaned_content` | TEXT | NOT NULL | Cleaned version (noise removed) |
| `word_count_before` | INTEGER | | Original word count |
| `word_count_after` | INTEGER | | Cleaned word count |
| `words_removed` | INTEGER | | Noise words removed |
| `processing_tokens` | INTEGER | | Tokens used by AI model |
| `processing_cost_usd` | DECIMAL(10,6) | | Cost in USD (~$0.0012/article) |
| `model_used` | VARCHAR(100) | | AI model version |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Auto-updated on changes |

**Foreign Key:**
- `article_id` → `articles.id` (ON DELETE CASCADE)

**Indexes:**
- `idx_processed_content_article_id` on `article_id`
- `idx_processed_content_created_at` on `created_at`

**Cleaning Process:**
- Removes: HTML artifacts, navigation text, ads, author bios, promotional content
- Preserves: Main article text, original language level, meaning
- Result: Focused content for language learners

**Example Record:**
```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "article_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "original_content": "Der Deutsche Bundestag hat heute... [450 words with ads/navigation]",
  "cleaned_content": "Der Deutsche Bundestag hat heute... [280 focused words]",
  "word_count_before": 450,
  "word_count_after": 280,
  "words_removed": 170,
  "processing_tokens": 1720,
  "processing_cost_usd": 0.001234,
  "model_used": "llama-3.3-70b-versatile",
  "created_at": "2025-10-25T18:00:00Z",
  "updated_at": "2025-10-25T18:00:00Z"
}
```

---

## Table Relationships

```
┌──────────────┐
│    feeds     │
└──────────────┘
       │
       │ source_feed (TEXT, not FK)
       ↓
┌──────────────┐
│   articles   │──────┐
└──────────────┘      │
       │              │
       │ FK (1:1)     │ FK (1:1)
       ↓              ↓
┌────────────────────┐  ┌──────────────────┐
│ article_analysis   │  │ processed_content│
└────────────────────┘  └──────────────────┘
```

### Relationship Details:

1. **feeds → articles**: Soft relationship (no foreign key)
   - `articles.source_feed` stores the feed URL as TEXT
   - Allows articles to persist even if feed is deleted
   - Query: JOIN ON `articles.source_feed = feeds.url`

2. **articles → article_analysis**: One-to-One (1:1)
   - Foreign Key: `article_analysis.article_id → articles.id`
   - Cascade: DELETE article → deletes its analysis
   - Constraint: UNIQUE on `article_id`

3. **articles → processed_content**: One-to-One (1:1)
   - Foreign Key: `processed_content.article_id → articles.id`
   - Cascade: DELETE article → deletes its processed content
   - Constraint: UNIQUE on `article_id`

---

## Data Flow

### Complete Article Lifecycle:

```
1. FEED DISCOVERY
   ↓
   INSERT INTO feeds
   (698 feeds discovered from 13 German news sources)

2. RSS SCRAPING
   ↓
   INSERT INTO articles (title, url, summary)
   (content is NULL at this stage)

3. FULL CONTENT SCRAPING
   ↓
   UPDATE articles SET content = '...'
   (fetch full HTML and extract text)

4. AI ANALYSIS
   ↓
   INSERT INTO article_analysis
   (CEFR level, topics, vocabulary, grammar)

5. CONTENT CLEANING
   ↓
   INSERT INTO processed_content
   (remove noise, optimize for learners)

6. FRONTEND CONSUMPTION
   ↓
   SELECT from all tables (via views)
   (display to language learners)
```

### Entry Points (CLI Scripts):

| Script | Operation | Tables Modified |
|--------|-----------|-----------------|
| `discover_feeds.py` | Discover RSS feeds | `feeds` (INSERT) |
| `run_scraper.py` | Scrape article metadata | `articles` (INSERT) |
| `scrape_full_content.py` | Fetch full article text | `articles` (UPDATE content) |
| `process_articles.py` | AI analysis | `article_analysis` (INSERT) |
| `clean_content.py` | Content cleaning | `processed_content` (INSERT) |

---

## Indexes

### Performance Optimizations

All indexes are created for common query patterns:

**For Article Browsing:**
- `idx_articles_published_date` (DESC) - Sort by newest first
- `idx_articles_source_domain` - Filter by source
- `idx_article_analysis_language_level` - Filter by CEFR level
- `idx_article_analysis_topics` (GIN) - Filter by topics (array search)

**For Article Detail:**
- `idx_articles_url` - Lookup by URL
- `idx_article_analysis_article_id` - Join with analysis
- `idx_processed_content_article_id` - Join with cleaned content

**For Feed Management:**
- `idx_feeds_status` - Find active/error feeds
- `idx_feeds_domain` - Group by domain

### GIN Indexes (Advanced)

**What is GIN?** Generalized Inverted Index for complex data types

- `idx_article_analysis_topics` - Enables fast array queries:
  ```sql
  -- Find articles with 'politics' topic
  WHERE 'politics' = ANY(topics)
  -- Or use array contains
  WHERE topics @> ARRAY['politics']
  ```

---

## Triggers

### Auto-Update `updated_at` Timestamp

All tables have automatic `updated_at` triggers:

```sql
-- Trigger function (shared)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Applied to all tables
CREATE TRIGGER update_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feeds_updated_at
    BEFORE UPDATE ON feeds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_update_article_analysis_updated_at
    BEFORE UPDATE ON article_analysis
    FOR EACH ROW EXECUTE FUNCTION update_article_analysis_updated_at();

CREATE TRIGGER trigger_update_processed_content_updated_at
    BEFORE UPDATE ON processed_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Behavior:** Any UPDATE operation automatically sets `updated_at = NOW()`

---

## Common Queries

### Get All Fully Processed Articles

```sql
SELECT
    a.id,
    a.title,
    a.url,
    a.published_date,
    a.source_domain,
    aa.language_level,
    aa.topics,
    pc.word_count_after
FROM articles a
INNER JOIN article_analysis aa ON a.id = aa.article_id
INNER JOIN processed_content pc ON a.id = pc.article_id
WHERE a.content IS NOT NULL
ORDER BY a.published_date DESC;
```

### Filter by Language Level

```sql
SELECT *
FROM articles a
INNER JOIN article_analysis aa ON a.id = aa.article_id
WHERE aa.language_level = 'B2'
ORDER BY a.published_date DESC
LIMIT 20;
```

### Filter by Topic

```sql
SELECT *
FROM articles a
INNER JOIN article_analysis aa ON a.id = aa.article_id
WHERE 'politics' = ANY(aa.topics)
ORDER BY a.published_date DESC;
```

### Get Article with All Data

```sql
SELECT
    a.*,
    aa.language_level,
    aa.topics,
    aa.vocabulary,
    aa.grammar_patterns,
    pc.cleaned_content,
    pc.word_count_after
FROM articles a
LEFT JOIN article_analysis aa ON a.id = aa.article_id
LEFT JOIN processed_content pc ON a.id = pc.article_id
WHERE a.id = 'article-uuid-here';
```

---

## Data Integrity

### Constraints Enforced:

1. **Unique URLs:** No duplicate articles (`articles.url UNIQUE`)
2. **Unique Feeds:** No duplicate feeds (`feeds.url UNIQUE`)
3. **One Analysis per Article:** `article_analysis.article_id UNIQUE`
4. **One Cleaned Version per Article:** `processed_content.article_id UNIQUE`
5. **Valid CEFR Levels:** CHECK constraint on `language_level`
6. **Cascade Deletes:** Delete article → auto-deletes analysis + processed_content

### Referential Integrity:

- ✅ Foreign keys enforce valid `article_id` references
- ✅ `ON DELETE CASCADE` prevents orphaned records
- ✅ `NOT NULL` constraints prevent missing critical data

---

## Next Steps for Frontend

To simplify frontend queries, we'll create **database views** that denormalize this data:

1. **`article_list_view`** - Lightweight list for browsing
2. **`article_detail_view`** - Complete article data
3. **`article_statistics`** - Aggregate counts

See [SUPABASE_VIEWS.md](./SUPABASE_VIEWS.md) for view definitions.
