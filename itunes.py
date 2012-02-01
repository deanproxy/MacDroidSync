# Author - Dean Jones - http://deanproxy.com
#
# ITunes class to sync from itunes to destination.

import os
import sys
import urllib2
import urlparse

# from Foundation import *
from ScriptingBridge import SBApplication


class iTunesTrack(object):

    def __init__(self, track):
        """ represents the essential information for a track """

        self.name = track.name()
        self.albumArtist = track.albumArtist()
        self.album = track.album()
        self.artist = track.artist()
        self.kind = track.kind()
        self.size = track.size()
        self.path = self._get_track_location(track)

    def is_protected(self):
        kind_blacklist = ['Protected AAC audio file']
        return self.kind in kind_blacklist

    def _get_track_location(self, track):
        """ Returns the absolute path to the iTunes track """

        location = urllib2.unquote(str(track.location()))
        return urlparse.urlparse(location)[2]


class iTunesPlaylist(object):
    def __init__(self, playlist):
        """ represents the essential information for a playlist """

        self.name = playlist.name()
        self.kind = playlist.specialKind()
        self.tracks = [iTunesTrack(i) for i in playlist.fileTracks()]

    def tracks_in_playlist(self, playlist):
        """ Returns an array of iTunesTrack """

        return self.tracks

    def is_music_playlist(self):
        real_playlist_kind = 1800302446
        return self.kind == real_playlist_kind

class iTunes(object):
    def __init__(self):
        """ opens the iTunes library """

        self.itunes = SBApplication.applicationWithBundleIdentifier_("com.apple.iTunes")

    def playlists(self):
        """ Returns all of the playlists available as an array of iTunesPlaylist """

        return [iTunesPlaylist(p) for p in self.itunes.sources()[0].userPlaylists()]

    def tracks(self):
        """ returns all tracks from the primary playlist (Music playlist) 
            which should be every track available as an array of iTunesTrack """

        return [iTunesTrack(t) for t in self.itunes.sources()[0].userPlaylists()[0].fileTracks()]

