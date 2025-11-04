# API Routes Reference (Future Use)

**Project:** German Language Learning Platform
**Purpose:** Documentation for Next.js API routes when needed
**Status:** Not required for MVP (Server Components handle data fetching)

---

## When to Use API Routes

For the MVP, **you don't need API routes** because:
- ✅ Server Components fetch data directly from Supabase
- ✅ Frontend is read-only (no mutations)
- ✅ No complex business logic needed yet

**Use API routes when you add:**
- User authentication (login, signup)
- Bookmarking/saving articles
- User progress tracking
- Search functionality (if complex)
- Rate limiting
- Caching layers
- Integration with external APIs

---

## API Routes Structure

When you need API routes, create them in `app/api/`:

```
app/
├── api/
│   ├── articles/
│   │   ├── route.ts              # GET /api/articles (list with filters)
│   │   └── [id]/
│   │       ├── route.ts          # GET /api/articles/[id]
│   │       └── bookmark/
│   │           └── route.ts      # POST /api/articles/[id]/bookmark
│   ├── topics/
│   │   └── route.ts              # GET /api/topics (get unique topics)
│   ├── stats/
│   │   └── route.ts              # GET /api/stats (statistics)
│   └── search/
│       └── route.ts              # GET /api/search?q=bundestag
```

---

## Example API Routes

### 1. GET /api/articles (List Articles)

**Purpose:** Get articles with filtering (alternative to Server Components)

**File:** `app/api/articles/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams

  const level = searchParams.get('level')
  const topic = searchParams.get('topic')
  const limit = parseInt(searchParams.get('limit') || '50')
  const offset = parseInt(searchParams.get('offset') || '0')

  try {
    let query = supabase
      .from('article_list_view')
      .select('*', { count: 'exact' })

    // Apply filters
    if (level) {
      query = query.eq('language_level', level.toUpperCase())
    }

    if (topic) {
      query = query.contains('topics', [topic])
    }

    // Apply pagination
    query = query
      .order('published_date', { ascending: false })
      .range(offset, offset + limit - 1)

    const { data, error, count } = await query

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({
      data,
      count,
      limit,
      offset
    })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
// Client component
const response = await fetch('/api/articles?level=B2&topic=politics&limit=20')
const { data, count } = await response.json()
```

---

### 2. GET /api/articles/[id] (Single Article)

**Purpose:** Get article detail by ID

**File:** `app/api/articles/[id]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id } = params

  try {
    const { data, error } = await supabase
      .from('article_detail_view')
      .select('*')
      .eq('id', id)
      .single()

    if (error) {
      return NextResponse.json(
        { error: 'Article not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({ data })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
const response = await fetch(`/api/articles/${articleId}`)
const { data: article } = await response.json()
```

---

### 3. GET /api/topics (Get Unique Topics)

**Purpose:** Get all topics for filter dropdown

**File:** `app/api/topics/route.ts`

```typescript
import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET() {
  try {
    const { data, error } = await supabase
      .rpc('get_unique_topics')

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
const response = await fetch('/api/topics')
const { data: topics } = await response.json()
// topics = [{ topic: "politics", count: 2340 }, ...]
```

---

### 4. GET /api/stats (Statistics)

**Purpose:** Get aggregate statistics

**File:** `app/api/stats/route.ts`

```typescript
import { NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET() {
  try {
    const { data, error } = await supabase
      .from('article_statistics')
      .select('*')
      .single()

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
const response = await fetch('/api/stats')
const { data: stats } = await response.json()
```

---

### 5. GET /api/search (Search Articles)

**Purpose:** Full-text search in articles

**File:** `app/api/search/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const query = searchParams.get('q')
  const level = searchParams.get('level')

  if (!query || query.length < 3) {
    return NextResponse.json(
      { error: 'Query must be at least 3 characters' },
      { status: 400 }
    )
  }

  try {
    let dbQuery = supabase
      .from('article_list_view')
      .select('*')
      .ilike('title', `%${query}%`)

    if (level) {
      dbQuery = dbQuery.eq('language_level', level.toUpperCase())
    }

    const { data, error } = await dbQuery.limit(20)

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data, query })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
const response = await fetch(`/api/search?q=bundestag&level=B2`)
const { data: results } = await response.json()
```

---

## Future: User-Specific Features

When you add user authentication, you'll need these routes:

### 6. POST /api/articles/[id]/bookmark (Bookmark Article)

**Purpose:** Save article to user's bookmarks

**Requirements:**
- User authentication (Supabase Auth)
- New table: `bookmarks` (user_id, article_id)

**File:** `app/api/articles/[id]/bookmark/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id: articleId } = params
  const supabase = createRouteHandlerClient({ cookies })

  // Check if user is authenticated
  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  try {
    // Insert bookmark
    const { data, error } = await supabase
      .from('bookmarks')
      .insert({
        user_id: user.id,
        article_id: articleId
      })
      .select()
      .single()

    if (error) {
      // Handle duplicate bookmark error
      if (error.code === '23505') {
        return NextResponse.json(
          { error: 'Article already bookmarked' },
          { status: 409 }
        )
      }

      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data }, { status: 201 })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const { id: articleId } = params
  const supabase = createRouteHandlerClient({ cookies })

  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  try {
    const { error } = await supabase
      .from('bookmarks')
      .delete()
      .eq('user_id', user.id)
      .eq('article_id', articleId)

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

**Usage from Frontend:**
```typescript
// Bookmark article
await fetch(`/api/articles/${articleId}/bookmark`, {
  method: 'POST'
})

// Remove bookmark
await fetch(`/api/articles/${articleId}/bookmark`, {
  method: 'DELETE'
})
```

---

### 7. GET /api/user/bookmarks (Get User Bookmarks)

**Purpose:** Get all articles bookmarked by user

**File:** `app/api/user/bookmarks/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

export async function GET(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies })

  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  try {
    const { data, error } = await supabase
      .from('bookmarks')
      .select(`
        *,
        article:article_list_view(*)
      `)
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

---

### 8. POST /api/user/progress (Track Reading Progress)

**Purpose:** Save user's reading progress

**Requirements:**
- New table: `user_progress` (user_id, article_id, completed, last_position)

**File:** `app/api/user/progress/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

export async function POST(request: NextRequest) {
  const supabase = createRouteHandlerClient({ cookies })

  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  const body = await request.json()
  const { article_id, completed, last_position } = body

  try {
    const { data, error } = await supabase
      .from('user_progress')
      .upsert({
        user_id: user.id,
        article_id,
        completed: completed || false,
        last_position: last_position || 0,
        updated_at: new Date().toISOString()
      })
      .select()
      .single()

    if (error) {
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ data })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

---

## API Route Best Practices

### 1. Error Handling

Always wrap in try-catch and return proper status codes:

```typescript
try {
  // Logic here
  return NextResponse.json({ data })
} catch (error) {
  console.error('API Error:', error)
  return NextResponse.json(
    { error: 'Internal server error' },
    { status: 500 }
  )
}
```

### 2. Input Validation

Validate query params and request body:

```typescript
const level = searchParams.get('level')

if (level && !['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].includes(level.toUpperCase())) {
  return NextResponse.json(
    { error: 'Invalid level' },
    { status: 400 }
  )
}
```

### 3. Rate Limiting (Advanced)

Consider adding rate limiting for production:

```typescript
import { ratelimit } from '@/lib/redis'

export async function GET(request: NextRequest) {
  const ip = request.ip ?? '127.0.0.1'
  const { success } = await ratelimit.limit(ip)

  if (!success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429 }
    )
  }

  // Continue with logic
}
```

### 4. Caching

Add cache headers for static data:

```typescript
export async function GET() {
  const { data } = await supabase.from('article_statistics').select('*').single()

  return NextResponse.json({ data }, {
    headers: {
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400'
    }
  })
}
```

---

## When to Use API Routes vs Server Components

| Use Case | Solution | Why |
|----------|----------|-----|
| Initial page load | Server Components | Faster, SEO-friendly |
| User interactions (bookmarks) | API Routes | Client-side mutations |
| Simple data fetching | Server Components | Less code, built-in |
| Complex business logic | API Routes | Easier to test, reusable |
| Search | Either | Server Components for simple, API for complex |
| Real-time updates | API Routes + polling | Need client-side fetching |
| Authentication | API Routes | Need session management |

---

## Summary

**For MVP (Now):**
- ✅ Use Server Components to fetch data directly
- ✅ No API routes needed

**For Future Features:**
- 📌 User authentication → API routes for auth
- 📌 Bookmarks → POST/DELETE /api/articles/[id]/bookmark
- 📌 Progress tracking → POST /api/user/progress
- 📌 Search → GET /api/search
- 📌 Complex filtering → GET /api/articles with query params

**Remember:**
- API routes run on the server (not browser)
- Use TypeScript for type safety
- Always validate input
- Return proper HTTP status codes
- Handle errors gracefully

This document serves as a reference for when you need to add these features later!
