# Frontend Specification - German Language Learning Platform

**For:** Next.js Frontend Project (Separate Repository)
**Backend:** Supabase PostgreSQL (Read-Only)
**Created:** 2025-10-27

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Supabase Connection](#supabase-connection)
4. [Database Views](#database-views)
5. [Application Routes](#application-routes)
6. [Feature Requirements](#feature-requirements)
7. [Data Flow](#data-flow)
8. [TypeScript Types](#typescript-types)
9. [Component Structure](#component-structure)
10. [Implementation Checklist](#implementation-checklist)

---

## Project Overview

### Purpose
A German language learning platform where users can:
- Browse German news articles by CEFR level (A1-C2)
- Filter articles by topics
- Read cleaned, learner-optimized content
- Learn vocabulary with inline translations
- Study grammar patterns used in articles

### User Flow
```
1. Homepage
   └─→ Select language level (A1-C2)
   └─→ Optional: Filter by topic

2. Article List
   └─→ Browse articles for selected level
   └─→ Click article to read

3. Article Reader
   └─→ Read cleaned German text
   └─→ Click highlighted vocabulary for translations
   └─→ View grammar patterns sidebar
   └─→ Return to list
```

---

## Tech Stack

### Required
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Database Client:** `@supabase/supabase-js`
- **Styling:** Tailwind CSS (or your preference)
- **Data Fetching:** Server Components (built-in)

### Recommended (Optional)
- **UI Components:** shadcn/ui or Radix UI
- **State Management:** React Context (minimal state needed)
- **Icons:** lucide-react or heroicons

### Installation
```bash
npx create-next-app@latest german-learning-frontend
cd german-learning-frontend
npm install @supabase/supabase-js
npm install -D tailwindcss
```

---

## Supabase Connection

### Environment Variables

Create `.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

**Important:**
- Use the **ANON KEY** (not service role key)
- RLS policies allow public read access (already configured in backend)
- Frontend can only READ, not write (secure by design)

### Supabase Client Setup

Create `lib/supabase.ts`:
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Usage in Server Components
```typescript
// app/page.tsx (Server Component)
import { supabase } from '@/lib/supabase'

export default async function HomePage() {
  const { data: articles } = await supabase
    .from('article_list_view')
    .select('*')
    .limit(20)

  return <div>{/* render articles */}</div>
}
```

---

## Database Views

**Important:** The backend provides pre-made views that JOIN multiple tables. Use these views, NOT the raw tables!

### View 1: `article_list_view` (For Browsing)

**Use for:** Homepage, article lists, filtering

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Article unique ID |
| `title` | TEXT | Article headline |
| `url` | TEXT | Original article URL |
| `published_date` | TIMESTAMPTZ | Publication date |
| `source_domain` | TEXT | Source (e.g., "www.spiegel.de") |
| `language_level` | VARCHAR(2) | CEFR level: A1, A2, B1, B2, C1, C2 |
| `topics` | TEXT[] | Array: ["politics", "economy"] |
| `word_count_after` | INTEGER | Article length in words |
| `created_at` | TIMESTAMPTZ | When scraped |

**Query Examples:**
```typescript
// Get all articles (with limit)
const { data } = await supabase
  .from('article_list_view')
  .select('*')
  .limit(50)

// Filter by level
const { data } = await supabase
  .from('article_list_view')
  .select('*')
  .eq('language_level', 'B2')
  .limit(50)

// Filter by level + topic
const { data } = await supabase
  .from('article_list_view')
  .select('*')
  .eq('language_level', 'B2')
  .contains('topics', ['politics'])
  .limit(50)

// Pagination
const { data } = await supabase
  .from('article_list_view')
  .select('*')
  .eq('language_level', 'B2')
  .order('published_date', { ascending: false })
  .range(0, 19)  // Items 0-19 (page 1)
```

---

### View 2: `article_detail_view` (For Reading)

**Use for:** Article detail page

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Article unique ID |
| `url` | TEXT | Original article URL |
| `title` | TEXT | Article headline |
| `published_date` | TIMESTAMPTZ | Publication date |
| `author` | TEXT | Author name (may be null) |
| `source_domain` | TEXT | Source domain |
| `language_level` | VARCHAR(2) | CEFR level |
| `topics` | TEXT[] | Array of topics |
| `vocabulary` | JSONB | Array of vocab objects (see below) |
| `grammar_patterns` | TEXT[] | Array of grammar explanations |
| `cleaned_content` | TEXT | **Main article text (cleaned)** |
| `word_count_after` | INTEGER | Article length |
| `created_at` | TIMESTAMPTZ | When scraped |

**Vocabulary Structure (JSONB):**
```json
[
  {
    "word": "Bundestag",
    "artikel": "der",
    "english": "German parliament",
    "plural": "Bundestage"
  },
  {
    "word": "beschließen",
    "artikel": null,
    "english": "to decide, to pass",
    "plural": null
  }
]
```

**Grammar Patterns Structure (TEXT[]):**
```json
[
  "Passive voice: werden + past participle (wurde beschlossen)",
  "Present perfect: haben + past participle (hat beschlossen)",
  "Subordinate clauses with 'dass'",
  "Genitive case for possession"
]
```

**Query Example:**
```typescript
// Get single article by ID
const { data: article, error } = await supabase
  .from('article_detail_view')
  .select('*')
  .eq('id', articleId)
  .single()  // Returns object, not array

// article.vocabulary is already parsed as JSON array
// article.topics is already an array
// article.grammar_patterns is already an array
```

---

### View 3: `article_statistics` (For Dashboard)

**Use for:** Optional stats display

**Columns:**
```typescript
{
  total_articles: number,
  level_a1_count: number,
  level_a2_count: number,
  level_b1_count: number,
  level_b2_count: number,
  level_c1_count: number,
  level_c2_count: number,
  avg_word_count: number
}
```

**Query Example:**
```typescript
const { data: stats } = await supabase
  .from('article_statistics')
  .select('*')
  .single()
```

---

### Helper Functions

#### `get_unique_topics()`
Returns all topics with article counts (for filter dropdown)

```typescript
const { data: topics } = await supabase.rpc('get_unique_topics')

// Returns:
// [
//   { topic: "politics", count: 2340 },
//   { topic: "economy", count: 1876 },
//   ...
// ]
```

#### `get_unique_domains()`
Returns all source domains with counts

```typescript
const { data: domains } = await supabase.rpc('get_unique_domains')

// Returns:
// [
//   { domain: "www.spiegel.de", count: 1523 },
//   { domain: "www.zeit.de", count: 1245 },
//   ...
// ]
```

---

## Application Routes

### Route Structure
```
/                           → Homepage (level selection)
/articles/[level]           → Article list for level (e.g., /articles/B2)
/articles/[level]/[id]      → Article reader (e.g., /articles/B2/uuid-123)
```

### File Structure
```
app/
├── layout.tsx              # Root layout
├── page.tsx                # Homepage (level selection)
├── articles/
│   └── [level]/
│       ├── page.tsx        # Article list
│       └── [id]/
│           └── page.tsx    # Article reader
├── components/
│   ├── LevelSelector.tsx
│   ├── ArticleCard.tsx
│   ├── ArticleReader.tsx
│   ├── VocabularyPopup.tsx
│   └── GrammarSidebar.tsx
└── lib/
    ├── supabase.ts
    └── types.ts
```

---

## Feature Requirements

### 1. Homepage (`/`)

**Purpose:** User selects their CEFR level

**UI Elements:**
- Title: "German Language Learning"
- Subtitle: "Select your level"
- 6 buttons: A1, A2, B1, B2, C1, C2
- Optional: Show article count per level (from `article_statistics`)

**Behavior:**
- Click level → Navigate to `/articles/[level]`
- Example: Click "B2" → Go to `/articles/B2`

**Server Component:**
```typescript
// app/page.tsx
import { supabase } from '@/lib/supabase'
import LevelSelector from '@/components/LevelSelector'

export default async function HomePage() {
  // Optional: Fetch stats for each level
  const { data: stats } = await supabase
    .from('article_statistics')
    .select('*')
    .single()

  return (
    <main>
      <h1>German Language Learning</h1>
      <p>Select your CEFR level</p>
      <LevelSelector stats={stats} />
    </main>
  )
}
```

---

### 2. Article List (`/articles/[level]`)

**Purpose:** Browse articles for selected level, with topic filter

**URL Examples:**
- `/articles/B2` → All B2 articles
- `/articles/A1` → All A1 articles

**UI Elements:**
- Header: "Level B2 Articles" (dynamic)
- Topic filter dropdown (optional)
- Grid/List of article cards:
  - Title
  - Source domain
  - Published date
  - Topics (badges)
  - Word count
  - "Read Article" button

**Data Fetching:**
```typescript
// app/articles/[level]/page.tsx
import { supabase } from '@/lib/supabase'
import ArticleCard from '@/components/ArticleCard'

type Props = {
  params: { level: string }
  searchParams: { topic?: string }
}

export default async function ArticleListPage({ params, searchParams }: Props) {
  const { level } = params
  const { topic } = searchParams

  // Build query
  let query = supabase
    .from('article_list_view')
    .select('*')
    .eq('language_level', level.toUpperCase())
    .order('published_date', { ascending: false })

  // Apply topic filter if provided
  if (topic) {
    query = query.contains('topics', [topic])
  }

  const { data: articles } = await query.limit(50)

  return (
    <main>
      <h1>Level {level.toUpperCase()} Articles</h1>

      {/* Topic Filter Component */}
      <TopicFilter currentTopic={topic} />

      {/* Article Grid */}
      <div className="grid">
        {articles?.map(article => (
          <ArticleCard key={article.id} article={article} level={level} />
        ))}
      </div>
    </main>
  )
}
```

**ArticleCard Component:**
```typescript
// components/ArticleCard.tsx
import Link from 'next/link'

type ArticleCardProps = {
  article: {
    id: string
    title: string
    source_domain: string
    published_date: string
    topics: string[]
    word_count_after: number
  }
  level: string
}

export default function ArticleCard({ article, level }: ArticleCardProps) {
  return (
    <div className="card">
      <h3>{article.title}</h3>
      <p>{article.source_domain}</p>
      <p>{new Date(article.published_date).toLocaleDateString()}</p>

      {/* Topic badges */}
      <div>
        {article.topics.map(topic => (
          <span key={topic} className="badge">{topic}</span>
        ))}
      </div>

      <p>{article.word_count_after} words</p>

      <Link href={`/articles/${level}/${article.id}`}>
        Read Article
      </Link>
    </div>
  )
}
```

---

### 3. Article Reader (`/articles/[level]/[id]`)

**Purpose:** Read article with vocabulary highlights and grammar guide

**URL Example:**
- `/articles/B2/uuid-123`

**UI Elements:**
1. **Header:**
   - Title
   - Source, author, date
   - Level badge
   - Topic badges

2. **Main Content (Left/Center):**
   - Cleaned article text (`cleaned_content`)
   - **Vocabulary words highlighted** (clickable)
   - Click word → Show popup with translation

3. **Sidebar (Right):**
   - "Grammar Patterns" section
   - List of grammar patterns from `grammar_patterns`

4. **Footer:**
   - "Back to Articles" link

**Data Fetching:**
```typescript
// app/articles/[level]/[id]/page.tsx
import { supabase } from '@/lib/supabase'
import ArticleReader from '@/components/ArticleReader'

type Props = {
  params: { level: string; id: string }
}

export default async function ArticleDetailPage({ params }: Props) {
  const { id } = params

  const { data: article, error } = await supabase
    .from('article_detail_view')
    .select('*')
    .eq('id', id)
    .single()

  if (error || !article) {
    return <div>Article not found</div>
  }

  return <ArticleReader article={article} />
}
```

---

### 4. Vocabulary Highlighting (Critical Feature!)

**Goal:** Highlight vocabulary words in `cleaned_content` and make them clickable

**Implementation Strategy:**

**Step 1:** Parse vocabulary from article
```typescript
type VocabWord = {
  word: string
  artikel: string | null
  english: string
  plural: string | null
}

const vocabulary: VocabWord[] = article.vocabulary
```

**Step 2:** Find and replace vocabulary words in `cleaned_content`
```typescript
function highlightVocabulary(content: string, vocabulary: VocabWord[]) {
  let highlightedContent = content

  vocabulary.forEach((vocab, index) => {
    const regex = new RegExp(`\\b${vocab.word}\\b`, 'gi')
    highlightedContent = highlightedContent.replace(
      regex,
      `<mark data-vocab-index="${index}">$&</mark>`
    )
  })

  return highlightedContent
}
```

**Step 3:** Render with click handlers
```typescript
// components/ArticleReader.tsx
'use client'

import { useState } from 'react'
import VocabularyPopup from './VocabularyPopup'

export default function ArticleReader({ article }) {
  const [selectedVocab, setSelectedVocab] = useState<VocabWord | null>(null)
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 })

  // Highlight vocabulary in content
  const highlightedContent = highlightVocabulary(
    article.cleaned_content,
    article.vocabulary
  )

  const handleVocabClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement

    if (target.tagName === 'MARK') {
      const index = parseInt(target.dataset.vocabIndex || '0')
      const vocab = article.vocabulary[index]

      setSelectedVocab(vocab)
      setPopupPosition({
        x: e.clientX,
        y: e.clientY
      })
    }
  }

  return (
    <div>
      {/* Header */}
      <header>
        <h1>{article.title}</h1>
        <p>{article.source_domain} • {article.author}</p>
        <span className="badge">{article.language_level}</span>
      </header>

      <div className="layout">
        {/* Main Content */}
        <article
          onClick={handleVocabClick}
          dangerouslySetInnerHTML={{ __html: highlightedContent }}
          className="prose"
        />

        {/* Sidebar: Grammar Patterns */}
        <aside>
          <h3>Grammar Patterns</h3>
          <ul>
            {article.grammar_patterns.map((pattern, i) => (
              <li key={i}>{pattern}</li>
            ))}
          </ul>
        </aside>
      </div>

      {/* Vocabulary Popup */}
      {selectedVocab && (
        <VocabularyPopup
          vocab={selectedVocab}
          position={popupPosition}
          onClose={() => setSelectedVocab(null)}
        />
      )}
    </div>
  )
}
```

**Step 4:** Vocabulary Popup Component
```typescript
// components/VocabularyPopup.tsx
'use client'

type Props = {
  vocab: {
    word: string
    artikel: string | null
    english: string
    plural: string | null
  }
  position: { x: number; y: number }
  onClose: () => void
}

export default function VocabularyPopup({ vocab, position, onClose }: Props) {
  return (
    <div
      className="popup"
      style={{
        position: 'fixed',
        top: position.y + 10,
        left: position.x + 10,
        background: 'white',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '16px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 1000
      }}
    >
      <button onClick={onClose} className="close-btn">×</button>

      <h4 className="text-lg font-bold">
        {vocab.artikel && <span className="text-blue-600">{vocab.artikel} </span>}
        {vocab.word}
      </h4>

      <p className="text-gray-600">{vocab.english}</p>

      {vocab.plural && (
        <p className="text-sm text-gray-500">
          Plural: {vocab.plural}
        </p>
      )}
    </div>
  )
}
```

---

## Data Flow

### Complete User Journey:

```
1. User visits /
   ↓
   Server Component fetches article_statistics
   ↓
   User sees level buttons with counts

2. User clicks "B2"
   ↓
   Navigate to /articles/B2
   ↓
   Server Component fetches:
     - article_list_view WHERE language_level = 'B2'
   ↓
   User sees grid of B2 articles

3. User optionally filters by topic "politics"
   ↓
   Navigate to /articles/B2?topic=politics
   ↓
   Server Component fetches:
     - article_list_view WHERE language_level = 'B2' AND 'politics' IN topics
   ↓
   User sees filtered articles

4. User clicks article "uuid-123"
   ↓
   Navigate to /articles/B2/uuid-123
   ↓
   Server Component fetches:
     - article_detail_view WHERE id = 'uuid-123'
   ↓
   Client Component:
     - Parses cleaned_content
     - Highlights vocabulary words
     - Renders grammar sidebar

5. User clicks highlighted word "Bundestag"
   ↓
   Popup shows:
     - der Bundestag
     - English: German parliament
     - Plural: Bundestage

6. User clicks "Back to Articles"
   ↓
   Navigate back to /articles/B2
```

---

## TypeScript Types

Create `lib/types.ts`:

```typescript
// Article list item
export type ArticleListItem = {
  id: string
  title: string
  url: string
  published_date: string
  source_domain: string
  language_level: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
  topics: string[]
  word_count_after: number
  created_at: string
}

// Vocabulary word
export type VocabularyWord = {
  word: string
  artikel: string | null  // "der", "die", "das", or null for verbs
  english: string
  plural: string | null
}

// Article detail
export type ArticleDetail = {
  id: string
  url: string
  title: string
  published_date: string
  author: string | null
  source_domain: string
  language_level: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
  topics: string[]
  vocabulary: VocabularyWord[]
  grammar_patterns: string[]
  cleaned_content: string
  word_count_after: number
  created_at: string
}

// Statistics
export type ArticleStatistics = {
  total_articles: number
  level_a1_count: number
  level_a2_count: number
  level_b1_count: number
  level_b2_count: number
  level_c1_count: number
  level_c2_count: number
  avg_word_count: number
}

// CEFR Levels
export const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const
export type CEFRLevel = typeof CEFR_LEVELS[number]
```

---

## Component Structure

### Suggested Components

```
components/
├── LevelSelector.tsx       # Homepage level buttons
├── ArticleCard.tsx         # Article preview card
├── ArticleReader.tsx       # Main article reading component (client)
├── VocabularyPopup.tsx     # Popup for vocabulary details (client)
├── GrammarSidebar.tsx      # Grammar patterns sidebar
├── TopicFilter.tsx         # Topic dropdown filter (client)
├── Header.tsx              # Site header/navigation
└── BackButton.tsx          # Navigation back button
```

---

## Implementation Checklist

### Phase 1: Setup
- [ ] Create Next.js project with TypeScript
- [ ] Install `@supabase/supabase-js`
- [ ] Set up Tailwind CSS
- [ ] Add `.env.local` with Supabase credentials
- [ ] Create `lib/supabase.ts` client
- [ ] Create `lib/types.ts` with TypeScript types

### Phase 2: Routes & Pages
- [ ] Create `app/page.tsx` (Homepage - level selection)
- [ ] Create `app/articles/[level]/page.tsx` (Article list)
- [ ] Create `app/articles/[level]/[id]/page.tsx` (Article reader)
- [ ] Create `app/layout.tsx` (Root layout with header)

### Phase 3: Core Components
- [ ] `LevelSelector` - 6 buttons for CEFR levels
- [ ] `ArticleCard` - Display article preview
- [ ] `ArticleReader` - Main reading interface (client component)
- [ ] `VocabularyPopup` - Clickable word translations
- [ ] `GrammarSidebar` - Display grammar patterns

### Phase 4: Features
- [ ] Implement vocabulary highlighting in content
- [ ] Add click handlers for vocabulary words
- [ ] Show popup with translations on click
- [ ] Add topic filter dropdown
- [ ] Add "Back to Articles" navigation

### Phase 5: Polish
- [ ] Add loading states
- [ ] Add error handling (article not found)
- [ ] Style with Tailwind
- [ ] Make responsive (mobile-friendly)
- [ ] Add metadata for SEO

---

## Example: Complete Article Reader Page

```typescript
// app/articles/[level]/[id]/page.tsx
import { supabase } from '@/lib/supabase'
import { ArticleDetail } from '@/lib/types'
import ArticleReader from '@/components/ArticleReader'
import { notFound } from 'next/navigation'

type Props = {
  params: { level: string; id: string }
}

export default async function ArticleDetailPage({ params }: Props) {
  const { id, level } = params

  // Fetch article from Supabase
  const { data: article, error } = await supabase
    .from('article_detail_view')
    .select('*')
    .eq('id', id)
    .single()

  // Handle errors
  if (error || !article) {
    notFound()
  }

  // Verify article matches requested level
  if (article.language_level !== level.toUpperCase()) {
    notFound()
  }

  return (
    <main className="container mx-auto px-4 py-8">
      <ArticleReader article={article as ArticleDetail} level={level} />
    </main>
  )
}

// Generate metadata for SEO
export async function generateMetadata({ params }: Props) {
  const { data: article } = await supabase
    .from('article_detail_view')
    .select('title, cleaned_content')
    .eq('id', params.id)
    .single()

  return {
    title: article?.title || 'Article',
    description: article?.cleaned_content.substring(0, 160) || ''
  }
}
```

---

## Notes

### Important Reminders:
1. ✅ **Use views, not raw tables:** `article_list_view`, `article_detail_view`
2. ✅ **Only show cleaned_content:** Never expose `original_content` to users
3. ✅ **Server Components by default:** Fetch data on server for speed
4. ✅ **Client Components only when needed:** Vocabulary popup, click handlers
5. ✅ **No authentication needed:** Public read-only access (MVP)
6. ✅ **Vocabulary is JSONB:** Already parsed as JavaScript array
7. ✅ **Topics is array:** Use `.contains()` for filtering

### Performance Tips:
- Use `limit(50)` to avoid fetching thousands of articles
- Implement pagination if article count > 50 per level
- Use Next.js `<Link>` for fast client-side navigation
- Prefetch articles on hover (Next.js does this automatically)

### Future Enhancements (Not MVP):
- User accounts (bookmark articles, track progress)
- Search functionality
- Audio pronunciation
- Flashcard generation from vocabulary
- Progress tracking per level

---

## Questions?

If anything is unclear during implementation, refer back to:
- Database schema: `/Users/ekin/Dev/claude/german-feed-scraper/docs/DATABASE_SCHEMA.md`
- This specification
- Next.js App Router docs: https://nextjs.org/docs/app
- Supabase JS docs: https://supabase.com/docs/reference/javascript

Good luck building! 🚀
