-- Migration: Article Analysis Table
-- Description: Stores AI-generated analysis for language learning features
-- Created: 2025-10-19

-- Create article_analysis table
CREATE TABLE IF NOT EXISTS article_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

    -- Language Level (CEFR)
    language_level VARCHAR(2) CHECK (language_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),

    -- Topic Classification
    topics TEXT[] NOT NULL DEFAULT '{}',

    -- Vocabulary (JSONB array of objects with word, artikel, english, plural)
    vocabulary JSONB NOT NULL DEFAULT '[]',

    -- Grammar Patterns (brief explanations)
    grammar_patterns TEXT[] NOT NULL DEFAULT '{}',

    -- Processing metadata
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_tokens INTEGER,
    processing_cost_usd DECIMAL(10, 6),
    model_used VARCHAR(100),

    -- Constraints
    UNIQUE(article_id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_article_analysis_article_id ON article_analysis(article_id);
CREATE INDEX idx_article_analysis_language_level ON article_analysis(language_level);
CREATE INDEX idx_article_analysis_topics ON article_analysis USING GIN(topics);
CREATE INDEX idx_article_analysis_processed_at ON article_analysis(processed_at);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_article_analysis_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_article_analysis_updated_at
    BEFORE UPDATE ON article_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_article_analysis_updated_at();

-- Add comments for documentation
COMMENT ON TABLE article_analysis IS 'AI-generated analysis of articles for language learning';
COMMENT ON COLUMN article_analysis.language_level IS 'CEFR language level (A1-C2)';
COMMENT ON COLUMN article_analysis.topics IS 'Array of topic classifications';
COMMENT ON COLUMN article_analysis.vocabulary IS 'JSONB array with word, artikel, english, plural fields';
COMMENT ON COLUMN article_analysis.grammar_patterns IS 'Array of brief grammar pattern explanations';
COMMENT ON COLUMN article_analysis.processing_tokens IS 'Number of tokens used for processing';
COMMENT ON COLUMN article_analysis.processing_cost_usd IS 'Cost in USD for processing this article';
