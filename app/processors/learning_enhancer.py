"""
Learning enhancer for German articles targeting B1-B2 learners.
Adds vocabulary, grammar, and cultural annotations without modifying original text.
"""

import json
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from groq import Groq
from app.database import get_db
from app.utils.logger import get_logger
from app.settings import settings

logger = get_logger(__name__)


class LearningEnhancer:
    """Enhance cleaned articles with learning annotations for B1-B2 German learners."""

    # Groq pricing (per 1M tokens)
    INPUT_COST_PER_1M = 0.59
    OUTPUT_COST_PER_1M = 0.79

    # Model configuration
    MODEL = "llama-3.3-70b-versatile"
    MAX_TOKENS = 3000  # For JSON output with annotations

    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize the learning enhancer.

        Args:
            api_key: Groq API key (defaults to environment variable)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.client = Groq(api_key=self.api_key)
        self.db_client = get_db()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []

        # Thread safety for parallel processing
        self.stats_lock = Lock()

    def _create_enhancement_prompt(self, cleaned_content: str, title: str, theme: str) -> str:
        """
        Create the prompt for learning enhancement.

        Args:
            cleaned_content: Cleaned article text
            title: Article title
            theme: Article theme

        Returns:
            Formatted prompt string
        """
        return f"""You are an experienced German language teacher preparing authentic German articles for intermediate learners (B1-B2 CEFR level).

Your task: Analyze this German article and create educational enhancements to help learners understand and learn from authentic German text.

IMPORTANT RULES:
- DO NOT modify or simplify the original article text
- DO NOT translate the article
- Focus on B1-B2 level vocabulary and grammar
- Provide concise, practical learning support
- Output ONLY valid JSON (no markdown, no explanations)

Article Information:
Title: {title}
Theme: {theme}

Article Text:
{cleaned_content[:6000]}

Create learning enhancements with:

1. VOCABULARY (10-15 words):
   - Select words that are KEY to understanding the article's main ideas
   - AVOID obvious cognates (e.g., "Account", "Funktion", "Computer")
   - AVOID basic A1-A2 words that intermediate learners already know
   - PRIORITIZE: Domain-specific terms, idiomatic expressions, advanced verbs, useful adjectives
   - Focus on words that enhance language learning and comprehension
   - For NOUNS: Include article (der/die/das) and plural form
   - For VERBS: Include infinitive form and common separable prefixes if applicable
   - For ADJECTIVES: Include if they're descriptive and useful
   - Provide English translation
   - Provide German explanation (simple German definition)
   - Show context sentence from article

2. GRAMMAR PATTERNS (3-5 patterns):
   - Identify key grammar structures in the article
   - Provide example sentence from the text
   - Give brief German explanation

3. CULTURAL NOTES (2-3 notes):
   - Highlight cultural references, idioms, or context
   - Explain German institutions, customs, or practices
   - Keep explanations concise

4. COMPREHENSION QUESTIONS (3-5 questions):
   - Write open-ended questions in German
   - Test understanding of main ideas
   - Encourage use of article vocabulary

5. DIFFICULTY & READING TIME:
   - Estimate CEFR level (B1, B2, or C1)
   - Estimate reading time in minutes for B1-B2 learners

VOCABULARY SELECTION EXAMPLES:
✓ GOOD: "verabschieden" (advanced verb), "Bundestag" (institution), "Vorschrift" (regulation)
✗ AVOID: "Account" (cognate), "Computer" (cognate), "interessant" (too basic)

Return ONLY this JSON structure:
{{
  "estimated_difficulty": "B1|B2|C1",
  "estimated_reading_time": 5,
  "key_vocabulary": [
    {{
      "word": "Bundestag",
      "article": "der",
      "plural": "die Bundestage",
      "context": "Der Bundestag hat heute ein neues Gesetz verabschiedet.",
      "english_translation": "German federal parliament",
      "german_explanation": "Das deutsche Parlament, wo Gesetze gemacht werden",
      "cefr_level": "B1"
    }},
    {{
      "word": "verabschieden",
      "article": null,
      "plural": null,
      "context": "Der Bundestag hat heute ein neues Gesetz verabschiedet.",
      "english_translation": "to pass (a law), to adopt",
      "german_explanation": "Ein Gesetz oder eine Entscheidung offiziell akzeptieren",
      "cefr_level": "B2"
    }},
    {{
      "word": "aufklären",
      "article": null,
      "plural": null,
      "context": "Die Polizei versucht, den Fall aufzuklären.",
      "english_translation": "to clarify, to solve (a case)",
      "german_explanation": "Etwas Unklares erklären oder einen Fall lösen",
      "cefr_level": "B2"
    }}
  ],
  "grammar_patterns": [
    {{
      "pattern": "Grammar pattern name",
      "example": "Example sentence from article",
      "explanation": "Brief German explanation"
    }}
  ],
  "cultural_notes": [
    "Cultural insight or context explanation"
  ],
  "comprehension_questions": [
    "Question in German?"
  ]
}}"""

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost

    def enhance_article(
        self,
        article_id: str,
        cleaned_content: str,
        title: str,
        theme: str
    ) -> Optional[Dict[str, Any]]:
        """
        Enhance a single article with learning annotations.

        Args:
            article_id: Article database ID
            cleaned_content: Cleaned article text
            title: Article title
            theme: Article theme

        Returns:
            Enhancement data dictionary or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                # Check if insufficient content
                if not cleaned_content or len(cleaned_content) < 100:
                    logger.warning(f"Article {article_id} has insufficient content, skipping")
                    return None

                # Check if already enhanced
                existing = self.db_client.table("learning_enhancements").select("id").eq("article_id", article_id).execute()
                if existing.data:
                    logger.info(f"Article {article_id} already enhanced, skipping")
                    return None

                # Create prompt
                prompt = self._create_enhancement_prompt(cleaned_content, title, theme)

                # Call Groq API
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a German language teacher. Output ONLY valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for consistent JSON
                    max_tokens=self.MAX_TOKENS,
                    response_format={"type": "json_object"}  # Ensure JSON output
                )

                # Extract response
                enhancement_json = response.choices[0].message.content
                enhancement_data = json.loads(enhancement_json)

                # Calculate cost
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                cost = self._calculate_cost(input_tokens, output_tokens)

                # Update statistics (thread-safe)
                with self.stats_lock:
                    self.total_articles_processed += 1
                    self.total_tokens_used += total_tokens
                    self.total_cost_usd += cost

                # Prepare database record
                result = {
                    'article_id': article_id,
                    'vocabulary_annotations': json.dumps(enhancement_data.get('key_vocabulary', [])),
                    'grammar_patterns': json.dumps(enhancement_data.get('grammar_patterns', [])),
                    'cultural_notes': enhancement_data.get('cultural_notes', []),
                    'comprehension_questions': json.dumps(enhancement_data.get('comprehension_questions', [])),
                    'estimated_difficulty': enhancement_data.get('estimated_difficulty', 'B2'),
                    'estimated_reading_time': enhancement_data.get('estimated_reading_time', 5),
                    'processing_tokens': total_tokens,
                    'processing_cost_usd': cost,
                    'model_used': self.MODEL
                }

                # Save to database
                self.db_client.table("learning_enhancements").insert(result).execute()

                logger.info(
                    f"Enhanced article {article_id}: "
                    f"difficulty={result['estimated_difficulty']}, "
                    f"{len(enhancement_data.get('key_vocabulary', []))} vocab words, "
                    f"{total_tokens} tokens, ${cost:.4f}"
                )

                return result

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error for article {article_id} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    with self.stats_lock:
                        self.failed_articles.append(article_id)
                    return None

            except Exception as e:
                logger.error(f"Error enhancing article {article_id} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    with self.stats_lock:
                        self.failed_articles.append(article_id)
                    return None

        return None

    def enhance_articles_parallel(
        self,
        limit: Optional[int] = None,
        max_cost_usd: float = 5.0,
        rate_limit_delay: float = 0.1,
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Enhance articles in parallel with learning annotations.

        Args:
            limit: Maximum number of articles to enhance (None for all)
            max_cost_usd: Maximum cost budget in USD
            rate_limit_delay: Delay between batch submissions in seconds
            max_workers: Number of parallel workers (default: 5)

        Returns:
            Summary dictionary with statistics
        """
        logger.info(f"Starting parallel learning enhancement (workers={max_workers}, limit={limit}, max_cost=${max_cost_usd})")

        # Reset statistics
        self.total_articles_processed = 0
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.failed_articles = []

        # Get all articles that have been cleaned but not yet enhanced
        enhanced = self.db_client.table("learning_enhancements").select("article_id").execute()
        enhanced_ids = {item['article_id'] for item in enhanced.data}

        # Fetch cleaned articles that haven't been enhanced yet
        query = self.db_client.table("processed_content").select("article_id, cleaned_content").execute()

        articles_with_content = []
        for item in query.data:
            if item['article_id'] not in enhanced_ids and item.get('cleaned_content'):
                # Get article metadata
                article_query = self.db_client.table("articles").select("id, title, theme").eq("id", item['article_id']).execute()
                if article_query.data:
                    article = article_query.data[0]
                    articles_with_content.append({
                        'id': article['id'],
                        'title': article.get('title', 'Untitled'),
                        'theme': article.get('theme', 'general'),
                        'cleaned_content': item['cleaned_content']
                    })

        # Apply limit AFTER filtering
        if limit:
            articles_with_content = articles_with_content[:limit]

        if not articles_with_content:
            logger.info("No articles to enhance (all already enhanced)")
            return self.get_statistics()

        total_to_process = len(articles_with_content)
        logger.info(f"Found {total_to_process} articles to enhance")

        start_time = time.time()

        # Process articles in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for idx, article in enumerate(articles_with_content, 1):
                # Check budget before submitting
                if self.total_cost_usd >= max_cost_usd:
                    logger.warning(f"Reached budget limit of ${max_cost_usd:.2f}, stopping submission")
                    break

                article_id = article['id']
                title = article['title']
                cleaned_content = article['cleaned_content']
                theme = article['theme']

                # Submit task
                future = executor.submit(
                    self.enhance_article,
                    article_id,
                    cleaned_content,
                    title,
                    theme
                )
                futures[future] = (idx, title)

                # Progress logging during submission (every article)
                logger.info(f"[Submitting] {idx}/{total_to_process}: {title[:60]}...")

                # Rate limiting
                if idx % 10 == 0:
                    time.sleep(rate_limit_delay)

            # Process results as they complete
            completed_count = 0
            for future in as_completed(futures):
                completed_count += 1
                idx, title = futures[future]

                try:
                    result = future.result()

                    # Calculate progress metrics
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed if elapsed > 0 else 0
                    eta_seconds = (len(futures) - completed_count) / rate if rate > 0 else 0
                    eta_minutes = eta_seconds / 60

                    if result:
                        logger.info(
                            f"✓ [{completed_count}/{len(futures)}] Enhanced: {title[:50]}... | "
                            f"Cost: ${self.total_cost_usd:.4f} | "
                            f"Rate: {rate:.2f}/sec | "
                            f"ETA: {eta_minutes:.1f}min"
                        )
                    else:
                        logger.warning(f"⊘ [{completed_count}/{len(futures)}] Skipped: {title[:50]}...")
                except Exception as e:
                    logger.error(f"✗ [{completed_count}/{len(futures)}] Error: {title[:50]}...: {e}")

        elapsed_time = time.time() - start_time

        logger.info(
            f"\nParallel learning enhancement complete!\n"
            f"Enhanced: {self.total_articles_processed}/{total_to_process}\n"
            f"Failed: {len(self.failed_articles)}\n"
            f"Total cost: ${self.total_cost_usd:.4f}\n"
            f"Time: {elapsed_time/60:.1f} minutes\n"
            f"Rate: {self.total_articles_processed/elapsed_time:.2f} articles/sec"
        )

        return self.get_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return {
            'total_processed': self.total_articles_processed,
            'total_failed': len(self.failed_articles),
            'failed_article_ids': self.failed_articles,
            'total_tokens': self.total_tokens_used,
            'total_cost_usd': self.total_cost_usd,
            'average_tokens_per_article': (
                self.total_tokens_used / self.total_articles_processed
                if self.total_articles_processed > 0 else 0
            ),
            'average_cost_per_article': (
                self.total_cost_usd / self.total_articles_processed
                if self.total_articles_processed > 0 else 0
            )
        }
