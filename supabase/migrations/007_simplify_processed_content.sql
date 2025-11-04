-- Simplify processed_content table
-- Remove original_content, word_count_before, word_count_after, words_removed
-- Keep only cleaned_content and processing metadata

-- Step 1: Drop views that depend on the columns
DROP VIEW IF EXISTS article_list_view CASCADE;
DROP VIEW IF EXISTS article_detail_view CASCADE;
DROP VIEW IF EXISTS article_statistics CASCADE;

-- Step 2: Drop the columns
ALTER TABLE processed_content
DROP COLUMN IF EXISTS original_content,
DROP COLUMN IF EXISTS word_count_before,
DROP COLUMN IF EXISTS word_count_after,
DROP COLUMN IF EXISTS words_removed;

-- Step 3: Recreate article_list_view (without word_count_after)
CREATE OR REPLACE VIEW article_list_view AS
SELECT
    -- From articles table
    a.id,
    a.title,
    a.url,
    a.published_date,
    a.source_domain,
    a.theme,
    a.created_at,

    -- From article_analysis table
    aa.language_level,
    aa.topics

FROM articles a
LEFT JOIN article_analysis aa ON a.id = aa.article_id
LEFT JOIN processed_content pc ON a.id = pc.article_id

WHERE
    a.content IS NOT NULL           -- Only articles with full content
    AND aa.article_id IS NOT NULL   -- Only analyzed articles
    AND pc.article_id IS NOT NULL   -- Only cleaned articles

ORDER BY a.published_date DESC;

COMMENT ON VIEW article_list_view IS 'Lightweight article data for browse/list views in frontend';

-- Step 4: Recreate article_detail_view (without word count fields)
CREATE OR REPLACE VIEW article_detail_view AS
SELECT
    -- Article basics
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

    -- Analysis data
    aa.language_level,
    aa.topics,
    aa.vocabulary,
    aa.grammar_patterns,
    aa.processed_at as analyzed_at,

    -- Content data (ONLY cleaned)
    pc.cleaned_content

FROM articles a
INNER JOIN article_analysis aa ON a.id = aa.article_id
INNER JOIN processed_content pc ON a.id = pc.article_id

WHERE a.content IS NOT NULL;

COMMENT ON VIEW article_detail_view IS 'Complete article data for detail/reading views in frontend';

-- Step 5: Recreate article_statistics (without word count stats)
CREATE OR REPLACE VIEW article_statistics AS
SELECT
    COUNT(DISTINCT a.id) as total_articles,
    COUNT(DISTINCT a.source_domain) as total_domains,
    MIN(a.published_date) as oldest_article,
    MAX(a.published_date) as newest_article,

    -- Count by language level
    COUNT(*) FILTER (WHERE aa.language_level = 'A1') as level_a1_count,
    COUNT(*) FILTER (WHERE aa.language_level = 'A2') as level_a2_count,
    COUNT(*) FILTER (WHERE aa.language_level = 'B1') as level_b1_count,
    COUNT(*) FILTER (WHERE aa.language_level = 'B2') as level_b2_count,
    COUNT(*) FILTER (WHERE aa.language_level = 'C1') as level_c1_count,
    COUNT(*) FILTER (WHERE aa.language_level = 'C2') as level_c2_count

FROM articles a
LEFT JOIN article_analysis aa ON a.id = aa.article_id
LEFT JOIN processed_content pc ON a.id = pc.article_id

WHERE
    a.content IS NOT NULL
    AND aa.article_id IS NOT NULL
    AND pc.article_id IS NOT NULL;

COMMENT ON VIEW article_statistics IS 'Aggregate statistics for dashboard/analytics in frontend';

-- Step 6: Grant permissions on recreated views
GRANT SELECT ON article_list_view TO anon, authenticated;
GRANT SELECT ON article_detail_view TO anon, authenticated;
GRANT SELECT ON article_statistics TO anon, authenticated;

-- Update comments
COMMENT ON TABLE processed_content IS 'AI-cleaned and optimized article content for language learners';
COMMENT ON COLUMN processed_content.cleaned_content IS 'AI-cleaned content optimized for language learning, removing ads, navigation, and irrelevant content';
