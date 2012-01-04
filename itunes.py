#!/usr/bin/env python
#
# Author - Dean Jones - http://deanproxy.com
#
# A quick and hacky way of syncing your iTunes library and playlist with your
# android phone.  Done to get a grip on Foundation and Scripting Bridge support
# on the Mac.
#
# Options:
#   --destination /Location/Of/Your/Android/media/Music
#
# TODO
#   - Allow specifying which playlists to sync (show all playlists and enter numbers to sync)
#       - Example: 
#            1) Music
#            2) Bob's Playlist
#            3) Rock Music
#           ...
#           Enter the numbers for the playlists you want synced (or 'all' for everything): 
#   - Sync playlist and music not found or different from Android to iTunes
#   - Sync movies into movie folder (provide option to ignore movies too)
#   - Provide a --script option that makes output easier for machines to read.
#   - Make a simple GUI for it all with py2app.
#       Some notes for py2app notes found here: http://svn.pythonmac.org/py2app/py2app/trunk/doc/index.html#tutorial
#
# P.S. Please forgive the code... It deserves some cleanup.

import os
import sys
import urllib2
import urlparse
import logging

from shutil import copy, Error
from Foundation import *
from ScriptingBridge import *
from optparse import OptionParser

logging.basicConfig(filename='syncItunes.log', level=logging.DEBUG)


destination = ''

kind_blacklist = ['Protected AAC audio file']

def get_terminal_size():
    " Borrowed from the console python module "

    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])

progress_bar_iter = 0
def display_progress(percent):
    " Display a nice progress bar "

    global progress_bar_iter

    (console_width, console_height) = get_terminal_size()
    static_text_length = 24 # The length of static content in the progress bar
    console_width = console_width - static_text_length
    
    percent = int(percent)
    numeric_padding_len = 0
    if percent < 10:
        numeric_padding_len = 2
    elif percent < 100:
        numeric_padding_len = 1

    decimal_percent = float(percent) / 100.0
    numeric_padding = ' ' * numeric_padding_len
    bar = '=' * int(float(console_width) * decimal_percent)
    bar_padding = ' ' * (console_width - len(bar))
    if progress_bar_iter >= 3:
        progress_bar_iter = 1
    else:
        progress_bar_iter = progress_bar_iter + 1
    dots = '.' * progress_bar_iter
    dots_padding = ' ' * (3 - progress_bar_iter)
    sys.stdout.write("Copying music {0}{1}[{2}{3}] {4}{5}%\r".
            format(dots, dots_padding, bar, bar_padding, numeric_padding, percent)) 

    sys.stdout.flush()


def tracks_match(local, remote):
    " md5 takes too long, so we will just check to see if the file sizes are identical "

    return os.path.getsize(local) == os.path.getsize(remote)

def get_track_location(track):
    " Returns the absolute path to the iTunes track "

    location = urllib2.unquote(str(track.location()))
    return urlparse.urlparse(location)[2]

def relative_track_path(track):
    " Relative path for a track "

    track_file_name = os.path.basename(get_track_location(track))
    artist = track.artist() or 'Unknown Artist'
    album = track.album() or 'Unknown Album'
    return os.path.join(artist, album, track_file_name)

def copy_track(track):
    " Makes sure to only copy tracks that need copying "

    src_track_file = get_track_location(track)
    dst_track_file = os.path.join(destination, relative_track_path(track))
    
    if os.path.exists(src_track_file):
        if not os.path.exists(dst_track_file) or not tracks_match(src_track_file, dst_track_file):
            if not os.path.exists(os.path.dirname(dst_track_file)):
                os.makedirs(os.path.dirname(dst_track_file))
            copy(src_track_file, dst_track_file)
    

def copy_tracks(track_list):
    accepted_tracks = [i for i in track_list if i.kind() not in kind_blacklist]
    total_tracks = len(accepted_tracks)
    current_tracks_synced = 0

    logging.info("Syncing a total of {0} tracks. {1} were not able to be synced.".
            format(total_tracks, (len(track_list) - total_tracks)))

    for track in accepted_tracks:
        logging.debug('Syncing {0}'.format(track.name().encode('utf-8')))
        copy_track(track)
        percent = (float(current_tracks_synced) / float(total_tracks)) * 100
        current_tracks_synced = current_tracks_synced + 1
        display_progress(percent)


def create_playlists(playlists):
    " Create all playlists in m3u and plb format. Copy music as we go... "
    real_playlist_kind = 1800302446


    # The first playlist should be the Music playlist.
    print "\nCreating playlists..."
    sys.stdout.flush()
    for playlist in playlists:
        if playlist.specialKind() == real_playlist_kind:
            playlist_file_name = "{0}.m3u".format(os.path.join(destination, playlist.name().encode('utf-8')))
            playlist_file = open(playlist_file_name, 'w')
            for track in playlist.fileTracks():
                if track.kind() not in kind_blacklist:
                    track_path = relative_track_path(track)
                    playlist_file.write(track_path.encode('utf-8'))
                    playlist_file.write("\n")
            playlist_file.close()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--destination', dest='destination', 
                      help='The full path for the location to copy the music to.',
                      default='/Volumes/NO NAME 1/media/Music')

    (options, args) = parser.parse_args()
    destination = options.destination

    if not os.path.exists(destination):
        print "-- ERROR -- The destination path does not exist. Do you have your phone plugged in?: %s" % destination.encode('utf-8')
        exit(1)

    print "Connecting to iTunes...\r",
    sys.stdout.flush()

    itunes = SBApplication.applicationWithBundleIdentifier_("com.apple.iTunes")

    copy_tracks(itunes.sources()[0].userPlaylists()[0].fileTracks())
    create_playlists(itunes.sources()[0].userPlaylists())

