from django.contrib import admin

from .models import AnalysisSession, Artist, Track


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'spotify_id', 'created_at')
    search_fields = ('display_name', 'spotify_id')


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'time_range', 'rank', 'session')
    list_filter = ('time_range',)
    search_fields = ('name',)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'artist_name', 'time_range', 'rank', 'session')
    list_filter = ('time_range',)
    search_fields = ('name', 'artist_name')
