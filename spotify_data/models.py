from django.db import models


class AnalysisSession(models.Model):
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    spotify_id = models.CharField(max_length=64, blank=True)
    display_name = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'spotify_data'


class Artist(models.Model):
    session = models.ForeignKey(
        AnalysisSession, on_delete=models.CASCADE, related_name='artists'
    )
    spotify_id = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    image_url = models.URLField(max_length=512, blank=True)
    genres = models.TextField(blank=True, help_text="Comma-separated genres")
    popularity = models.IntegerField(default=0)
    time_range = models.CharField(max_length=16, default='medium_term')
    rank = models.IntegerField(default=0)

    class Meta:
        app_label = 'spotify_data'


class Track(models.Model):
    session = models.ForeignKey(
        AnalysisSession, on_delete=models.CASCADE, related_name='tracks'
    )
    spotify_id = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    artist_name = models.CharField(max_length=256)
    album_name = models.CharField(max_length=256, blank=True)
    album_image_url = models.URLField(max_length=512, blank=True)
    duration_ms = models.IntegerField(default=0)
    time_range = models.CharField(max_length=16, default='medium_term')
    rank = models.IntegerField(default=0)
    played_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'spotify_data'
