import wx
import requests
import os
import sys
import json
from io import BytesIO
import support.shazamsupport as shazamsupport
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC

class FindSong:
    def __init__(self, parent):
        self.parent = parent
        self.files = []
        self.frame = wx.Frame(parent, -1, "SongFind", size=(550, 200))
        self.shazam = shazamsupport.Shazam()
        self.default = wx.Image('resources/cd_label.png', wx.BITMAP_TYPE_PNG).Rescale(50, 50, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()

        self.image_list = wx.ImageList(50, 50)

        self.image_list.Add(self.default)

        panel = wx.Panel(self.frame, -1)
        self.CreateUI(panel)
        # resize to force the listctrl to expand
        self.frame.SetSize((551, 201))
        self.frame.SetSize((550, 200))

        # set minimum size
        self.frame.SetMinSize((550, 200))

        # prevent horizontal resizing
        self.frame.SetMaxSize((550, 999999))

        # add the get started overlay image
        self.overlay = wx.StaticBitmap(panel, -1, bitmap=wx.Bitmap('resources/getstarted.png', wx.BITMAP_TYPE_ICON), pos=(200, 20))
        self.overlay.SetSize((200,97))


        self.frame.Show()




    def CreateUI(self, panel):
        vbox = wx.BoxSizer(wx.VERTICAL)

        toolbar = self.frame.CreateToolBar(style=wx.TB_TEXT)

        select_tool = toolbar.AddTool(wx.ID_ANY, 'Load Songs', wx.Bitmap('resources/plus.png'))
        toolbar.Realize()
        toolbar.Bind(wx.EVT_TOOL, self.OnSelectFiles, select_tool)

        process_tool = toolbar.AddTool(wx.ID_ANY, 'Process', wx.Bitmap('resources/process.png'))
        toolbar.Realize()
        toolbar.Bind(wx.EVT_TOOL, self.OnFind, process_tool)

        metadata_tool = toolbar.AddTool(wx.ID_ANY, 'Save Meta', wx.Bitmap('resources/save.png'))
        toolbar.Realize()
        toolbar.Bind(wx.EVT_TOOL, self.OnSave, metadata_tool)


        # hide columns headers
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_NO_HEADER)
        # track title / file name
        self.list_ctrl.InsertColumn(1, 'Track', width=550)

        # enable image list
        self.list_ctrl.SetImageList(self.image_list, wx.IMAGE_LIST_SMALL)

        # add a double click event to view song info
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnSongInfo)




        vbox.Add(self.list_ctrl, proportion=1, flag=wx.EXPAND)

        panel.SetSizer(vbox)

    def OnSongInfo(self, event):
        index = event.GetIndex()
        song_file = self.files[index]
        self.ShowSongInfo(song_file)

    def ShowSongInfo(self, song_file):
        # if the song info is not created yet, get it right now
        if len(song_file) < 3:
            result = self.shazam.recognize(song_file[0])
            cover = requests.get(result['track']['images']['coverart']).content
            song_file.append(result)
            song_file.append(cover)

        # create a new frame
        frame = wx.Frame(None, -1, "Song Info", size=(500, 600))

        vbox = wx.BoxSizer(wx.VERTICAL)
        panel = wx.Panel(frame, -1)
        panel.SetSizer(vbox)
        # add the song info
        title = wx.StaticText(panel, -1, f"Title: {song_file[2]['track']['title']}")
        artist = wx.StaticText(panel, -1, f"Artist: {song_file[2]['track']['subtitle']}")
        album = wx.StaticText(panel, -1, f"Album: {song_file[2]['track']['sections'][0]['metadata'][0]['text']}")
        date = wx.StaticText(panel, -1, f"Date: {song_file[2]['track']['sections'][0]['metadata'][2]['text']}")
        genre = wx.StaticText(panel, -1, f"Genre: {song_file[2]['track']['genres']['primary']}")

        # add full info in a text control
        full_info = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE)
        full_info.AppendText(json.dumps(song_file[2], indent=4))

        #smaller font
        font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        full_info.SetFont(font)




        # cover
        image = wx.ImageFromStream(BytesIO(song_file[3]))

        cover = wx.StaticBitmap(panel, -1, image.Rescale(200, 200, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap())

        vbox.Add(cover, 0, wx.ALL, 5)
        vbox.Add(title, 0, wx.ALL, 5)
        vbox.Add(artist, 0, wx.ALL, 5)
        vbox.Add(album, 0, wx.ALL, 5)
        vbox.Add(date, 0, wx.ALL, 5)
        vbox.Add(genre, 0, wx.ALL, 5)
        vbox.Add(full_info, 1, wx.EXPAND | wx.ALL, 5)

        # show the frame
        frame.Show()




    def OnSelectFiles(self, event):
        # hide the get started overlay
        self.overlay.Destroy()

        with wx.FileDialog(self.frame, message='', wildcard="Audio files (*.wav, *.mp3, *.flac, *.aac, *.m4a)|*.wav;*.mp3;*.flac;*.aac;*.m4a",
                           style=wx.FD_OPEN | wx.FD_MULTIPLE) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            paths = fileDialog.GetPaths()
            for path in paths:
                if path not in self.files:
                    count = self.list_ctrl.GetItemCount()
                    index = self.list_ctrl.InsertItem(count, path)
                    #image
                    self.list_ctrl.SetItemImage(index, 0)

                    self.files.append([path, index])

    def OnFind(self, event):
        for file in self.files:
            result = self.shazam.recognize(file[0])


            cover = requests.get(result['track']['images']['coverart']).content

            file.append(result)
            file.append(cover)


            image = wx.ImageFromStream(BytesIO(cover))
            self.image_list.Add(image.Rescale(50, 50, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap())

            self.UpdateUI(file[1], f"{result['track']['title']} - {result['track']['subtitle']}", self.image_list.GetImageCount() - 1)

    def OnSave(self, event):
        # check if files have been processed (metadata added)
        for file in self.files:
            if len(file) < 3:
                return

        # load in mutagen
        for file in self.files:
            try:
                audio = EasyID3(file[0])
            except:
                audio = mutagen.File(file[0], easy=True)
                audio.add_tags()

            print(file[2]['track'])

            audio['title'] = file[2]['track']['title']
            audio['artist'] = file[2]['track']['subtitle']
            audio['album'] = file[2]['track']['sections'][0]['metadata'][0]['text']
            audio['date'] = file[2]['track']['sections'][0]['metadata'][2]['text']
            audio['genre'] = file[2]['track']['genres']['primary']

            audio.save()

            # save cover
            audio = ID3(file[0])
            audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=file[3])
            audio.save()




    def UpdateUI(self, index, result, cover):
        self.list_ctrl.SetItem(index, 0, result)
        self.list_ctrl.SetItemImage(index, cover)


    def Show(self):
        self.frame.Show()

if __name__ == '__main__':
    app = wx.App()
    FindSong(None).Show()
    app.MainLoop()