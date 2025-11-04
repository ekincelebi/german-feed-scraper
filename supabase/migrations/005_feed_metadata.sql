-- Add metadata columns to feeds table for strategy support

-- Add new columns for feed configuration
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS theme TEXT;
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS strategy TEXT DEFAULT 'full_archive';
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 2;

-- Add comments for documentation
COMMENT ON COLUMN feeds.category IS 'Feed category: learning, news_simple, news_mainstream, lifestyle, specialized';
COMMENT ON COLUMN feeds.theme IS 'Feed theme: vocabulary, idioms, audio_transcripts, general_news, etc.';
COMMENT ON COLUMN feeds.strategy IS 'Fetch strategy: full_archive or daily_updates';
COMMENT ON COLUMN feeds.description IS 'Human-readable description of the feed';
COMMENT ON COLUMN feeds.priority IS 'Priority level: 1=High, 2=Medium, 3=Low';

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS idx_feeds_category ON feeds(category);
CREATE INDEX IF NOT EXISTS idx_feeds_strategy ON feeds(strategy);
CREATE INDEX IF NOT EXISTS idx_feeds_priority ON feeds(priority);

-- Add check constraint for strategy values
ALTER TABLE feeds ADD CONSTRAINT check_strategy
    CHECK (strategy IN ('full_archive', 'daily_updates'));

-- Add check constraint for priority values
ALTER TABLE feeds ADD CONSTRAINT check_priority
    CHECK (priority >= 1 AND priority <= 3);
