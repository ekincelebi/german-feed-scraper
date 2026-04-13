-- Migration: Cleanup deprecated analysis schema
-- Drop article_analysis and legacy views that depend on it.
-- Note: article_learning_view is based on learning_enhancements and is kept.

-- Drop legacy views first (they depend on article_analysis)
DROP VIEW IF EXISTS article_detail_view CASCADE;
DROP VIEW IF EXISTS article_list_view CASCADE;
DROP VIEW IF EXISTS article_statistics CASCADE;

-- Drop tables
DROP TABLE IF EXISTS article_analysis CASCADE;

-- Note: This migration removes:
-- 1. article_analysis table (replaced by learning_enhancements)
-- 2. Legacy article_detail_view/article_list_view/article_statistics
-- 3. Follow-up migration 010 recreates all frontend views on the new schema