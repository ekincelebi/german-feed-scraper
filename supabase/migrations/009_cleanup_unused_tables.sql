-- Migration: Cleanup unused tables and views
-- Drop tables and views that are no longer needed

-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS article_learning_view CASCADE;
DROP VIEW IF EXISTS article_detail_view CASCADE;
DROP VIEW IF EXISTS article_list_view CASCADE;
DROP VIEW IF EXISTS article_statistics CASCADE;

-- Drop tables
DROP TABLE IF EXISTS article_analysis CASCADE;

-- Note: This migration removes:
-- 1. article_analysis table (replaced by learning_enhancements)
-- 2. article_statistics table (if not needed)
-- 3. article_learning_view (will be recreated if needed)
-- 4. article_detail_view (will be recreated if needed)
-- 5. article_list_view (will be recreated if needed)