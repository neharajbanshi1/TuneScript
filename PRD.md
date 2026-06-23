# PRD: TuneScript — Spotify Data Analysis Dashboard

## Problem Statement

Spotify users have years of listening history but no easy, privacy-respecting way to see meaningful analysis of their own taste. Existing third-party platforms require accounts, store data permanently, and bury insights behind paywalls. Users want a lightweight, zero-commitment dashboard that shows who they actually listen to, how their taste evolves, and what their listening patterns look like — with personality, not corporate blandness.

## Solution

TuneScript is an anonymous, session-only web app where users log in with Spotify OAuth, see analysis panels of their own data, and leave without any account being created. No data is persisted beyond the session. The focus is on genuine data analysis (not just re-listing playlists) with a witty, irreverent tone.

## User Stories

1. As a Spotify user, I want to log in with my Spotify account without creating yet another account, so that I can see my stats immediately.
2. As a Spotify user, I want to see my top artists for the last 4 weeks, 6 months, and all time, so that I can compare what I'm into now vs historically.
3. As a Spotify user, I want to see my top tracks across the same time ranges, so that I can spot which songs define each era.
4. As a Spotify user, I want to see how much my taste has changed (new artists vs loyal favorites vs faded ones), so that I can measure my listening evolution.
5. As a Spotify user, I want to see what time of day I listen most, so that I can confirm or discover my listening habits.
6. As a Spotify user, I want to see my saved library stats (total tracks, hours, most-saved artists), so that I can understand my collection.
7. As a Spotify user, I want to see which artists survived across all time ranges (commitment score), so that I know my real ride-or-die favorites.
8. As a Spotify user, I want to see how concentrated my listening is across artists, so that I know if I'm a loyalist, curator, or explorer.
9. As a Spotify user, I want to see which single album I've listened to most, so that I know my current obsession.
10. As a Spotify user, I want to see if my genre count is expanding or narrowing, so that I can track my adventurousness.
11. As a Spotify user, I want to see if my average song length is changing, so that I can measure my attention span.
12. As a Spotify user, I want the UI to feel playful and human with witty captions, so that the experience is fun, not clinical.
13. As a developer contributing to the analysis layer, I want the stats queries to use Django ORM / SQL, so that I can write and optimize analysis queries myself.

## Implementation Decisions

### Architecture

- **Stack:** Django 6.0.5 (templates, not REST API) + SQLite + Chart.js (CDN).
- **Frontend approach:** Server-rendered Django templates with Chart.js for visualizations. No SPA framework.
- **Auth:** Spotify OAuth 2.0 Authorization Code Flow (standard, not PKCE). No separate user accounts in the app.
- **Session model:** Anonymous sessions only. Data is fetched from Spotify on OAuth callback, stored in SQLite models keyed to the session, and displayed on the dashboard. Logout deletes the session's data.
- **Data scope:** `user-top-read` (top artists/tracks across 3 time ranges), `user-read-recently-played` (last 50 tracks), `user-library-read` (saved tracks).

### Data Model

Three models:

- **AnalysisSession** — one per OAuth login. Stores `session_key`, `spotify_id`, `display_name`.
- **Artist** — FK to session. Stores `spotify_id`, `name`, `image_url`, `genres` (comma-separated; note: Spotify returns empty for most artists), `popularity`, `time_range` (short/medium/long_term), `rank`.
- **Track** — FK to session. Stores `spotify_id`, `name`, `artist_name`, `album_name`, `album_image_url`, `duration_ms`, `time_range` (short/medium/long_term/recent/saved), `rank`, `played_at` (nullable, only for recently played).

### Analysis Modules (Current)

1. **Top Artists Panel** — Grid of profile photos, toggleable by short/medium/long term.
2. **Top Tracks Panel** — Ranked list, toggleable by time range.
3. **Listening Concentration** — Measures how many unique artists appear in your top tracks and what % is dominated by the top 3. Visual bar chart of top 3 vs others. Assigns a personality tag: Loyalist, Curator, or Explorer.
4. **Taste Evolution** — Venn-style comparison: new faves (short-only), loyalties (both short+long), faded (long-only). Doughnut chart + percentage stat with witty copy.
5. **Commitment Score** — Artists present in all 3 time ranges (short, medium, long). Lists your ride-or-die artists with percentage score.
6. **Album Obsession** — Which single album has the most tracks in your top lists. Shows album name, artist, and track count.
7. **Attention Span** — Compares average song duration of recent (4 weeks) vs all-time top tracks. Positive diff = shorter attention span.
8. **Adventurousness** — Unique genre count per time range. Compares recent vs long-term. Tags as "expanding", "narrowing", or "stable".
9. **Saved Library** — Total saved tracks, total hours of music, top 5 most-saved artists.
10. **Listening Times** — Optional panel. Buckets recently played tracks into morning/afternoon/evening/night with doughnut chart.

### API Layer

- `spotify_data/spotify.py` — thin wrapper around `requests`. Functions map 1:1 to Spotify endpoints. No SDK dependency.
- Includes: `_fetch` helper with 429 retry + backoff, individual artist lookups for genre enrichment.
- OAuth flow: redirect to Spotify -> callback exchanges code -> fetches profile + top artists/tracks for all 3 time ranges + recently played + saved tracks. ~8 API calls on login.

### Tone & Personality

- Brand: "TuneScript" with a music-note icon.
- Each card has dynamically generated witty captions based on the user's data.
- Dark theme with Spotify-green (#1db954) accents.

## Out of Scope (Future)

- User accounts and long-term data persistence
- Profile comparison between users
- Audio features analysis (blocked by Spotify API for dev-mode apps)
- Recommendations or playlist generation
- Genre-based analysis (Spotify API returns empty genres for most artists)
- Deployment to production (dev-mode capped at 5 users)

## Further Notes

- The app is in Spotify's **Development Mode** (max 5 users, app owner needs Premium). Extended quota is not pursued.
- The Feb 2026 API lockdown removed `popularity`, `followers`, batch endpoints, and genre data for dev-mode apps. The app works within these constraints.
- All analysis queries are in `views.py` using Django ORM. A companion SQL exercise book (`SQL_EXERCISES.md`) catalogs every ORM pattern used.
