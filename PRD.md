# PRD: TuneScript — Spotify Data Analysis Dashboard

## Problem Statement

Spotify users have years of listening history but no easy, privacy-respecting way to see meaningful analysis of their own taste. Existing third-party platforms require accounts, store data permanently, and bury insights behind paywalls. Users want a lightweight, zero-commitment dashboard that shows who they actually listen to, how their taste evolves, and what their listening patterns look like — with personality, not corporate blandness.

## Solution

TuneScript is an anonymous, session-only web app where users log in with Spotify OAuth, see 3–4 analysis panels of their own data, and leave without any account being created. No data is persisted beyond the session. The focus is on genuine data analysis (not just re-listing playlists) with a witty, irreverent tone.

## User Stories

1. As a Spotify user, I want to log in with my Spotify account without creating yet another account, so that I can see my stats immediately.
2. As a Spotify user, I want to see my top artists for the last 4 weeks, 6 months, and all time, so that I can compare what I'm into now vs historically.
3. As a Spotify user, I want to see my top tracks across the same time ranges, so that I can spot which songs define each era.
4. As a Spotify user, I want to see a genre breakdown of my all-time top artists, so that I can understand my "genre DNA."
5. As a Spotify user, I want to see how much my taste has changed (new artists vs loyal favorites vs faded ones), so that I can measure my listening evolution.
6. As a Spotify user, I want to see what time of day I listen most, so that I can confirm or discover my listening habits.
7. As a Spotify user, I want the UI to feel playful and human with witty captions, so that the experience is fun, not clinical.
8. As a developer contributing to the analysis layer, I want the stats queries to use Django ORM / SQL so that I can write and optimize analysis queries myself.

## Implementation Decisions

### Architecture

- **Stack:** Django 6.0.5 (templates, not REST API) + SQLite + Chart.js (CDN).
- **Frontend approach:** Server-rendered Django templates with Chart.js for visualizations. No SPA framework.
- **Auth:** Spotify OAuth 2.0 Authorization Code Flow (standard, not PKCE). No separate user accounts in the app.
- **Session model:** Anonymous sessions only. Data is fetched from Spotify on OAuth callback, stored in SQLite models keyed to the session, and displayed on the dashboard. Logout deletes the session's data.
- **Data scope:** `user-top-read` (top artists/tracks across 3 time ranges), `user-read-recently-played` (last 50 tracks), `user-library-read` (saved tracks — endpoint exists in service but not yet wired to a dashboard panel).

### Data Model

Three models:

- **AnalysisSession** — one per OAuth login. Stores `session_key`, `spotify_id`, `display_name`.
- **Artist** — FK to session. Stores `spotify_id`, `name`, `image_url`, `genres` (comma-separated), `popularity`, `time_range` (short/medium/long_term), `rank`.
- **Track** — FK to session. Stores `spotify_id`, `name`, `artist_name`, `album_name`, `album_image_url`, `duration_ms`, `time_range` (short/medium/long_term/recent), `rank`, `played_at` (nullable, only for recently played).

### Analysis Modules (MVP)

1. **Top Artists Panel** — Grid of profile photos, toggleable by short/medium/long term.
2. **Top Tracks Panel** — Ranked list, toggleable by time range.
3. **Genre DNA** — Doughnut chart aggregating genres from all-time top artists using `collections.Counter`.
4. **Taste Evolution** — Venn-style comparison: new faves (short-only), loyalties (both), faded (long-only). Doughnut chart + percentage stat with witty copy.
5. **Listening Times** — Optional panel. Buckets recently played tracks into morning/afternoon/evening/night.

### API Layer

- `spotify_data/spotify.py` — thin wrapper around `requests`. Functions map 1:1 to Spotify endpoints. No SDK dependency.
- OAuth flow: redirect to Spotify → callback exchanges code → fetches profile + top artists/tracks for all 3 time ranges + recently played. 7 API calls on login.

### Tone & Personality

- Brand: "TuneScript" with a music-note icon.
- Tags under each panel header are dynamically generated based on the data (e.g., "You've replaced 60% of your all-time faves. Who even are you anymore?")
- Dark theme with Spotify-green (#1db954) accents.

## Gaps Identified After Initial Build (To Polish)

1. **Hardcoded secrets** — `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are in `settings.py`. Move to environment variables / `.env`.
2. **No token refresh** — Access token expires in 1 hour. `refresh_access_token()` exists but is never called. For the session-only use case this is acceptable (data is fetched once on login), but if the callback itself takes too long, it could fail mid-way.
3. **No pagination** — `_fetch_all_pages()` helper exists but is unused. Top items are limited to 50. Good enough for MVP.
4. **Saved tracks not used on dashboard** — `get_saved_tracks()` and the `user-library-read` scope are unused. Could power a future "Library Stats" panel.
5. **Admin not registered** — Models not visible in Django admin. Low priority.
6. **No error handling for API rate limits** — No retry logic on 429 responses.
7. **No `.gitignore`** — `db.sqlite3`, `.DS_Store`, `__pycache__` may be tracked.
8. **No `requirements.txt`** — Dependencies not pinned.
9. **No tests** — `tests.py` is empty.

## Out of Scope (Future)

- User accounts and long-term data persistence
- Profile comparison between users
- Audio features analysis (blocked by Spotify API restrictions for dev-mode apps)
- Recommendations or playlist generation
- Mobile app / PWA
- Deployment to production (dev-mode capped at 5 users anyway)

## Further Notes

- The app is in Spotify's **Development Mode** (max 5 users, app owner needs Premium). Extended quota is not pursued.
- The Feb 2026 API lockdown removed `popularity`, `followers`, and batch endpoints. The app works within these constraints.
- The analysis queries in `views.py` use Django ORM. The user (intermediate SQL) is expected to refine these or replace them with raw SQL via `Model.objects.raw()` as they see fit.
