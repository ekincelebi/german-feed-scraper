-- Migration: Processed Content Table
-- Description: Stores cleaned and optimized article content for language learners
-- Created: 2025-10-19

-- Create processed_content table
CREATE TABLE IF NOT EXISTS processed_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

    -- Content versions
    original_content TEXT NOT NULL,
    cleaned_content TEXT NOT NULL,

    -- Processing metadata
    word_count_before INTEGER,
    word_count_after INTEGER,
    words_removed INTEGER,
    processing_tokens INTEGER,
    processing_cost_usd DECIMAL(10, 6),
    model_used VARCHAR(100),

    -- Constraints
    UNIQUE(article_id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_processed_content_article_id ON processed_content(article_id);
CREATE INDEX idx_processed_content_created_at ON processed_content(created_at);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER trigger_update_processed_content_updated_at
    BEFORE UPDATE ON processed_content
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE processed_content IS 'Cleaned and optimized article content for language learners';
COMMENT ON COLUMN processed_content.original_content IS 'Original scraped article content';
COMMENT ON COLUMN processed_content.cleaned_content IS 'Cleaned content with noise removed, focused on main topics';
COMMENT ON COLUMN processed_content.word_count_before IS 'Word count before cleaning';
COMMENT ON COLUMN processed_content.word_count_after IS 'Word count after cleaning';
COMMENT ON COLUMN processed_content.words_removed IS 'Number of words removed during cleaning';
COMMENT ON COLUMN processed_content.processing_tokens IS 'Number of tokens used for processing';
COMMENT ON COLUMN processed_content.processing_cost_usd IS 'Cost in USD for processing this article';
