from collections import Counter
from datetime import datetime, timezone

from django.conf import settings
from django.db import models as db_models
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET

from . import spotify
from .models import AnalysisSession, Artist, Track


@require_GET
def login(request):
    auth_url = spotify.get_auth_url(
        settings.SPOTIFY_CLIENT_ID,
        settings.SPOTIFY_REDIRECT_URI,
    )
    return redirect(auth_url)


@require_GET
def callback(request):
    code = request.GET.get('code')
    error = request.GET.get('error')
    if error or not code:
        return render(request, 'error.html', {'message': f'Spotify denied access: {error}'})

    token_data = spotify.exchange_code(
        settings.SPOTIFY_CLIENT_ID,
        settings.SPOTIFY_CLIENT_SECRET,
        settings.SPOTIFY_REDIRECT_URI,
        code,
    )
    access_token = token_data['access_token']
    refresh_token = token_data.get('refresh_token')

    profile = spotify.get_profile(access_token)

    session = AnalysisSession.objects.create(
        session_key=request.session.session_key or 'anon',
        spotify_id=profile['id'],
        display_name=profile.get('display_name', 'Unknown'),
    )

    # Fetch and store top artists for all time ranges
    time_ranges = [('short_term', 'Last 4 Weeks'), ('medium_term', 'Last 6 Months'), ('long_term', 'All Time')]
    for tr_key, _ in time_ranges:
        raw_artists = spotify.get_top_artists(access_token, tr_key)
        for i, a in enumerate(raw_artists):
            Artist.objects.create(
                session=session,
                spotify_id=a['id'],
                name=a['name'],
                image_url=a['images'][0]['url'] if a.get('images') else '',
                genres=','.join(a.get('genres', [])),
                popularity=a.get('popularity', 0),
                time_range=tr_key,
                rank=i + 1,
            )

        raw_tracks = spotify.get_top_tracks(access_token, tr_key)
        for i, t in enumerate(raw_tracks):
            Track.objects.create(
                session=session,
                spotify_id=t['id'],
                name=t['name'],
                artist_name=t['artists'][0]['name'] if t.get('artists') else '',
                album_name=t['album']['name'] if t.get('album') else '',
                album_image_url=t['album']['images'][0]['url'] if t.get('album') and t['album'].get('images') else '',
                duration_ms=t.get('duration_ms', 0),
                time_range=tr_key,
                rank=i + 1,
            )

    # Fetch saved tracks
    raw_saved = spotify.get_saved_tracks(access_token)
    saved_track_count = 0
    for i, t in enumerate(raw_saved):
        Track.objects.create(
            session=session,
            spotify_id=t['id'],
            name=t['name'],
            artist_name=t['artists'][0]['name'] if t.get('artists') else '',
            album_name=t['album']['name'] if t.get('album') else '',
            album_image_url=t['album']['images'][0]['url'] if t.get('album') and t['album'].get('images') else '',
            duration_ms=t.get('duration_ms', 0),
            time_range='saved',
            rank=i + 1,
        )
    saved_track_count = len(raw_saved)

    # Fetch recently played
    raw_recent = spotify.get_recently_played(access_token)
    for i, item in enumerate(raw_recent):
        t = item['track']
        Track.objects.create(
            session=session,
            spotify_id=t['id'],
            name=t['name'],
            artist_name=t['artists'][0]['name'] if t.get('artists') else '',
            album_name=t['album']['name'] if t.get('album') else '',
            album_image_url=t['album']['images'][0]['url'] if t.get('album') and t['album'].get('images') else '',
            duration_ms=t.get('duration_ms', 0),
            time_range='recent',
            rank=i + 1,
            played_at=_parse_played_at(item.get('played_at')),
        )

    request.session['session_id'] = session.id
    request.session['display_name'] = session.display_name
    request.session['refresh_token'] = refresh_token
    request.session['access_token'] = access_token
    request.session['saved_track_count'] = saved_track_count

    return redirect('dashboard')


def _parse_played_at(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


@require_GET
def dashboard(request):
    session_id = request.session.get('session_id')
    if not session_id:
        return redirect('login')

    try:
        session_obj = AnalysisSession.objects.get(id=session_id)
    except AnalysisSession.DoesNotExist:
        return redirect('login')

    top_artists = _get_top_artists_by_range(session_obj)
    top_tracks = _get_top_tracks_by_range(session_obj)
    genre_data = _compute_genre_data(session_obj)
    taste_shift = _compute_taste_shift(session_obj)
    listening_times = _compute_listening_times(session_obj)
    commitment = _compute_commitment(session_obj)
    concentration = _compute_concentration(session_obj)
    album_obsession = _compute_album_obsession(session_obj)
    artist_movers = _compute_artist_movers(session_obj)
    recent_plays = _compute_recent_plays(session_obj)

    display_name = request.session.get('display_name', 'You')

    context = {
        'display_name': display_name,
        'top_artists': top_artists,
        'top_tracks': top_tracks,
        'genres': genre_data,
        'taste_shift': taste_shift,
        'listening_times': listening_times,
        'commitment': commitment,
        'concentration': concentration,
        'album_obsession': album_obsession,
        'artist_movers': artist_movers,
        'recent_plays': recent_plays,
    }
    return render(request, 'dashboard.html', context)


def _get_top_artists_by_range(session_obj):
    """Return dict of time_range -> list of artist dicts."""
    ranges = {}
    for tr in ('short_term', 'medium_term', 'long_term'):
        qs = session_obj.artists.filter(time_range=tr).order_by('rank')
        ranges[tr] = [
            {'name': a.name, 'rank': a.rank, 'image_url': a.image_url, 'genres': a.genres}
            for a in qs
        ]
    return ranges


def _get_top_tracks_by_range(session_obj):
    ranges = {}
    for tr in ('short_term', 'medium_term', 'long_term'):
        qs = session_obj.tracks.filter(time_range=tr).order_by('rank')
        ranges[tr] = [
            {
                'name': t.name,
                'artist_name': t.artist_name,
                'album_image_url': t.album_image_url,
                'rank': t.rank,
            }
            for t in qs
        ]
    return ranges


def _compute_genre_data(session_obj):
    genre_counter = Counter()
    for artist in session_obj.artists.filter(time_range='long_term'):
        for g in artist.genres.split(','):
            g = g.strip().lower()
            if g:
                genre_counter[g] += 1
    total = sum(genre_counter.values())
    if not total:
        return None
    top_genres = genre_counter.most_common(10)
    return {
        'labels': [g for g, _ in top_genres],
        'values': [c for _, c in top_genres],
        'total': total,
    }


def _compute_concentration(session_obj):
    tracks = session_obj.tracks.filter(
        time_range__in=('short_term', 'medium_term', 'long_term'),
    )
    if not tracks.exists():
        return None

    artist_counts = list(
        tracks.values('artist_name')
        .annotate(count=db_models.Count('id'))
        .order_by('-count')
    )
    total_tracks = sum(a['count'] for a in artist_counts)
    unique_artists = len(artist_counts)
    top_three_pct = round(
        sum(a['count'] for a in artist_counts[:3]) / total_tracks * 100
    ) if total_tracks else 0

    top_three = [
        {
            'name': a['artist_name'],
            'count': a['count'],
            'pct': round(a['count'] / total_tracks * 100) if total_tracks else 0,
        }
        for a in artist_counts[:3]
    ]

    others_count = total_tracks - sum(a['count'] for a in artist_counts[:3])
    others_pct = round(others_count / total_tracks * 100) if total_tracks else 0

    if top_three_pct > 60:
        label = 'Concentrated'
        tag = 'loyalist'
    elif top_three_pct > 35:
        label = 'Balanced'
        tag = 'curator'
    else:
        label = 'Diverse'
        tag = 'explorer'

    return {
        'label': label,
        'tag': tag,
        'unique_artists': unique_artists,
        'top_three_pct': top_three_pct,
        'others_pct': others_pct,
        'top_three': top_three,
        'total_tracks': total_tracks,
    }


def _compute_taste_shift(session_obj):
    """Compare short_term vs long_term top artists."""
    short_artists = set(
        session_obj.artists.filter(time_range='short_term').values_list('spotify_id', flat=True)
    )
    long_artists = set(
        session_obj.artists.filter(time_range='long_term').values_list('spotify_id', flat=True)
    )
    new_faves = short_artists - long_artists
    constants = short_artists & long_artists
    nostalgia = long_artists - short_artists

    new_faves_names = list(
        session_obj.artists.filter(
            time_range='short_term', spotify_id__in=new_faves
        ).order_by('rank').values_list('name', flat=True)[:5]
    )
    constants_names = list(
        session_obj.artists.filter(
            time_range='long_term', spotify_id__in=constants
        ).order_by('rank').values_list('name', flat=True)[:5]
    )

    return {
        'new_count': len(new_faves),
        'constant_count': len(constants),
        'nostalgia_count': len(nostalgia),
        'new_faves': new_faves_names,
        'constants': constants_names,
        'shift_pct': round(len(new_faves) / max(len(short_artists), 1) * 100),
    }


def _compute_listening_times(session_obj):
    """Analyze recently played tracks for time-of-day patterns."""
    recent = session_obj.tracks.filter(time_range='recent', played_at__isnull=False)
    if not recent.exists():
        return None

    buckets = {'morning': 0, 'afternoon': 0, 'evening': 0, 'night': 0}
    for t in recent:
        hour = t.played_at.hour
        if 5 <= hour < 12:
            buckets['morning'] += 1
        elif 12 <= hour < 17:
            buckets['afternoon'] += 1
        elif 17 <= hour < 22:
            buckets['evening'] += 1
        else:
            buckets['night'] += 1

    top_bucket = max(buckets, key=buckets.get)
    return {
        'buckets': buckets,
        'top_bucket': top_bucket,
        'total': recent.count(),
    }


def _compute_commitment(session_obj):
    artists_short = set(
        session_obj.artists.filter(time_range='short_term').values_list('spotify_id', flat=True)
    )
    artists_med = set(
        session_obj.artists.filter(time_range='medium_term').values_list('spotify_id', flat=True)
    )
    artists_long = set(
        session_obj.artists.filter(time_range='long_term').values_list('spotify_id', flat=True)
    )
    committed = artists_short & artists_med & artists_long
    unique_all = artists_short | artists_med | artists_long

    committed_names = list(
        session_obj.artists.filter(
            time_range='long_term', spotify_id__in=committed
        ).order_by('rank').values_list('name', flat=True)[:5]
    )

    return {
        'count': len(committed),
        'total_unique': len(unique_all),
        'score': round(len(committed) / max(len(unique_all), 1) * 100),
        'committed_artists': committed_names,
    }


def _compute_album_obsession(session_obj):
    all_top_tracks = session_obj.tracks.filter(
        time_range__in=('short_term', 'medium_term', 'long_term'),
    )
    if not all_top_tracks.exists():
        return None

    album_counts = (
        all_top_tracks.values('album_name', 'artist_name')
        .annotate(count=db_models.Count('id'))
        .order_by('-count')
    )
    top = album_counts.first()
    if not top or top['count'] < 2:
        return None

    return {
        'album': top['album_name'],
        'artist': top['artist_name'],
        'track_count': top['count'],
    }


def _compute_artist_movers(session_obj):
    short_ranked = {
        a.spotify_id: {'name': a.name, 'rank': a.rank}
        for a in session_obj.artists.filter(time_range='short_term')
    }
    long_ranked = {
        a.spotify_id: {'name': a.name, 'rank': a.rank}
        for a in session_obj.artists.filter(time_range='long_term')
    }

    movers = []
    for sid, sa in short_ranked.items():
        if sid in long_ranked:
            diff = long_ranked[sid]['rank'] - sa['rank']
            if diff != 0:
                movers.append({
                    'name': sa['name'],
                    'old_rank': long_ranked[sid]['rank'],
                    'new_rank': sa['rank'],
                    'change': diff,
                    'direction': 'up' if diff > 0 else 'down',
                })

    movers.sort(key=lambda x: abs(x['change']), reverse=True)

    return {
        'top_gainers': [m for m in movers if m['direction'] == 'up'][:3],
        'top_losers': [m for m in movers if m['direction'] == 'down'][:3],
        'total_movers': len(movers),
    }


def _compute_recent_plays(session_obj):
    recent = session_obj.tracks.filter(time_range='recent', played_at__isnull=False)
    if not recent.exists():
        return None

    from collections import Counter
    artist_counter = Counter()
    track_counter = Counter()
    day_counter = Counter()
    hour_counter = Counter()

    for t in recent:
        artist_counter[t.artist_name] += 1
        track_counter[f'{t.name} — {t.artist_name}'] += 1
        day_counter[t.played_at.strftime('%A')] += 1
        hour_counter[t.played_at.hour] += 1

    top_artist = artist_counter.most_common(1)[0]
    top_track = track_counter.most_common(1)[0]
    top_day = day_counter.most_common(1)[0]
    peak_hour = hour_counter.most_common(1)[0]

    return {
        'total_plays': recent.count(),
        'top_artist': {'name': top_artist[0], 'plays': top_artist[1]},
        'top_track': {'name': top_track[0], 'plays': top_track[1]},
        'top_day': {'name': top_day[0], 'plays': top_day[1]},
        'peak_hour': f'{peak_hour[0]}:00',
        'day_breakdown': dict(day_counter.most_common()),
    }


@require_GET
def logout_view(request):
    session_id = request.session.get('session_id')
    if session_id:
        AnalysisSession.objects.filter(id=session_id).delete()
    request.session.flush()
    return redirect('landing')


@require_GET
def landing(request):
    if request.session.get('session_id'):
        return redirect('dashboard')
    return render(request, 'landing.html')
