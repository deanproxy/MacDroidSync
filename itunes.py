#!/usr/bin/env python
#
# Author - Dean Jones - http://deanproxy.com
#
# A quick and hacky way of syncing your iTunes library and playlist with your
# android phone.  You provide the path to your iTunes Library.xml and the destination
# to the place that you want your music copied to and it will hook you up.
# 
# It will create both m3u and plb playlist files.  plb files work best with the 
# samsung default music app while m3u files work with almost any player.  They're
# essentially the exact same format so I have no clue why samsung decided it only 
# wanted a file with an odd plb extention.
#
# Options:
#   --library /Location/Of/Your/iTunes Library.xml
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
import logging

from shutil import copy
from Foundation import *
from optparse import OptionParser

logging.basicConfig(filename='syncItunes.log', level=logging.DEBUG)


library_file = ''
destination = ''
music_dir = ''

def tracks_match(local, remote):
    " md5 takes too long, so we will just check to see if the file sizes are identical "

    return os.path.getsize(local) == os.path.getsize(remote)

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

def copy_track(track):
    " Makes sure to only copy tracks that need copying "

    did_copy = False

    # Need to strip the leading / off for join to work
    src = os.path.join(music_dir, track[1:])
    dst = os.path.join(destination, os.path.dirname(track[1:]))
    track_file_name = os.path.basename(src)
    dst_file = os.path.join(dst, track_file_name)
    if os.path.exists(src):
        if not os.path.exists(dst_file) or not tracks_match(src, dst_file):
            if not os.path.exists(dst):
                os.makedirs(dst)
            copy(src, dst)
            did_copy = True

    return did_copy


def get_tracks(db):
    " Get track info from approved track types "

    tracks = {}
    total_tracks = 0
    accepted_kinds = ['AAC audio file', 'MPEG audio file', 'Purchased AAC audio file', 'WAV audio file']
    file_protocol_len = 16 # file://localhost length
    location_splice_len = len(music_dir)

    for track in db['Tracks'].itervalues():
        if track['Kind'] in accepted_kinds:
            location = urllib2.url2pathname(track['Location'])[file_protocol_len:]
            new_location = location[location_splice_len:]
            tracks[track['Track ID']] = new_location
            total_tracks = total_tracks + 1
        else:
            logging.info('Excluding file of kind: "{0}" -> "{1}"'.format(track['Kind'], track['Name']))

    logging.info('Total tracks found: {0}'.format(total_tracks))
    return tracks


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

def create_playlists(db, tracks):
    " Create all playlists in m3u and plb format. Copy music as we go... "

    playlist_blacklist = ['Library', 'Movies', 'TV Shows', 'Books', 'iTunes DJ', 
                          'Top 25 Most Played', 'Purchased', 'My Top Rated', 'Recently Added',
                          'Recently Played']
    # Get the terminal size so we can display a progress bar
    total_tracks = len(tracks)
    current_tracks_synced = 0
    print "Syncing {0} total tracks.\r".format(total_tracks),
    logging.info("Syncing {0} total tracks.".format(total_tracks))
    for playlist in db['Playlists'].itervalues():
        if playlist['Name'] in playlist_blacklist:
            logging.info('Excluding playlist "{0}"'.format(playlist['Name']))
            continue
        if 'Playlist Items' in playlist:
            playlist_file_name = "{0}.m3u".format(os.path.join(destination, playlist['Name'].encode('utf-8')))
            playlist_file = open(playlist_file_name, 'w')
            for item in playlist['Playlist Items'].itervalues():
                track_id = item['Track ID']
                if track_id in tracks:
                    track = tracks[track_id]
                    logging.debug('Syncing file {0}'.format(track.encode('utf-8')))
                    if copy_track(track):
                        current_tracks_synced = current_tracks_synced + 1
                        logging.debug("Synced track {0} - {1}".format(current_tracks_synced, track.encode('utf-8')))

                    # If all tracks have been synced, inform that we're creating the playlists now
                    if current_tracks == total_tracks:
                        current_tracks = current_tracks + 1
                        print "\nCreating playlists..."
                    else:
                        percent = (float(current_tracks_synced) / float(total_tracks)) * 100
                        display_progress(percent)
                    playlist_file.write("{0}\n".format(track.encode('utf-8')))

            playlist_file.close()

            # Copy the file to a plb file (since they're the same format by removing the m3u extension
            copy(playlist_file_name, "{0}.plb".format(playlist_file_name[:-4]))


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-l', '--library', 
                      dest='library', 
                      help='The full path to your iTunes Library.xml file.',
                      default='/Volumes/Media/iTunes/iTunes Library.xml')
    parser.add_option('-d', '--destination', dest='destination', 
                      help='The full path for the location to copy the music to.',
                      default='/Volumes/NO NAME 1/media/Music')

    (options, args) = parser.parse_args()
    library_file = options.library
    destination = options.destination
    music_dir = os.path.join(os.path.dirname(library_file), 'iTunes Media', 'Music')
    db = NSDictionary.dictionaryWithContentsOfFile_(library_file)

    print "Getting all track info...\r",
    tracks = get_tracks(db)
    create_playlists(db, tracks)

