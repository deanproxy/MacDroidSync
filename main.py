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

    print repr(playlist.name)
    print "Total tracks to be synced: {0}".format(total_tracks)
    pl_name = playlist.name.decode('utf-8').encode('latin-1')
    playlist_file_name = "{0}.m3u".format(os.path.join(playlist_dir, pl_name))
    playlist_file = open(playlist_file_name, 'w')

    for track in playlist.tracks:
        print "Syncing track: {0}".format(track.name.encode('utf-8'))
        if not track.is_protected():
            (keep_going,skip) = progress.Update(count, 'Copying Track: %s' % track.name.encode('utf-8'))
            if not keep_going:
                return (count, -1)
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
    artist = track.albumArtist or 'Unknown Artist'
    album = track.album or 'Unknown Album'
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
    options = ['Sync all songs and playlists', 'Sync only songs', 'Sync only specified playlists']

    def __init__(self, parent, title):
        super(MainFrame, self).__init__(parent, title=title, size=(500, 400))

        # Set up the menu functionality
        menubar = wx.MenuBar()
        filemenu = wx.Menu()
        menubar.Append(filemenu,"&File") 
        self.SetMenuBar(menubar)

        # The box sizer that all widgets will fit in
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Set up the playlist selection
        self.selected_playlists = []
        itunes = iTunes()
        self.playlists = [p.name for p in itunes.playlists() if p.is_music_playlist()]
        self.plbox = wx.CheckListBox(self, 3, choices=self.playlists)
        self.Bind(wx.EVT_CHECKLISTBOX, self.set_playlists, id=3)

        # The directory browser
        dirbrowse = filebrowse.DirBrowseButton(self, labelText='Destination', startDirectory='/Volumes', 
                toolTip='Choose where to sync', changeCallback=self.set_destination, id=2) 
        dirbrowse.SetValue('Choose where to sync')
        dirbrowse.Disable()

        # The choice of what to do
        self.choice = wx.Choice(self, choices=MainFrame.options, id=1)
        self.Bind(wx.EVT_CHOICE, self.set_choice, id=1)

        # Our sync button
        self.sync_button = wx.Button(self, 4, 'Sync')
        self.Bind(wx.EVT_BUTTON, self.on_sync, id=4)

        vbox.AddMany([
            (dirbrowse, 0, wx.EXPAND|wx.ALL, 5),
            (self.choice, 0, wx.EXPAND|wx.ALL, 5),
            #(dirbrowse, 0, wx.EXPAND|wx.ALL, 5),
            # Set the proportion to 1 because we want the listbox to resize VERTICAL and HORIZONTAL
            (self.plbox, 1, wx.EXPAND|wx.ALL, 5),
            (self.sync_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT|wx.ALL, 5)
        ])

        # We're placing a boxsizer inside of a boxsizer so that we can get
        # a nice 20 pixel border (padding) around all elements.
        mainbox = wx.BoxSizer(wx.VERTICAL)
        mainbox.Add(vbox, 1, wx.EXPAND|wx.ALL, 20)

        # We have a default where all items are checked
        indexes = [idx for (idx,p) in enumerate(self.playlists)]
        self.plbox.SetChecked(indexes)

        self.SetSizer(mainbox)
        self.Show()

    def set_playlists(self, evt):
        index = evt.GetSelection()
        print "Current selection is: {0}".format(self.choice.GetCurrentSelection())
        if self.choice.GetCurrentSelection() != 2:
            # They have selected or deselected an element and have not choosen 
            # to specify the playlists they want. Change their choice for them.
            self.choice.SetSelection(2)

        if self.plbox.IsChecked(index):
            self.selected_playlists.append(index)
        elif index in self.selected_playlists:
            self.selected_playlists.pop(index)

        self.plbox.SetSelection(index) 
        
    def set_destination(self, evt):
        global destination
        destination = evt.GetString()

    def set_choice(self, evt):
        # TODO - We need to check all boxes if they select they want all playlists
        # We should also disable the boxes when they do choose that.
        if self.choice.GetCurrentSelection() == 0:
            indexes = [idx for (idx,p) in enumerate(self.playlists)]
            self.plbox.SetChecked(indexes)
        elif self.choice.GetCurrentSelection() == 1:
            # Clear all checked
            self.plbox.SetChecked([])

    def on_sync(self, event):
        global destination

        itunes = iTunes()
        progress = None

        print "Destination is: {0}".format(destination)
        if not destination or destination == 'Choose where to sync':
            msg = wx.MessageDialog(self, 'You must enter a destination directory first.', 
                    "Error", wx.OK|wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()
            return
        else:
            destination = os.path.join(destination, 'itunes', 'Music')


        print "Syncing to: {0}".format(destination)
        if self.choice.GetCurrentSelection() == 0:
            # First playlist should be the special 'Music' playlist, which has all tracks
            total_tracks = len(itunes.playlists()[0].tracks)
            progress = wx.ProgressDialog('Syncing iTunes Tracks', 'Copying track...', 
                    maximum=total_tracks, style=0|wx.PD_CAN_ABORT|wx.PD_ESTIMATED_TIME|wx.PD_REMAINING_TIME)
            # First we want to write all tracks under the Music playlist, but not write that as an m3u file
            tracks = [t for t in itunes.playlists()[0].tracks if not t.is_protected()]
            (synced, skipped) = sync_tracks(tracks, progress)
            if skipped == -1:
                # They canceled the sync progress
                return

            # Next, finish up by writing the playlists m3u files out
            playlists = [p for p in itunes.playlists() if p.is_music_playlist()]
            for playlist in playlists:
                (synced, skipped) = sync_playlist(playlist, progress)
                if skipped == -1:
                    # Canceled the sync
                    return

            msg = wx.MessageDialog(self, 'Synced {0} tracks. {1} tracks could not be synced due to DRM'.
                        format(synced, skipped), "Finished!", wx.OK | wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()

        if progress:
            progress.Destroy()


if __name__ == '__main__':
    app = wx.App()
    MainFrame(None, 'Mac-Droid-Sync')
    app.MainLoop()

