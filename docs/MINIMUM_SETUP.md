# Minimum Project Setup

This document describes the absolute minimum project structure needed to run the two main parallel processing scripts.

## 📁 Minimum Project Structure

```
german-feed-scraper/
├── .env                          # Environment variables (required)
├── requirements.txt              # Python dependencies
├── venv/                         # Virtual environment
│
├── app/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── feed_config.py       # Feed sources configuration
│   │
│   ├── database.py              # Supabase connection
│   ├── settings.py              # App settings
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   └── content_processor.py # AI content cleaning (parallel)
│   │
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── content_extractors.py   # Full content extraction
│   │   └── ordering_strategy.py    # Round-robin ordering
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py            # Logging configuration
│
└── scripts/
    ├── fetch_yesterday_articles.py   # Parallel article fetching
    └── process_article_content.py    # Parallel content processing
```

---

## 🚀 Commands to Run

### Command 1: Fetch Yesterday's Articles
```bash
# Parallel fetching with 15 workers
source venv/bin/activate && python scripts/fetch_yesterday_articles.py --workers 15
```

**What it does:**
- Fetches all articles published yesterday from configured feeds
- Uses 15 parallel workers for speed
- Round-robin ordering for domain diversity
- Domain-based rate limiting (max 3 per domain)
- Saves articles to Supabase `articles` table

**Expected Performance:**
- ~100 articles in 25-30 seconds

---

### Command 2: Process Articles with AI
```bash
# Process 50 articles with $5 budget (parallel mode)
python scripts/process_article_content.py --limit 50 --max-cost 5.0 --rate-limit 1.0 --parallel --workers 10
```

**What it does:**
- Cleans article content using AI (Groq Llama 3.3 70B)
- Removes ads, navigation, irrelevant content
- Uses 10 parallel workers for speed
- Budget control: stops at $5.00
- Rate limit: 1.0 second between requests
- Saves cleaned content to Supabase `processed_content` table

**Expected Performance:**
- ~50 articles in 15-20 seconds
- Cost: ~$0.07 (50 articles × $0.0014)

**Note:**
- Add `--parallel --workers 10` for parallel processing (3-5x faster)
- Without it, runs sequentially (much slower)

---

## ⚙️ Configuration Requirements

### 1. Environment Variables (.env)

Create a `.env` file in the project root:

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Groq API (required for content processing)
GROQ_API_KEY=your-groq-api-key

# Optional
LOG_LEVEL=INFO
```

### 2. Python Dependencies

Install required packages:

```bash
pip install feedparser httpx beautifulsoup4 lxml groq supabase python-dotenv
```

Or use `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Required packages:**
- `feedparser` - RSS parsing
- `httpx` - HTTP requests
- `beautifulsoup4` - Content extraction
- `lxml` - HTML parsing
- `groq` - AI content processing
- `supabase` - Database client
- `python-dotenv` - Environment variables

---

## 📊 Database Requirements

Your Supabase database must have these tables:

### Articles Table
```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    theme TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    author TEXT,
    source_domain TEXT,
    source_feed TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Processed Content Table
```sql
CREATE TABLE processed_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    cleaned_content TEXT NOT NULL,
    processing_tokens INTEGER,
    processing_cost_usd DECIMAL(10, 6),
    model_used VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(article_id)
);
```

---

## 🧪 Testing the Setup

### 1. Test Database Connection
```bash
python -c "from app.database import get_db; db = get_db(); print('✓ Database connected')"
```

### 2. Test Feed Configuration
```bash
python -c "from app.config.feed_config import FEED_SOURCES; print(f'✓ {len(FEED_SOURCES)} feeds configured')"
```

### 3. Test Content Processor
```bash
python -c "from app.processors.content_processor import ContentProcessor; p = ContentProcessor(); print('✓ Content processor ready')"
```

### 4. Test with Small Batch
```bash
# Fetch just 1 article from each feed (quick test)
python scripts/fetch_yesterday_articles.py --workers 5

# Process just 5 articles (quick test)
python scripts/process_article_content.py --limit 5 --max-cost 0.1 --parallel --workers 3
```

---

## 🔍 Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the project root
cd /Users/ekin/Dev/claude/german-feed-scraper

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Database connection failed"
```bash
# Check .env file exists and has correct values
cat .env | grep SUPABASE

# Test connection
python -c "from app.database import get_db; get_db()"
```

### "GROQ_API_KEY not found"
```bash
# Check .env file
cat .env | grep GROQ_API_KEY

# Get API key from: https://console.groq.com/keys
```

### "[Errno 35] Resource temporarily unavailable"
- Reduce `--workers` count (try 10 instead of 15)
- Increase rate limit delay `--rate-limit 1.5`
- This happens when making too many concurrent connections

### Budget exceeded quickly
- Check `--max-cost` parameter
- Monitor cost: Articles cost ~$0.0014 each
- Adjust `--limit` to process fewer articles

---

## 📈 Performance Expectations

| Task | Articles | Time | Cost | Workers |
|------|----------|------|------|---------|
| **Fetch** | 100 | ~30s | Free | 15 |
| **Process** (parallel) | 100 | ~30s | $0.14 | 10 |
| **Process** (sequential) | 100 | ~150s | $0.14 | 1 |

**Daily Pipeline:**
- Fetch 100 articles: ~30 seconds
- Process 100 articles: ~30 seconds
- **Total: ~1 minute**
- **Cost: ~$0.14/day or ~$4/month**

---

## 🎯 Quick Start Workflow

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Fetch yesterday's articles (parallel)
python scripts/fetch_yesterday_articles.py --workers 15

# 3. Process fetched articles (parallel)
python scripts/process_article_content.py --limit 100 --max-cost 5.0 --rate-limit 1.0 --parallel --workers 10

# 4. Check results in Supabase
# - articles table: raw fetched articles
# - processed_content table: cleaned articles
```

---

## 💡 Tips

### Optimize Fetching Speed
- **15 workers** is optimal for most systems
- Use `--max-per-domain 3` to respect rate limits
- Round-robin ordering ensures domain diversity early

### Optimize Processing Speed
- Always use `--parallel` flag for 3-5x speedup
- **10 workers** is optimal (5-10 range works well)
- Adjust `--rate-limit` based on API limits (default: 0.5s)
- Use `--max-cost` to control budget

### Reduce Costs
- Process only new articles: use `--limit`
- Test with small batches first
- Monitor cost in real-time during processing

---

## 📚 Next Steps

1. **Run the commands** above to test your setup
2. **Check the results** in your Supabase database
3. **Adjust parameters** based on your needs (workers, budget, rate limits)
4. **Set up automation** (cron job, scheduled task) to run daily

---

**You're ready to go! 🚀**

For more detailed documentation, see:
- `docs/PROJECT_OVERVIEW.md` - Complete project documentation
- `docs/PARALLEL_PROCESSING_GUIDE.md` - Detailed parallel processing guide
- `docs/DATABASE_SCHEMA.md` - Database structure
