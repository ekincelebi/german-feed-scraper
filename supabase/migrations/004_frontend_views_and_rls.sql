-- ============================================================================
-- Migration: Frontend Views and RLS Policies
-- Description: Create views and security policies for Next.js frontend
-- Created: 2025-10-27
-- ============================================================================

-- ============================================================================
-- SECTION 1: CREATE VIEWS FOR FRONTEND
-- ============================================================================

-- View 1: article_list_view
-- Purpose: Lightweight view for browsing articles (list/grid view)
-- Returns: Minimal data for fast loading and filtering
CREATE OR REPLACE VIEW article_list_view AS
SELECT
    -- From articles table
    a.id,
    a.title,
    a.url,
    a.published_date,
    a.source_domain,
    a.created_at,

    -- From article_analysis table
    aa.language_level,
    aa.topics,

    -- From processed_content table
    pc.word_count_after

FROM articles a
LEFT JOIN article_analysis aa ON a.id = aa.article_id
LEFT JOIN processed_content pc ON a.id = pc.article_id

WHERE
    a.content IS NOT NULL           -- Only articles with full content
    AND aa.article_id IS NOT NULL   -- Only analyzed articles
    AND pc.article_id IS NOT NULL   -- Only cleaned articles

ORDER BY a.published_date DESC;

COMMENT ON VIEW article_list_view IS 'Lightweight article data for browse/list views in frontend';


-- View 2: article_detail_view
-- Purpose: Complete article data for reading view
-- Returns: All content, vocabulary, grammar patterns
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
    a.created_at,
    a.updated_at,

    -- Analysis data
    aa.language_level,
    aa.topics,
    aa.vocabulary,              -- JSONB array of vocabulary objects
    aa.grammar_patterns,        -- Text array of grammar patterns
    aa.processed_at as analyzed_at,

    -- Content data (ONLY cleaned, not original)
    pc.cleaned_content,         -- The cleaned article text for learners
    pc.word_count_after,
    pc.word_count_before,
    pc.words_removed

FROM articles a
INNER JOIN article_analysis aa ON a.id = aa.article_id
INNER JOIN processed_content pc ON a.id = pc.article_id

WHERE a.content IS NOT NULL;

COMMENT ON VIEW article_detail_view IS 'Complete article data for detail/reading views in frontend';


-- View 3: article_statistics
-- Purpose: Aggregate statistics for dashboard/filters
-- Returns: Counts by level, totals, averages
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
    COUNT(*) FILTER (WHERE aa.language_level = 'C2') as level_c2_count,

    -- Content statistics
    AVG(pc.word_count_after)::INTEGER as avg_word_count,
    MIN(pc.word_count_after) as min_word_count,
    MAX(pc.word_count_after) as max_word_count

FROM articles a
LEFT JOIN article_analysis aa ON a.id = aa.article_id
LEFT JOIN processed_content pc ON a.id = pc.article_id

WHERE
    a.content IS NOT NULL
    AND aa.article_id IS NOT NULL
    AND pc.article_id IS NOT NULL;

COMMENT ON VIEW article_statistics IS 'Aggregate statistics for dashboard/analytics in frontend';


-- ============================================================================
-- SECTION 2: CREATE HELPER FUNCTIONS
-- ============================================================================

-- Function: get_unique_topics
-- Purpose: Get all unique topics across all articles for filter UI
CREATE OR REPLACE FUNCTION get_unique_topics()
RETURNS TABLE(topic TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        UNNEST(aa.topics) as topic,
        COUNT(*) as count
    FROM article_analysis aa
    GROUP BY topic
    ORDER BY count DESC, topic ASC;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_unique_topics IS 'Returns all unique topics with article counts for filter dropdowns';


-- Function: get_unique_domains
-- Purpose: Get all source domains for filter UI
CREATE OR REPLACE FUNCTION get_unique_domains()
RETURNS TABLE(domain TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.source_domain as domain,
        COUNT(*) as count
    FROM articles a
    WHERE a.content IS NOT NULL
    GROUP BY a.source_domain
    ORDER BY count DESC, domain ASC;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_unique_domains IS 'Returns all source domains with article counts for filter dropdowns';


-- ============================================================================
-- SECTION 3: ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on base tables (if not already enabled)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE feeds ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Allow public read access to articles" ON articles;
DROP POLICY IF EXISTS "Allow public read access to article_analysis" ON article_analysis;
DROP POLICY IF EXISTS "Allow public read access to processed_content" ON processed_content;
DROP POLICY IF EXISTS "Allow public read access to feeds" ON feeds;

-- Policy: Public read access to articles
-- Purpose: Allow unauthenticated frontend to read all articles
CREATE POLICY "Allow public read access to articles"
ON articles
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: Public read access to article_analysis
CREATE POLICY "Allow public read access to article_analysis"
ON article_analysis
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: Public read access to processed_content
CREATE POLICY "Allow public read access to processed_content"
ON processed_content
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: Public read access to feeds (for source info)
CREATE POLICY "Allow public read access to feeds"
ON feeds
FOR SELECT
TO anon, authenticated
USING (true);

-- Note: Write operations remain restricted (only service_role can write)
-- Your Python scraping system uses service_role key, so it can still write
-- Frontend uses anon key, so it can only read

COMMENT ON POLICY "Allow public read access to articles" ON articles IS 'Frontend can read all articles (read-only)';
COMMENT ON POLICY "Allow public read access to article_analysis" ON article_analysis IS 'Frontend can read all analysis data (read-only)';
COMMENT ON POLICY "Allow public read access to processed_content" ON processed_content IS 'Frontend can read all cleaned content (read-only)';
COMMENT ON POLICY "Allow public read access to feeds" ON feeds IS 'Frontend can read feed sources (read-only)';


-- ============================================================================
-- SECTION 4: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Note: Most indexes already exist from previous migrations
-- Adding any missing indexes for optimal frontend query performance

-- Index for filtering by language level
CREATE INDEX IF NOT EXISTS idx_article_analysis_language_level
ON article_analysis(language_level);

-- GIN index for topic array queries (if not exists)
CREATE INDEX IF NOT EXISTS idx_article_analysis_topics_gin
ON article_analysis USING GIN(topics);

-- Index for sorting by published date (descending)
CREATE INDEX IF NOT EXISTS idx_articles_published_date_desc
ON articles(published_date DESC);

-- Index for filtering by source domain
CREATE INDEX IF NOT EXISTS idx_articles_source_domain
ON articles(source_domain);

-- Composite index for common query: level + published_date
CREATE INDEX IF NOT EXISTS idx_article_analysis_level_and_article
ON article_analysis(language_level, article_id);


-- ============================================================================
-- SECTION 5: GRANT PERMISSIONS
-- ============================================================================

-- Grant SELECT on views to anon and authenticated roles
GRANT SELECT ON article_list_view TO anon, authenticated;
GRANT SELECT ON article_detail_view TO anon, authenticated;
GRANT SELECT ON article_statistics TO anon, authenticated;

-- Grant EXECUTE on functions to anon and authenticated roles
GRANT EXECUTE ON FUNCTION get_unique_topics() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_unique_domains() TO anon, authenticated;


-- ============================================================================
-- SECTION 6: VERIFICATION QUERIES
-- ============================================================================
-- Run these queries after migration to verify everything works

-- Test 1: Count articles in list view
-- Expected: Should return count of fully processed articles
-- SELECT COUNT(*) FROM article_list_view;

-- Test 2: Get articles for specific level
-- Expected: Only B2 articles
-- SELECT * FROM article_list_view WHERE language_level = 'B2' LIMIT 10;

-- Test 3: Get articles with topic filter
-- Expected: Articles containing 'politics' topic
-- SELECT * FROM article_list_view WHERE 'politics' = ANY(topics) LIMIT 10;

-- Test 4: Get single article detail
-- Expected: Full article with all fields
-- SELECT * FROM article_detail_view LIMIT 1;

-- Test 5: Get statistics
-- Expected: Aggregate counts
-- SELECT * FROM article_statistics;

-- Test 6: Get unique topics
-- Expected: List of topics with counts
-- SELECT * FROM get_unique_topics();

-- Test 7: Get unique domains
-- Expected: List of domains with counts
-- SELECT * FROM get_unique_domains();

-- Test 8: Verify RLS policies exist
-- Expected: Should show 4 policies
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE tablename IN ('articles', 'article_analysis', 'processed_content', 'feeds');


-- ============================================================================
-- SECTION 7: ROLLBACK SCRIPT (if needed)
-- ============================================================================
-- If you need to undo this migration, run:

-- DROP VIEW IF EXISTS article_list_view;
-- DROP VIEW IF EXISTS article_detail_view;
-- DROP VIEW IF EXISTS article_statistics;
-- DROP FUNCTION IF EXISTS get_unique_topics();
-- DROP FUNCTION IF EXISTS get_unique_domains();
-- DROP POLICY IF EXISTS "Allow public read access to articles" ON articles;
-- DROP POLICY IF EXISTS "Allow public read access to article_analysis" ON article_analysis;
-- DROP POLICY IF EXISTS "Allow public read access to processed_content" ON processed_content;
-- DROP POLICY IF EXISTS "Allow public read access to feeds" ON feeds;


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Run verification queries above to ensure everything works
-- 2. Test frontend connection using Supabase anon key
-- 3. Verify RLS policies prevent write operations from frontend
-- ============================================================================
