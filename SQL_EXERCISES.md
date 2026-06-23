# SQL Exercise Book — TuneScript

This document catalogs every SQL/ORM pattern used in the TuneScript project. Each exercise shows the Django ORM code, the equivalent raw SQL it generates, and what it computes.

Use these to practice translating between Django ORM and raw SQL.

---

## Setup

Run these queries using `python3 manage.py shell` or connect to the database directly:

```bash
sqlite3 db.sqlite3
.tables
.schema spotify_data_artist
.schema spotify_data_track
.schema spotify_data_analysissession
```

## Schema

```sql
-- AnalysisSession: one per login
CREATE TABLE spotify_data_analysissession (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key VARCHAR(40) NOT NULL UNIQUE,
    spotify_id VARCHAR(64) NOT NULL,
    display_name VARCHAR(256) NOT NULL,
    created_at DATETIME NOT NULL
);

-- Artist: top artists per session per time range
CREATE TABLE spotify_data_artist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id BIGINT REFERENCES spotify_data_analysissession(id),
    spotify_id VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    image_url VARCHAR(512) NOT NULL,
    genres TEXT NOT NULL,         -- comma-separated, often empty
    popularity INTEGER NOT NULL,
    time_range VARCHAR(16) NOT NULL,  -- short_term | medium_term | long_term
    rank INTEGER NOT NULL
);

-- Track: top tracks + recently played + saved
CREATE TABLE spotify_data_track (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id BIGINT REFERENCES spotify_data_analysissession(id),
    spotify_id VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    artist_name VARCHAR(256) NOT NULL,
    album_name VARCHAR(256) NOT NULL,
    album_image_url VARCHAR(512) NOT NULL,
    duration_ms INTEGER NOT NULL,
    time_range VARCHAR(16) NOT NULL,  -- short_term | medium_term | long_term | recent | saved
    rank INTEGER NOT NULL,
    played_at DATETIME               -- NULL for all except 'recent'
);
```

---

## Level 1: Basic Filter + Order

### Exercise 1.1 — Get top 10 all-time artists

**ORM:**
```python
session_obj.artists.filter(time_range='long_term').order_by('rank')[:10]
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'long_term'
ORDER BY rank ASC
LIMIT 10;
```

**What it does:** Returns the user's top 10 artists of all time, ordered by their rank (1 = most listened).

---

### Exercise 1.2 — Get recently played tracks from the last session

**ORM:**
```python
session_obj.tracks.filter(time_range='recent').order_by('rank')
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_track
WHERE session_id = ? AND time_range = 'recent'
ORDER BY rank ASC;
```

**What it does:** Returns the last 50 tracks you played, ordered by recency.

---

### Exercise 1.3 — Get a specific session by ID

**ORM:**
```python
AnalysisSession.objects.get(id=session_id)
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_analysissession WHERE id = ?;
```

**What it does:** Fetches a single session object. Raises an exception if not found.

---

## Level 2: Aggregation (Count, Sum, Avg)

### Exercise 2.1 — Count how many saved tracks you have

**ORM:**
```python
session_obj.tracks.filter(time_range='saved').count()
```

**Equivalent SQL:**
```sql
SELECT COUNT(*) FROM spotify_data_track
WHERE session_id = ? AND time_range = 'saved';
```

**What it does:** Counts the number of tracks saved to your library.

---

### Exercise 2.2 — Calculate total play time of all saved tracks

**ORM:**
```python
from django.db.models import Sum
session_obj.tracks.filter(time_range='saved').aggregate(total=Sum('duration_ms'))
```

**Equivalent SQL:**
```sql
SELECT SUM(duration_ms) AS total FROM spotify_data_track
WHERE session_id = ? AND time_range = 'saved';
```

**What it does:** Sums all track durations in milliseconds.

---

### Exercise 2.3 — Calculate average track length for short vs long term

**ORM:**
```python
from django.db.models import Avg
session_obj.tracks.filter(time_range='short_term').aggregate(avg=Avg('duration_ms'))
session_obj.tracks.filter(time_range='long_term').aggregate(avg=Avg('duration_ms'))
```

**Equivalent SQL:**
```sql
SELECT AVG(duration_ms) AS avg FROM spotify_data_track
WHERE session_id = ? AND time_range = 'short_term';

SELECT AVG(duration_ms) AS avg FROM spotify_data_track
WHERE session_id = ? AND time_range = 'long_term';
```

**What it does:** Computes the average song length for recent (4 week) and all-time top tracks.

---

### Exercise 2.4 — Check if any tracks exist in a time range

**ORM:**
```python
session_obj.tracks.filter(time_range='recent', played_at__isnull=False).exists()
```

**Equivalent SQL:**
```sql
SELECT EXISTS(
    SELECT 1 FROM spotify_data_track
    WHERE session_id = ? AND time_range = 'recent' AND played_at IS NOT NULL
) AS "exists";
```

**What it does:** Checks whether there's at least one recently played track with a timestamp.

---

## Level 3: Group By + Annotation

### Exercise 3.1 — Count how many tracks each artist has in your top lists

**ORM:**
```python
from django.db.models import Count
session_obj.tracks.filter(
    time_range__in=('short_term', 'medium_term', 'long_term')
).values('artist_name').annotate(count=Count('id')).order_by('-count')
```

**Equivalent SQL:**
```sql
SELECT artist_name, COUNT(id) AS count FROM spotify_data_track
WHERE session_id = ? AND time_range IN ('short_term', 'medium_term', 'long_term')
GROUP BY artist_name
ORDER BY count DESC;
```

**What it does:** Groups all your top tracks by artist and counts how many tracks each artist has. Used for Listening Concentration.

---

### Exercise 3.2 — Find which album has the most tracks in your top lists

**ORM:**
```python
session_obj.tracks.filter(
    time_range__in=('short_term', 'medium_term', 'long_term')
).values('album_name', 'artist_name').annotate(count=Count('id')).order_by('-count')
```

**Equivalent SQL:**
```sql
SELECT album_name, artist_name, COUNT(id) AS count FROM spotify_data_track
WHERE session_id = ? AND time_range IN ('short_term', 'medium_term', 'long_term')
GROUP BY album_name, artist_name
ORDER BY count DESC;
```

**What it does:** Groups by album (disambiguated by artist) and counts tracks per album. The first result is your Album Obsession.

---

### Exercise 3.3 — Find your top 5 most-saved artists

**ORM:**
```python
session_obj.tracks.filter(time_range='saved').values('artist_name').annotate(
    count=Count('id')
).order_by('-count')[:5]
```

**Equivalent SQL:**
```sql
SELECT artist_name, COUNT(id) AS count FROM spotify_data_track
WHERE session_id = ? AND time_range = 'saved'
GROUP BY artist_name
ORDER BY count DESC
LIMIT 5;
```

**What it does:** From your saved tracks library, finds the 5 artists you've saved the most tracks from.

---

## Level 4: Set Operations with values_list

Django ORM doesn't have SQL `INTERSECT`/`EXCEPT` directly, so we use Python set operations on querysets.

### Exercise 4.1 — Find artists present in all 3 time ranges (Commitment Score)

**ORM:**
```python
short = set(session_obj.artists.filter(time_range='short_term').values_list('spotify_id', flat=True))
medium = set(session_obj.artists.filter(time_range='medium_term').values_list('spotify_id', flat=True))
long_term = set(session_obj.artists.filter(time_range='long_term').values_list('spotify_id', flat=True))
committed = short & medium & long_term  # Python set intersection
```

**Equivalent SQL (would need multiple queries or INTERSECT):**
```sql
-- Query 1: Short term
SELECT spotify_id FROM spotify_data_artist WHERE session_id = ? AND time_range = 'short_term';
-- Query 2: Medium term
SELECT spotify_id FROM spotify_data_artist WHERE session_id = ? AND time_range = 'medium_term';
-- Query 3: Long term
SELECT spotify_id FROM spotify_data_artist WHERE session_id = ? AND time_range = 'long_term';
-- Equivalent single-query approach:
SELECT spotify_id, COUNT(DISTINCT time_range) FROM spotify_data_artist
WHERE session_id = ? AND time_range IN ('short_term', 'medium_term', 'long_term')
GROUP BY spotify_id
HAVING COUNT(DISTINCT time_range) = 3;
```

**What it does:** Finds artists that appear in all three time ranges — your ride-or-die artists.

---

### Exercise 4.2 — Find new vs faded artists (Taste Evolution)

**ORM:**
```python
short = set(session_obj.artists.filter(time_range='short_term').values_list('spotify_id', flat=True))
long_term = set(session_obj.artists.filter(time_range='long_term').values_list('spotify_id', flat=True))
new_faves = short - long_term                    # new discoveries
constants = short & long_term                    # loyal favorites
nostalgia = long_term - short                    # faded out
```

**Equivalent SQL:**
```sql
-- New faves (in short but not in long):
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'short_term'
EXCEPT
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'long_term';

-- Loyalties (in both):
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'short_term'
INTERSECT
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'long_term';

-- Nostalgia (in long but not in short):
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'long_term'
EXCEPT
SELECT spotify_id FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'short_term';
```

**What it does:** Using Python set difference/intersection to categorize artists by whether they're new, consistent, or faded.

---

### Exercise 4.3 — Get names for a set of artist IDs

**ORM:**
```python
session_obj.artists.filter(
    time_range='short_term',
    spotify_id__in=new_faves
).order_by('rank').values_list('name', flat=True)[:5]
```

**Equivalent SQL:**
```sql
SELECT name FROM spotify_data_artist
WHERE session_id = ?
  AND time_range = 'short_term'
  AND spotify_id IN ('id1', 'id2', 'id3', ...)
ORDER BY rank ASC
LIMIT 5;
```

**What it does:** Given a set of artist IDs, fetches their display names ordered by rank.

---

## Level 5: Filtering with `__in`

### Exercise 5.1 — Get all top tracks across multiple time ranges

**ORM:**
```python
session_obj.tracks.filter(
    time_range__in=('short_term', 'medium_term', 'long_term')
)
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_track
WHERE session_id = ? AND time_range IN ('short_term', 'medium_term', 'long_term');
```

**What it does:** Fetches tracks from all three top-list time ranges at once. The `__in` lookup maps to SQL `IN`.

---

### Exercise 5.2 — Get recently played tracks with a valid timestamp

**ORM:**
```python
session_obj.tracks.filter(time_range='recent', played_at__isnull=False)
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_track
WHERE session_id = ? AND time_range = 'recent' AND played_at IS NOT NULL;
```

**What it does:** Filters for recently played tracks that actually have a timestamp recorded.

---

## Level 6: Reverse FK Relations

### Exercise 6.1 — Access all artists for a session

**ORM:**
```python
session_obj.artists.all()   # Django automatically creates this reverse relation
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_artist WHERE session_id = ?;
```

**What it does:** The `related_name='artists'` on the `Artist.session` FK field lets you access all artists belonging to a session via `session_obj.artists`.

---

### Exercise 6.2 — Chain filters on reverse relations

**ORM:**
```python
session_obj.artists.filter(time_range='long_term').order_by('rank')
```

**Equivalent SQL:**
```sql
SELECT * FROM spotify_data_artist
WHERE session_id = ? AND time_range = 'long_term'
ORDER BY rank ASC;
```

**What it does:** Filters and orders the reverse relation. Same as a regular queryset.

---

## Level 7: Delete

### Exercise 7.1 — Delete a session and all its related data

**ORM:**
```python
AnalysisSession.objects.filter(id=session_id).delete()
```

**Equivalent SQL:**
```sql
-- Due to ON DELETE CASCADE, or Django's emulation:
DELETE FROM spotify_data_track WHERE session_id = ?;
DELETE FROM spotify_data_artist WHERE session_id = ?;
DELETE FROM spotify_data_analysissession WHERE id = ?;
```

**What it does:** Deletes the session and all associated artists and tracks (cascade).

---

## Practice Prompts

Try writing the ORM or SQL for these:

1. Get your top 5 most-played artists from the last 6 months.
2. Find all tracks longer than 5 minutes in your saved library.
3. Count how many unique artists appear across all your top lists.
4. Find the most common album name across your top tracks.
5. Calculate the percentage of recently played tracks that you also have saved.
6. Find artists that appear in short_term but NOT in medium_term.
7. Get the average popularity of your top 20 all-time artists.
8. Find your most-listened-to artist from each time range.
9. Calculate the total number of minutes of recently listened music.
10. Find if there are any duplicate track names across short and long term.
