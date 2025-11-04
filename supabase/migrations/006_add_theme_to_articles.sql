-- Add theme field to articles table
-- This field stores the theme/category from the feed source (e.g., 'vocabulary', 'recipes', 'health')

ALTER TABLE articles
ADD COLUMN IF NOT EXISTS theme TEXT;

-- Create index for theme filtering
CREATE INDEX IF NOT EXISTS idx_articles_theme ON articles(theme);

-- Add comment
COMMENT ON COLUMN articles.theme IS 'Theme/category of the article from feed source (e.g., vocabulary, recipes, health, culture)';
