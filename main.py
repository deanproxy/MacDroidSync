#!/usr/bin/env python

#from itunes import ITunes

import os
import wx

class MainFrame(wx.Frame):
    options = ['Sync all songs and playlists', 'Sync only songs', 'Choose playlist to sync']

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(400, 210))

        filemenu = wx.Menu()
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.Bind(wx.EVT_MENU, self.on_close, menuExit)

        wx.Choice(self, -1, pos=(10, 20), size=(380, -1), choices = MainFrame.options)

        wx.Button(self, 1, 'Cancel', (210, 150))
        wx.Button(self, 2, 'Sync', (300, 150))
        self.Bind(wx.EVT_BUTTON, self.on_close, id=1)

        self.SetSizeHints(minW=400, minH=210, maxW=400, maxH=210)
        self.Show(True)

    def on_close(self, event):
        self.Close(True)


app = wx.App(False)
frame = MainFrame(None, 'Mac-Droid-Sync')
app.MainLoop()

