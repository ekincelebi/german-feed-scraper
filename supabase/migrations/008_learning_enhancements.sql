-- Migration: Add learning_enhancements table for B1-B2 German learners
-- Purpose: Store educational annotations for articles without modifying original text

-- Create learning_enhancements table
CREATE TABLE IF NOT EXISTS learning_enhancements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,

    -- Vocabulary support (10-15 B1-B2 words with context)
    vocabulary_annotations JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Key phrases for learning
    key_phrases TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Grammar patterns (3-5 patterns with examples)
    grammar_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Cultural context (2-3 insights)
    cultural_notes TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Comprehension questions (3-5 open-ended)
    comprehension_questions JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Discussion prompts (optional)
    discussion_prompts TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Metadata
    estimated_difficulty VARCHAR(10) CHECK (estimated_difficulty IN ('A2', 'B1', 'B2', 'C1', 'C2')),
    estimated_reading_time INTEGER,  -- in minutes

    -- Processing metadata
    processing_tokens INTEGER,
    processing_cost_usd DECIMAL(10, 6),
    model_used VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one enhancement per article
    UNIQUE(article_id)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_learning_enhancements_article_id
    ON learning_enhancements(article_id);

CREATE INDEX IF NOT EXISTS idx_learning_enhancements_difficulty
    ON learning_enhancements(estimated_difficulty);

CREATE INDEX IF NOT EXISTS idx_learning_enhancements_created_at
    ON learning_enhancements(created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE learning_enhancements IS
    'Educational annotations for articles: vocabulary, grammar, cultural notes for B1-B2 German learners';

COMMENT ON COLUMN learning_enhancements.vocabulary_annotations IS
    'Array of objects: {word, article (der/die/das), plural, context, english_translation, german_explanation, cefr_level}';

COMMENT ON COLUMN learning_enhancements.grammar_patterns IS
    'Array of objects: {pattern, example, explanation}';

COMMENT ON COLUMN learning_enhancements.comprehension_questions IS
    'Array of strings: Open-ended questions in German';

COMMENT ON COLUMN learning_enhancements.estimated_difficulty IS
    'CEFR level: A2, B1, B2, C1, or C2';

COMMENT ON COLUMN learning_enhancements.estimated_reading_time IS
    'Estimated reading time in minutes for B1-B2 learners';

-- Create view for frontend consumption
CREATE OR REPLACE VIEW article_learning_view AS
SELECT
    a.id AS article_id,
    a.url,
    a.title,
    a.published_date,
    a.author,
    a.source_domain,
    a.theme,
    pc.cleaned_content,
    le.vocabulary_annotations,
    le.key_phrases,
    le.grammar_patterns,
    le.cultural_notes,
    le.comprehension_questions,
    le.discussion_prompts,
    le.estimated_difficulty,
    le.estimated_reading_time,
    a.created_at
FROM articles a
INNER JOIN processed_content pc ON a.id = pc.article_id
INNER JOIN learning_enhancements le ON a.id = le.article_id
WHERE a.content IS NOT NULL;

COMMENT ON VIEW article_learning_view IS
    'Complete learning view: article + cleaned content + educational enhancements';

-- Grant permissions (adjust based on your RLS policies)
-- For public read access (anonymous and authenticated users)
GRANT SELECT ON learning_enhancements TO anon, authenticated;
GRANT SELECT ON article_learning_view TO anon, authenticated;

-- For service role (full access for scripts)
GRANT ALL ON learning_enhancements TO service_role;
