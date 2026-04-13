"""
Domain-specific content extractors for German news sites.

Each extractor is optimized for a specific site's HTML structure to ensure
complete content extraction, not just summaries.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentExtractor:
    """Base class for content extraction with site-specific strategies."""

    def __init__(self, timeout: int = 30):
        """
        Initialize content extractor.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )

    def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL using domain-specific strategy.

        Args:
            url: Article URL

        Returns:
            Dictionary with extracted content and metadata
        """
        domain = urlparse(url).netloc

        # Route to domain-specific extractor
        if 'nachrichtenleicht.de' in domain:
            return self._extract_nachrichtenleicht(url)
        elif 'dw.com' in domain or 'learngerman.dw.com' in domain:
            return self._extract_dw(url)
        elif 'brigitte.de' in domain:
            return self._extract_brigitte(url)
        elif 'sueddeutsche.de' in domain:
            return self._extract_sueddeutsche(url)
        elif 'spiegel.de' in domain:
            return self._extract_spiegel(url)
        elif 't3n.de' in domain:
            return self._extract_t3n(url)
        elif 'tagesschau.de' in domain:
            return self._extract_tagesschau(url)
        elif 'geo.de' in domain:
            return self._extract_geo(url)
        elif 'chefkoch.de' in domain:
            return self._extract_chefkoch(url)
        else:
            # Fallback to generic extraction
            return self._extract_generic(url)

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse webpage.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object or None if error
        """
        try:
            logger.debug(f"Fetching: {url}")
            response = self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _clean_text(self, elements) -> str:
        """
        Extract and clean text from elements.

        Args:
            elements: BeautifulSoup elements or single element

        Returns:
            Cleaned text
        """
        if not elements:
            return ""

        # Handle single element or list
        if not isinstance(elements, list):
            elements = [elements]

        text_parts = []
        for elem in elements:
            if elem:
                # Get all text-containing tags
                for tag in elem.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 10:  # Filter very short snippets
                        text_parts.append(text)

        full_text = '\n\n'.join(text_parts)
        return full_text.strip()

    def _extract_nachrichtenleicht(self, url: str) -> Dict[str, Any]:
        """
        Extract content from nachrichtenleicht.de.

        Selectors:
        - article-content: Main article content
        - Article header description
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Get article header description
            header_desc = ""
            desc_elem = soup.find('div', class_='article-header__description') or soup.find('p', class_='article-intro')
            if desc_elem:
                header_desc = desc_elem.get_text(strip=True)

            # Get main article content from article-content
            content_parts = [header_desc] if header_desc else []

            article_content = soup.find('div', class_='article-content')
            if article_content:
                content_parts.append(self._clean_text(article_content))

            content = '\n\n'.join(filter(None, content_parts))

            logger.info(f"✓ Nachrichtenleicht: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from nachrichtenleicht: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_dw(self, url: str) -> Dict[str, Any]:
        """
        Extract content from dw.com and learngerman.dw.com.

        Selectors:
        - content-area: Main article content
        - main: Fallback for learngerman pages

        Note: learngerman.dw.com pages are JavaScript-rendered and may not
        have accessible content in the initial HTML. These will return empty
        and should use RSS feed content as fallback.
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Check if this is a JavaScript-rendered page (learngerman)
            # These pages have minimal HTML and load content via JS
            if 'learngerman.dw.com' in url:
                # Check if page has actual content or just JS placeholders
                body = soup.find('body')
                if body:
                    text_content = body.get_text(strip=True)
                    # If very little text, it's JS-rendered
                    if len(text_content) < 500:
                        logger.info(f"⊘ DW: JavaScript-rendered page, use RSS content")
                        return {"content": "", "title": title, "error": "JS-rendered", "use_rss_content": True}

            # Get content from content-area or main
            content = ""
            content_area = soup.find('div', class_='content-area')

            if not content_area:
                # Try main for learngerman pages
                content_area = soup.find('main') or soup.find('article')

            if content_area:
                # Remove unwanted elements
                for unwanted in content_area.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                    unwanted.decompose()

                content = self._clean_text(content_area)

            logger.info(f"✓ DW: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from DW: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_brigitte(self, url: str) -> Dict[str, Any]:
        """
        Extract content from brigitte.de.

        Special handling:
        - Recipe pages: Follow "zum rezepte" links, then extract from recipe__main
        - Regular articles: Extract full content
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Check if this is a recipe overview page with "zum rezepte" links
            recipe_links = soup.find_all('a', string=lambda s: s and 'zum rezept' in s.lower())

            if recipe_links and '/rezepte/' in url:
                # This is a recipe overview - get first recipe link
                first_recipe = recipe_links[0].get('href')
                if first_recipe:
                    # Make absolute URL
                    recipe_url = urljoin(url, first_recipe)
                    logger.info(f"Following recipe link: {recipe_url}")

                    # Fetch actual recipe page
                    recipe_soup = self._fetch_page(recipe_url)
                    if recipe_soup:
                        # Extract from recipe__body (not recipe__main)
                        recipe_body = recipe_soup.find('div', class_='recipe__body')
                        if recipe_body:
                            content = self._clean_text(recipe_body)
                            # Update title from recipe page
                            recipe_title = recipe_soup.find('h1')
                            if recipe_title:
                                title = recipe_title.get_text(strip=True)

                            logger.info(f"✓ BRIGITTE Recipe: {len(content)} chars")
                            return {"content": content, "title": title, "error": None}

            # Regular article or fallback
            content = ""

            # Try main article content
            article = soup.find('article') or soup.find('div', class_='article-body')
            if article:
                # Remove unwanted elements
                for unwanted in article.find_all(['script', 'style', 'nav', 'aside', 'footer', 'ad']):
                    unwanted.decompose()

                content = self._clean_text(article)

            logger.info(f"✓ BRIGITTE: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from BRIGITTE: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_sueddeutsche(self, url: str) -> Dict[str, Any]:
        """
        Extract content from sueddeutsche.de.

        Note: Skip liveblog URLs (they update constantly)
        """
        # Skip liveblogs
        if 'liveblog' in url:
            logger.info(f"⊘ Skipping liveblog: {url}")
            return {"content": "", "title": "", "error": "Liveblog skipped", "skip": True}

        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Get article content
            content = ""
            article = soup.find('article') or soup.find('div', class_='article-body')

            if article:
                # Remove unwanted elements
                for unwanted in article.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                    unwanted.decompose()

                content = self._clean_text(article)

            logger.info(f"✓ Süddeutsche: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from Süddeutsche: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_spiegel(self, url: str) -> Dict[str, Any]:
        """
        Extract content from spiegel.de.

        Selectors:
        - [data-area="body"]: Main article content
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Get content from data-area="body"
            content = ""
            body_area = soup.find(attrs={'data-area': 'body'})

            if body_area:
                # Remove unwanted elements
                for unwanted in body_area.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                    unwanted.decompose()

                content = self._clean_text(body_area)
            else:
                # Fallback to article tag
                article = soup.find('article')
                if article:
                    content = self._clean_text(article)

            logger.info(f"✓ Spiegel: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from Spiegel: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_t3n(self, url: str) -> Dict[str, Any]:
        """
        Extract content from t3n.de.

        Selectors:
        - content-wrapper: Main article content
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Get content from content-wrapper
            content = ""
            content_wrapper = soup.find('div', class_='content-wrapper') or soup.find('article')

            if content_wrapper:
                # Remove unwanted elements
                for unwanted in content_wrapper.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                    unwanted.decompose()

                content = self._clean_text(content_wrapper)

            logger.info(f"✓ t3n: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from t3n: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_tagesschau(self, url: str) -> Dict[str, Any]:
        """Extract content from tagesschau.de."""
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            content = ""
            article = soup.find('article') or soup.find('div', class_='article-body')
            if article:
                content = self._clean_text(article)

            logger.info(f"✓ Tagesschau: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from Tagesschau: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_geo(self, url: str) -> Dict[str, Any]:
        """Extract content from geo.de."""
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            content = ""
            article = soup.find('article') or soup.find('div', class_='article-body')
            if article:
                content = self._clean_text(article)

            logger.info(f"✓ GEO: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from GEO: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_chefkoch(self, url: str) -> Dict[str, Any]:
        """Extract content from chefkoch.de."""
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            content = ""
            # Try main tag with paragraphs
            main = soup.find('main')
            if main:
                # Remove unwanted elements
                for unwanted in main.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                    unwanted.decompose()

                content = self._clean_text(main)

            if not content or len(content) < 100:
                # Fallback to recipe selectors
                recipe = soup.find('article', class_='recipe') or soup.find('div', class_='recipe-content')
                if recipe:
                    content = self._clean_text(recipe)

            logger.info(f"✓ Chefkoch: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting from Chefkoch: {e}")
            return {"content": "", "title": "", "error": str(e)}

    def _extract_generic(self, url: str) -> Dict[str, Any]:
        """
        Generic content extraction fallback.

        Uses common selectors and heuristics.
        """
        soup = self._fetch_page(url)
        if not soup:
            return {"content": "", "title": "", "error": "Failed to fetch page"}

        try:
            # Get title
            title = ""
            title_elem = soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Try common article selectors
            content = ""
            selectors = [
                ('article', {}),
                ('div', {'class': 'article-content'}),
                ('div', {'class': 'article-body'}),
                ('div', {'class': 'content'}),
                ('div', {'class': 'post-content'}),
                ('main', {}),
            ]

            for tag, attrs in selectors:
                elem = soup.find(tag, attrs) if attrs else soup.find(tag)
                if elem:
                    # Remove unwanted elements
                    for unwanted in elem.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                        unwanted.decompose()

                    content = self._clean_text(elem)
                    if len(content) > 100:  # Only accept if substantial
                        break

            logger.info(f"✓ Generic: {len(content)} chars")
            return {"content": content, "title": title, "error": None}

        except Exception as e:
            logger.error(f"Error extracting (generic): {e}")
            return {"content": "", "title": "", "error": str(e)}

    def close(self):
        """Close HTTP client."""
        self.client.close()
