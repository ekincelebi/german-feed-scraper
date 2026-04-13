-- Migration: Recreate frontend views after article_analysis cleanup
-- Purpose: Provide stable read models based on current tables:
--          articles + processed_content + learning_enhancements

-- Drop potentially stale views first
DROP VIEW IF EXISTS article_learning_view CASCADE;
DROP VIEW IF EXISTS article_detail_view CASCADE;
DROP VIEW IF EXISTS article_list_view CASCADE;
DROP VIEW IF EXISTS article_statistics CASCADE;

-- Lightweight list view for browse pages
CREATE OR REPLACE VIEW article_list_view AS
SELECT
    a.id,
    a.title,
    a.url,
    a.published_date,
    a.source_domain,
    a.theme,
    le.estimated_difficulty,
    le.estimated_reading_time,
    a.created_at
FROM articles a
INNER JOIN processed_content pc ON a.id = pc.article_id
INNER JOIN learning_enhancements le ON a.id = le.article_id
WHERE a.content IS NOT NULL
ORDER BY a.published_date DESC NULLS LAST, a.created_at DESC;

COMMENT ON VIEW article_list_view IS
    'Lightweight article list for frontend: article metadata + learner difficulty.';

-- Detailed article view for reading pages
CREATE OR REPLACE VIEW article_detail_view AS
SELECT
    a.id,
    a.url,
    a.title,
    a.published_date,
    a.author,
    a.source_domain,
    a.source_feed,
    a.theme,
    a.created_at,
    a.updated_at,
    pc.cleaned_content,
    le.vocabulary_annotations,
    le.grammar_patterns,
    le.cultural_notes,
    le.comprehension_questions,
    le.estimated_difficulty,
    le.estimated_reading_time,
    le.created_at AS enhanced_at
FROM articles a
INNER JOIN processed_content pc ON a.id = pc.article_id
INNER JOIN learning_enhancements le ON a.id = le.article_id
WHERE a.content IS NOT NULL;

COMMENT ON VIEW article_detail_view IS
    'Detailed article view: metadata + cleaned content + learning enhancements.';

-- Full learning view (kept for backwards compatibility with scripts/docs)
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
    'Complete learning view: article + cleaned content + educational enhancements.';

-- Aggregate statistics for dashboard usage
CREATE OR REPLACE VIEW article_statistics AS
SELECT
    COUNT(DISTINCT a.id) AS total_articles,
    COUNT(DISTINCT a.source_domain) AS total_domains,
    MIN(a.published_date) AS oldest_article,
    MAX(a.published_date) AS newest_article,
    COUNT(DISTINCT pc.article_id) AS total_cleaned_articles,
    COUNT(DISTINCT le.article_id) AS total_enhanced_articles,
    COUNT(*) FILTER (WHERE le.estimated_difficulty = 'A2') AS level_a2_count,
    COUNT(*) FILTER (WHERE le.estimated_difficulty = 'B1') AS level_b1_count,
    COUNT(*) FILTER (WHERE le.estimated_difficulty = 'B2') AS level_b2_count,
    COUNT(*) FILTER (WHERE le.estimated_difficulty = 'C1') AS level_c1_count,
    COUNT(*) FILTER (WHERE le.estimated_difficulty = 'C2') AS level_c2_count
FROM articles a
LEFT JOIN processed_content pc ON a.id = pc.article_id
LEFT JOIN learning_enhancements le ON a.id = le.article_id
WHERE a.content IS NOT NULL;

COMMENT ON VIEW article_statistics IS
    'Aggregated article statistics using cleaned/enhanced learning pipeline.';

-- Public read access for frontend clients
GRANT SELECT ON article_list_view TO anon, authenticated;
GRANT SELECT ON article_detail_view TO anon, authenticated;
GRANT SELECT ON article_learning_view TO anon, authenticated;
GRANT SELECT ON article_statistics TO anon, authenticated;
