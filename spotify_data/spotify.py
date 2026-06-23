import base64
import requests
from datetime import datetime, timezone
from urllib.parse import urlencode

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE = 'https://api.spotify.com/v1'


def get_auth_url(client_id, redirect_uri):
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': 'user-top-read user-read-recently-played user-library-read',
        'show_dialog': 'false',
    }
    return f'{AUTH_URL}?{urlencode(params)}'


def exchange_code(client_id, client_secret, redirect_uri, code):
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    })
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id, client_secret, refresh_token):
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
    })
    resp.raise_for_status()
    return resp.json()


def _headers(access_token):
    return {'Authorization': f'Bearer {access_token}'}


def get_profile(access_token):
    resp = requests.get(f'{API_BASE}/me', headers=_headers(access_token))
    resp.raise_for_status()
    return resp.json()


def _fetch_all_pages(url, headers, params=None):
    items = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get('items', []))
        url = data.get('next')
        params = None
    return items


def get_top_artists(access_token, time_range='medium_term', limit=50):
    url = f'{API_BASE}/me/top/artists'
    params = {'time_range': time_range, 'limit': limit}
    resp = requests.get(url, headers=_headers(access_token), params=params)
    resp.raise_for_status()
    return resp.json().get('items', [])


def get_top_tracks(access_token, time_range='medium_term', limit=50):
    url = f'{API_BASE}/me/top/tracks'
    params = {'time_range': time_range, 'limit': limit}
    resp = requests.get(url, headers=_headers(access_token), params=params)
    resp.raise_for_status()
    return resp.json().get('items', [])


def get_recently_played(access_token, limit=50):
    url = f'{API_BASE}/me/player/recently-played'
    params = {'limit': limit}
    resp = requests.get(url, headers=_headers(access_token), params=params)
    resp.raise_for_status()
    return resp.json().get('items', [])


def get_saved_tracks(access_token, limit=50):
    url = f'{API_BASE}/me/tracks'
    params = {'limit': limit}
    resp = requests.get(url, headers=_headers(access_token), params=params)
    resp.raise_for_status()
    data = resp.json()
    return [item['track'] for item in data.get('items', [])]
