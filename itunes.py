#!/usr/bin/env python
#
# Author - Dean Jones - http://deanproxy.com
#
# ITunes class to sync from itunes to destination.

import os
import sys
import urllib2
import urlparse
import logging

from shutil import copy, Error
from Foundation import *
from ScriptingBridge import *

import wx

logging.basicConfig(filename='/tmp/syncItunes.log', level=logging.DEBUG)

kind_blacklist = ['Protected AAC audio file']

class ITunes(object):
    def __init__(self, destination):
        """ opens the iTunes library """

        self.destination = destination
        self.itunes = SBApplication.applicationWithBundleIdentifier_("com.apple.iTunes")

    def sync(self):
        """" Copies all of the tracks to the destination """

        track_list = self.itunes.sources()[0].userPlaylists()[0].fileTracks()
        accepted_tracks = [i for i in track_list if i.kind() not in kind_blacklist]
        total_tracks = len(accepted_tracks)

        logging.info("Syncing a total of {0} tracks. {1} were not able to be synced.".
                format(total_tracks, (len(track_list) - total_tracks)))

        progress = wx.ProgressDialog('Syncing iTunes Tracks', 'Copying track...', 
                maximum=total_tracks, style=0|wx.PD_CAN_ABORT)
        for count,track in enumerate(accepted_tracks):
            (keep_going,skip) = progress.Update(count, 'Copying Track: %s' % track.name().encode('utf-8'))
            if not keep_going:
                break
            logging.debug('Syncing {0}'.format(track.name().encode('utf-8')))
            self._copy_track(track)

        progress.Update(total_tracks, 'Creating playlists...')
        self._create_playlists()
        progress.Destroy()

    def _create_playlists(self):
        """ Create all playlists in m3u format. Copy music as we go... """

        real_playlist_kind = 1800302446
        playlists = self.itunes.sources()[0].userPlaylists()

        # The first playlist should be the Music playlist.
        for playlist in playlists:
            if playlist.specialKind() == real_playlist_kind:
                playlist_file_name = "{0}.m3u".format(os.path.join(self.destination, playlist.name().encode('utf-8')))
                playlist_file = open(playlist_file_name, 'w')
                for track in playlist.fileTracks():
                    if track.kind() not in kind_blacklist:
                        track_path = self._relative_track_path(track)
                        playlist_file.write(track_path.encode('utf-8'))
                        playlist_file.write("\n")
                playlist_file.close()

    def _tracks_match(self, local, remote):
        """ md5 takes too long, so we will just check to see if the file sizes are identical """

        return os.path.getsize(local) == os.path.getsize(remote)

    def _get_track_location(self, track):
        """ Returns the absolute path to the iTunes track """

        location = urllib2.unquote(str(track.location()))
        return urlparse.urlparse(location)[2]

    def _relative_track_path(self, track):
        """ Relative path for a track """

        track_file_name = os.path.basename(get_track_location(track))
        artist = track.artist() or 'Unknown Artist'
        album = track.album() or 'Unknown Album'
        return os.path.join(artist, album, track_file_name)

    def _copy_track(self, track):
        """ Makes sure to only copy tracks that need copying """

        src_track_file = self._get_track_location(track)
        dst_track_file = os.path.join(self.destination, self._relative_track_path(track))
        
        if os.path.exists(src_track_file):
            if not os.path.exists(dst_track_file) or not self._tracks_match(src_track_file, dst_track_file):
                if not os.path.exists(os.path.dirname(dst_track_file)):
                    os.makedirs(os.path.dirname(dst_track_file))
                copy(src_track_file, dst_track_file)
        
