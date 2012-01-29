#!/usr/bin/env python

#from itunes import ITunes

import os
import logging 

from shutil import copy, Error
from itunes import iTunes, iTunesTrack, iTunesPlaylist

import wx
import wx.lib.filebrowsebutton as filebrowse
import wx.lib.anchors as anchors

logging.basicConfig(filename='/tmp/syncItunes.log', level=logging.DEBUG)

destination = None

def sync_tracks(tracks, progress=None):
    """ 
        Copies all of the tracks to the destination.
        Returns total tracks copied, total tracks skipped
    """

    count = 0
    for count,track in enumerate(tracks):
        if progress:
            (keep_going,skip) = progress.Update(count, 'Copying Track: %s' % track.name.encode('utf-8'))
            if not keep_going:
                return (count + 1, -1)
        logging.debug('Syncing {0}'.format(track.name.encode('utf-8')))
        copy_track(track)

    return (count + 1, len(tracks) - (count+1))

def sync_playlist(playlist, progress=None):
    """ 
        Create all playlists in m3u format. Copy music as we go... 
        Returns total tracks copied, total tracks skipped
    """

    total_tracks = len(playlist.tracks)
    count = 0

    playlist_dir = os.path.join(destination, 'Playlists')
    if not os.path.exists(playlist_dir):
        os.makedirs(playlist_dir)

    playlist_file_name = "{0}.m3u".format(os.path.join(playlist_dir, playlist.name.encode('utf-8')))
    playlist_file = open(playlist_file_name, 'w')

    for track in playlist.tracks:
        if not track.is_protected:
            (keep_going,skip) = progress.Update(count, 'Copying Track: %s' % track.name.encode('utf-8'))
            if not keep_going:
                return
            copy_track(track)
            track_path = relative_track_path(track)
            playlist_file.write(os.path.join('..', track_path.encode('utf-8')))
            playlist_file.write("\n")
            count = count + 1

    playlist_file.close()

    return (count, total_tracks - count)


def relative_track_path(track):
    """ Relative path for a track """

    track_file_name = os.path.basename(track.path)
    artist = track.albumArtist() or 'Unknown Artist'
    album = track.album() or 'Unknown Album'
    return os.path.join(artist, album, track_file_name)

def tracks_match(local, remote):
    """ md5 takes too long, so we will just check to see if the file sizes are identical """

    return os.path.getsize(local) == os.path.getsize(remote)

def copy_track(track):
    """ Makes sure to only copy tracks that need copying """

    src_track_file = track.path
    dst_track_file = os.path.join(destination, relative_track_path(track))
    
    if os.path.exists(src_track_file):
        if not os.path.exists(dst_track_file) or not tracks_match(src_track_file, dst_track_file):
            if not os.path.exists(os.path.dirname(dst_track_file)):
                os.makedirs(os.path.dirname(dst_track_file))
            copy(src_track_file, dst_track_file)
        

class MainFrame(wx.Frame):
    options = ['Sync all songs and playlists', 'Sync only songs', 'Choose playlist to sync']

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(540, 210))
        wx.Panel(self, -1, style=wx.TAB_TRAVERSAL|wx.CLIP_CHILDREN|wx.FULL_REPAINT_ON_RESIZE)

        filemenu = wx.Menu()
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.Bind(wx.EVT_MENU, self.on_close, menuExit)

        self.choice = MainFrame.options[0]
        choice = wx.Choice(self, -1, size=(500, -1), choices=MainFrame.options, pos=(20, 20))
        self.Bind(wx.EVT_CHOICE, self.set_choice, choice)
        filebrowse.DirBrowseButton(self, -1, size=(500, -1), pos=(20, 50), changeCallback=self.set_destination)

        cancel = wx.Button(self, 1, 'Cancel', pos=(330, 150))
        cancel.SetConstraints(
            anchors.LayoutAnchors(cancel, False, False, True, True)
        )
        sync = wx.Button(self, 2, 'Sync', pos=(430, 150))
        sync.SetConstraints(
            anchors.LayoutAnchors(sync, False, False, True, True)
        )
        self.Bind(wx.EVT_BUTTON, self.on_close, id=1)
        self.Bind(wx.EVT_BUTTON, self.on_sync, id=2)

        self.SetSizeHints(minW=540, minH=210, maxW=540, maxH=210)
        self.Show(True)

    def on_close(self, event):
        self.Close(True)

    def set_destination(self, evt):
        global destination
        destination = evt.GetString()

    def set_choice(self, evt):
        self.choice = evt.GetString()

    def on_sync(self, event):
        global destination

        itunes = iTunes()
        progress = None

        print "Destination is: {0}".format(destination)
        if not destination:
            msg = wx.MessageDialog(self, 'You must enter a destination directory first.', "Error", wx.OK|wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()
            return


        print "Choice is: {0}".format(self.choice)
        if self.choice == 'Sync all songs and playlists...':
            # First playlist should be the special 'Music' playlist, which has all tracks
            total_tracks = len(itunes.playlists()[0].tracks)
            progress = wx.ProgressDialog('Syncing iTunes Tracks', 'Copying track...', 
                    maximum=total_tracks, style=0|wx.PD_CAN_ABORT)
            (synced, skipped) = sync_playlists(itunes.playlists())
            msg = wx.MessageDialog(self, 'Synced {0} tracks. {1} tracks could not be synced due to DRM'.
                        format(synced, skipped), "Finished!", wx.OK | wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()

        if progress:
            progress.Destroy()


app = wx.App(False)
frame = MainFrame(None, 'Mac-Droid-Sync')
app.MainLoop()

