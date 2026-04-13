# Frontend Guide: Reading Articles

This guide explains how a frontend app should read articles from the backend API safely.

## Architecture Rule

- Frontend must call backend endpoints only (`/api/*`).
- Frontend must not query Supabase tables directly.
- Frontend must never use `SUPABASE_KEY` (service role) in browser code.

## Base URL

Set your frontend API base URL to your backend service, for example:

- Local: `http://localhost:8000`
- Production: `https://your-api-domain.com`

## Available Endpoints

### 1) Health

- `GET /health`
- Purpose: Check API availability.

### 2) List Articles

- `GET /api/articles`
- Query parameters:
  - `limit` (optional, default `20`, max `100`)
  - `offset` (optional, default `0`)
  - `domain` (optional, example: `tagesschau.de`)
  - `difficulty` (optional, one of: `A2`, `B1`, `B2`, `C1`, `C2`)

Example:

`GET /api/articles?limit=20&offset=0&difficulty=B1`

Response shape:

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Article title",
      "url": "https://...",
      "published_date": "2026-04-13T10:00:00+00:00",
      "source_domain": "tagesschau.de",
      "theme": "politics",
      "estimated_difficulty": "B1",
      "estimated_reading_time": 6,
      "created_at": "2026-04-13T10:05:00+00:00"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### 3) Article Detail

- `GET /api/articles/{id}`
- Path parameter:
  - `id`: article UUID

Response includes safe detail fields, including cleaned content and learning enhancements.

## TypeScript Example

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;

export type Difficulty = "A2" | "B1" | "B2" | "C1" | "C2";

export interface ArticleListItem {
  id: string;
  title: string;
  url: string;
  published_date: string | null;
  source_domain: string | null;
  theme: string | null;
  estimated_difficulty: Difficulty | null;
  estimated_reading_time: number | null;
  created_at: string;
}

export interface ArticleListResponse {
  items: ArticleListItem[];
  limit: number;
  offset: number;
}

export async function fetchArticles(params: {
  limit?: number;
  offset?: number;
  domain?: string;
  difficulty?: Difficulty;
}): Promise<ArticleListResponse> {
  const search = new URLSearchParams();
  if (params.limit != null) search.set("limit", String(params.limit));
  if (params.offset != null) search.set("offset", String(params.offset));
  if (params.domain) search.set("domain", params.domain);
  if (params.difficulty) search.set("difficulty", params.difficulty);

  const response = await fetch(`${API_BASE_URL}/api/articles?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch articles (${response.status})`);
  }

  return response.json();
}

export async function fetchArticleById(id: string) {
  const response = await fetch(`${API_BASE_URL}/api/articles/${id}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store"
  });

  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Failed to fetch article (${response.status})`);
  return response.json();
}
```

## Pagination Pattern

- Use `limit` + `offset`.
- Start with `limit=20`, `offset=0`.
- Next page: `offset = offset + limit`.
- Stop when `items.length < limit`.

## Filtering Pattern

- Difficulty filter: use exact uppercase values (`A2`, `B1`, `B2`, `C1`, `C2`).
- Domain filter: pass exact domain values (for example `tagesschau.de`).
- For invalid params, API returns `422`.

## Error Handling UX

- `429`: show "Too many requests, retry shortly."
- `500`: show generic fallback and retry button.
- `404` on detail page: show "Article not found."
- Avoid showing raw backend error text to users.

## Security Checklist (Frontend)

- Keep API base URL in frontend env (`NEXT_PUBLIC_API_BASE_URL`).
- Do not store or expose Supabase service role keys.
- Do not call Supabase table endpoints directly from browser code.
- Treat all API fields as untrusted content before rendering.
- Use escaped rendering for article content unless intentionally sanitized.
