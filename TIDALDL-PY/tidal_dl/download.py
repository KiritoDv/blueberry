#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   download.py
@Time    :   2020/11/08
@Author  :   Yaronzz
@Version :   1.0
@Contact :   yaronhuang@foxmail.com
@Desc    :   
'''
from itertools import count
from math import floor
import os
from aigpy.cmdHelper import green, red, yellow

import aigpy.m3u8Helper as m3u8Helper
from aigpy.tagHelper import TagTool
from aigpy.netHelper import downloadFile, downloadFileMultiThread
from aigpy.stringHelper import isNull, getSubOnlyEnd
from aigpy.pathHelper import replaceLimitChar, getFileName, remove
from aigpy.fileHelper import getFileContent, getFileSize
import aigpy.netHelper as netHelper

from tidal_dl.player import Strawberry

from tidal_dl.settings import Settings
from tidal_dl.tidal import TidalAPI
from tidal_dl.enum import Type, AudioQuality
from tidal_dl.printf import Printf
from tidal_dl.blueberry import Blueberry
from tidal_dl.decryption import decrypt_security_token
from tidal_dl.decryption import decrypt_file
import sys
from datetime import datetime
from pynput import keyboard

API = TidalAPI()

def __loadAPI__(user):
    API.key.accessToken = user.accessToken
    API.key.userId = user.userid
    API.key.countryCode = user.countryCode
    #API.key.sessionId = user.sessionid1


def __loadVideoAPI__(user):
    API.key.accessToken = user.accessToken
    API.key.userId = user.userid
    API.key.countryCode = user.countryCode
    #API.key.sessionId = user.sessionid2 if not isNull(user.sessionid2) else user.sessionid1



def __getIndexStr__(index):
    pre = "0"
    if index < 10:
        return pre+str(index)
    if index < 99:
        return str(index)
    return str(index)

def __getExtension__(url):
    if '.flac' in url:
        return '.flac'
    if '.mp4' in url:
        return '.mp4'
    return '.m4a'

def __getArtists__(array):
    ret = []
    for item in array:
        ret.append(item.name)
    return ret

def __parseContributors__(roleType, Contributors):
    if Contributors is None:
        return None
    try:
        ret = []
        for item in Contributors['items']:
            if item['role'] == roleType:
                ret.append(item['name'])
        return ret
    except:
        return None


def __setMetaData__(track, album, filepath, contributors):
    obj = TagTool(filepath)
    obj.album = track.album.title
    obj.title = track.title
    obj.artist = __getArtists__(track.artists)
    obj.copyright = track.copyRight
    obj.tracknumber = track.trackNumber
    obj.discnumber = track.volumeNumber
    obj.composer = __parseContributors__('Composer', contributors)
    obj.isrc = track.isrc
    obj.albumartist = __getArtists__(album.artists)
    obj.date = album.releaseDate
    obj.totaldisc = album.numberOfVolumes
    if obj.totaldisc <= 1:
        obj.totaltrack = album.numberOfTracks
    coverpath = API.getCoverUrl(album.cover, "1280", "1280")
    obj.save(coverpath)
    return

def __convertToM4a__(filepath, codec):
    if 'ac4' in codec or 'mha1' in codec:
        return filepath
    if '.mp4' not in filepath:
        return filepath
    newpath = filepath.replace('.mp4', '.m4a')
    remove(newpath)
    os.rename(filepath, newpath)
    return newpath


# "{ArtistName}/{Flag} [{AlbumID}] [{AlbumYear}] {AlbumTitle}"
def __getAlbumPath__(conf: Settings, album):
    base = conf.downloadPath + '/Album/'
    artist = replaceLimitChar(album.artists[0].name, '-')
    # album folder pre: [ME][ID]
    flag = API.getFlag(album, Type.Album, True, "")
    if conf.audioQuality != AudioQuality.Master:
        flag = flag.replace("M", "")
    if not conf.addExplicitTag:
        flag = flag.replace("E", "")
    if not isNull(flag):
        flag = "[" + flag + "] "
        
    sid = str(album.id)
    #album and addyear
    albumname = replaceLimitChar(album.title, '-')
    year = ""
    if album.releaseDate is not None:
        year = getSubOnlyEnd(album.releaseDate, '-')
    # retpath
    retpath = conf.albumFolderFormat
    if retpath is None or len(retpath) <= 0:
        retpath = Settings.getDefaultAlbumFolderFormat()
    retpath = retpath.replace(R"{ArtistName}", artist.strip())
    retpath = retpath.replace(R"{Flag}", flag)
    retpath = retpath.replace(R"{AlbumID}", sid)
    retpath = retpath.replace(R"{AlbumYear}", year)
    retpath = retpath.replace(R"{AlbumTitle}", albumname.strip())
    retpath = retpath.strip()
    return base + retpath


def __getAlbumPath2__(conf, album):
    # outputdir/Album/artist/
    artist = replaceLimitChar(album.artists[0].name, '-').strip()
    base = conf.downloadPath + '/Album/' + artist + '/'

    # album folder pre: [ME][ID]
    flag = API.getFlag(album, Type.Album, True, "")
    if conf.audioQuality != AudioQuality.Master:
        flag = flag.replace("M", "")
    if not conf.addExplicitTag:
        flag = flag.replace("E", "")
    if not isNull(flag):
        flag = "[" + flag + "] "

    sid = "[" + str(album.id) + "] " if conf.addAlbumIDBeforeFolder else ""

    #album and addyear
    albumname = replaceLimitChar(album.title, '-').strip()
    year = ""
    if conf.addYear and album.releaseDate is not None:
        year = "[" + getSubOnlyEnd(album.releaseDate, '-') + "] "
    return base + flag + sid + year + albumname + '/'


def __getPlaylistPath__(conf, playlist):
    # outputdir/Playlist/
    base = conf.downloadPath + '/Playlist/'
    # name
    name = replaceLimitChar(playlist.title, '-')
    return base + name + '/'

# "{TrackNumber} - {ArtistName} - {TrackTitle}{ExplicitFlag}"


def __getTrackPath__(conf: Settings, track, stream, album=None, playlist=None):
    if album is not None:
        base = __getAlbumPath__(conf, album) + '/'
        if album.numberOfVolumes > 1:
            base += 'CD' + str(track.volumeNumber) + '/'
    if playlist is not None:
        base = __getPlaylistPath__(conf, playlist)
    # number
    number = __getIndexStr__(track.trackNumber)
    if playlist is not None:
        number = __getIndexStr__(track.trackNumberOnPlaylist)
    # artist
    artist = replaceLimitChar(track.artists[0].name, '-')
    # title
    title = track.title
    if not isNull(track.version):
        title += ' (' + track.version + ')'
    title = replaceLimitChar(title, '-')
    # get explicit
    explicit = "(Explicit)" if conf.addExplicitTag and track.explicit else ''
    #album and addyear
    albumname = replaceLimitChar(album.title, '-')
    year = ""
    if album.releaseDate is not None:
        year = getSubOnlyEnd(album.releaseDate, '-')
    # extension
    extension = __getExtension__(stream.url)
    retpath = conf.trackFileFormat
    if retpath is None or len(retpath) <= 0:
        retpath = Settings.getDefaultTrackFileFormat()
    retpath = retpath.replace(R"{TrackNumber}", number)
    retpath = retpath.replace(R"{ArtistName}", artist.strip())
    retpath = retpath.replace(R"{TrackTitle}", title)
    retpath = retpath.replace(R"{ExplicitFlag}", explicit)
    retpath = retpath.replace(R"{AlbumYear}", year)
    retpath = retpath.replace(R"{AlbumTitle}", albumname.strip())
    retpath = retpath.strip()
    return base + retpath + extension


def __getTrackPath2__(conf, track, stream, album=None, playlist=None):
    if album is not None:
        base = __getAlbumPath__(conf, album)
        if album.numberOfVolumes > 1:
            base += 'CD' + str(track.volumeNumber) + '/'
    if playlist is not None:
        base = __getPlaylistPath__(conf, playlist)

    # hyphen
    hyphen = ' - ' if conf.addHyphen else ' '
    # get number
    number = ''
    if conf.useTrackNumber:
        number = __getIndexStr__(track.trackNumber) + hyphen
        if playlist is not None:
            number = __getIndexStr__(track.trackNumberOnPlaylist) + hyphen
    # get artist
    artist = ''
    if conf.artistBeforeTitle:
        artist = replaceLimitChar(track.artists[0].name, '-') + hyphen
    # get explicit
    explicit = "(Explicit)" if conf.addExplicitTag and track.explicit else ''
    # title
    title = track.title
    if not isNull(track.version):
        title += ' - ' + track.version
    title = replaceLimitChar(title, '-')
    # extension
    extension = __getExtension__(stream.url)
    return base + number + artist.strip() + title + explicit + extension


def __getVideoPath__(conf, video, album=None, playlist=None):
    if album is not None and album.title is not None:
        base = __getAlbumPath__(conf, album)
    elif playlist is not None:
        base = __getPlaylistPath__(conf, playlist)
    else:
        base = conf.downloadPath + '/Video/'

    # hyphen
    hyphen = ' - ' if conf.addHyphen else ' '
    # get number
    number = ''
    if conf.useTrackNumber:
        number = __getIndexStr__(video.trackNumber) + hyphen
    # get artist
    artist = ''
    if conf.artistBeforeTitle:
        artist = replaceLimitChar(video.artists[0].name, '-') + hyphen
    # get explicit
    explicit = "(Explicit)" if conf.addExplicitTag and video.explicit else ''
    # title
    title = replaceLimitChar(video.title, '-')
    # extension
    extension = ".mp4"
    return base + number + artist.strip() + title + explicit + extension


def __isNeedDownload__(path, url):
    curSize = getFileSize(path)
    if curSize <= 0:
        return True
    netSize = netHelper.getFileSize(url)
    if curSize >= netSize:
        return False
    return True


def __downloadVideo__(conf, video, album=None, playlist=None):
    msg, stream = API.getVideoStreamUrl(video.id, conf.videoQuality)
    if not isNull(msg):
        Printf.err(video.title + "." + msg)
        return
    path = __getVideoPath__(conf, video, album, playlist)
    if m3u8Helper.download(stream.m3u8Url, path):
        Printf.success(getFileName(path))
    else:
        Printf.err("\nDownload failed!" + getFileName(path))


def __downloadTrack__(conf: Settings, track, album=None, playlist=None):
    try:
        msg, stream = API.getStreamUrl(track.id, conf.audioQuality)
        if not isNull(msg) or stream is None:
            Printf.err(track.title + "." + msg)
            return
        path = __getTrackPath__(conf, track, stream, album, playlist)

        # check exist
        if conf.checkExist and __isNeedDownload__(path, stream.url) == False:
            playSong(track, path);
            Printf.success(getFileName(path) + " (skip:already exists!)")
            return

        # Printf.info("Download \"" + track.title + "\" Codec: " + stream.codec)
        if conf.multiThreadDownload:
            check, err = downloadFileMultiThread(stream.url, path + '.part',
                                                 stimeout=20, showprogress=conf.showProgress)
        else:
            check, err = downloadFile(stream.url, path + '.part', stimeout=20, showprogress=conf.showProgress)
        if not check:
            Printf.err("Download failed! " + getFileName(path) + ' (' + str(err) + ')')
            return
        # encrypted -> decrypt and remove encrypted file
        if isNull(stream.encryptionKey):
            os.replace(path + '.part', path)
        else:
            key, nonce = decrypt_security_token(stream.encryptionKey)
            decrypt_file(path + '.part', path, key, nonce)
            os.remove(path + '.part')

        path = __convertToM4a__(path, stream.codec)

        # contributors
        contributors = API.getTrackContributors(track.id)
        __setMetaData__(track, album, path, contributors)
        # Printf.success(getFileName())
        playSong(track, path);
    except Exception as e:
        Printf.err("Download failed! " + track.title + ' (' + str(e) + ')')

def genVolume(vol, length):
    tmp = ""
    for i in range(0, length):        
        tmp += ("■" if(i < round(vol * length, 2)) else "□")
    return tmp

def genProgressBar(current, max, length):
    tmp = ""
    for i in range(0, length):
        tmp += ("■" if(i < length - ((current / max) * length)) else "□")
    return tmp


def playCallback(song, count, length, progress, info):
    progress = genProgressBar(count, length, 30);
    vol = round(song.get_volume(), 2)    
    start = datetime.fromtimestamp(round((length - count) / 44)).strftime("%M:%S")
    finish = datetime.fromtimestamp(round((length) / 44)).strftime("%M:%S")
    desc = f"{start} [{progress}] {finish} Vol: [{genVolume(vol, 10)}] {round(100 * vol)}%";

    sys.stdout.write("\r" + desc)
    sys.stdout.flush()    

def stopCallback(keyl, path):
    # os.remove(path)
    keyl.stop()
    os.system('clear')

def on_key(song, key):
    if(key == 'dvol'):
        vol = round(song.get_volume(), 2)
        if(vol > 0):            
            song.set_volume(vol - 0.1)            
            Blueberry.sel_local_vol(vol)
    if(key == 'uvol'):
        vol = round(song.get_volume(), 2)
        if(vol <= 0.9):
            song.set_volume(vol + 0.1)
            Blueberry.sel_local_vol(vol)
    if(key == 'play'):
        if song.is_paused(): song.play()
        else: song.pause()
    if(key == 'stop'):
        song.stop()
    if(key == 'kill'):
        Blueberry.set_break_status(True)
        song.stop()

def playSong(track, path):
        
    song = Strawberry(path)
    song.load()    

    desc = f"({track.title} - {track.album.title})"
    
    keyl = keyboard.GlobalHotKeys({
        "<cmd_l>+<alt>+o": lambda: on_key(song, 'play'),
        '<cmd_l>+<alt>+p': lambda: on_key(song, 'stop'), 
        '<cmd_l>+<alt>+[': lambda: on_key(song, 'dvol'),
        '<cmd_l>+<alt>+]': lambda: on_key(song, 'uvol'),
        '<cmd_l>+<alt>+i': lambda: on_key(song, 'kill'),
    })

    keyl.start()
    
    max_frames = round(song.getMaxFrames() / 1000)

    song.playcb = lambda count: playCallback(song, round(abs((count + 1) / 1000)), max_frames, None, desc)
    song.stopcb = lambda x: stopCallback(keyl, path)

    os.system('clear')
    song.set_vol(Blueberry.gel_local_vol())

    ml = 65;
    print('')
    for cw in range(0, round(ml / 2 - len(desc) / 2)):
        print(" ", end='')

    print(f"{desc}\n")

    song.start()    


def __downloadCover__(conf, album):
    if album == None:
        return
    path = __getAlbumPath__(conf, album) + '/cover.jpg'
    url = API.getCoverUrl(album.cover, "1280", "1280")
    if url is not None:
        downloadFile(url, path)


def __album__(conf, obj):
    Printf.album(obj)
    msg, tracks, videos = API.getItems(obj.id, Type.Album)
    if not isNull(msg):
        Printf.err(msg)
        return
    # if conf.saveCovers:
    #    __downloadCover__(conf, obj)
    for item in tracks:
        if(Blueberry.should_break()):
            Blueberry.set_break_status(False)
            break
        __downloadTrack__(conf, item, obj)
    # for item in videos:
    #    __downloadVideo__(conf, item, obj)


def __track__(conf, obj):
    Printf.track(obj)
    msg, album = API.getAlbum(obj.album.id)
    # if conf.saveCovers:
    #     __downloadCover__(conf, album)
    __downloadTrack__(conf, obj, album)


def __video__(conf, obj):
    Printf.video(obj)
    __downloadVideo__(conf, obj, obj.album)


def __artist__(conf, obj):
    msg, albums = API.getArtistAlbums(obj.id, conf.includeEP)
    Printf.artist(obj, len(albums))
    if not isNull(msg):
        Printf.err(msg)
        return
    for item in albums:
        __album__(conf, item)


def __playlist__(conf, obj):
    Printf.playlist(obj)
    msg, tracks, videos = API.getItems(obj.uuid, Type.Playlist)
    if not isNull(msg):
        Printf.err(msg)
        return

    for index, item in enumerate(tracks):
        if(Blueberry.should_break()):
            Blueberry.set_break_status(False)
            break
        mag, album = API.getAlbum(item.album.id)
        item.trackNumberOnPlaylist = index + 1
        __downloadTrack__(conf, item, album, obj)
    # for item in videos:
    #    __downloadVideo__(conf, item, None)


def __file__(user, conf, string):
    txt = getFileContent(string)
    if isNull(txt):
        Printf.err("Nothing can read!")
        return
    array = txt.split('\n')
    for item in array:
        if isNull(item):
            continue
        if item[0] == '#':
            continue
        if item[0] == '[':
            continue
        start(user, conf, item)

def searchTrack(user, lang, field, song, conf):
    __loadAPI__(user)

    msg, obj = API.searchSong(field, song, limit=10)

    for item in obj:
        if field == 'track':
            print(green(f"Enter [{obj.index(item)}]: ") + f"{item.title} - {item.artist.name} - {item.album.title}")
        elif field == 'album':
            print(green(f"Enter [{obj.index(item)}]: ") + f"{item.title} - {item.artist.name}")
        else:
            print(green(f"Enter [{obj.index(item)}]: ") + f"{item.title} - {item.numberOfTracks} Songs")        

    try:
        choice = int(Printf.enter(lang))
        if(choice >= 0 and choice < len(obj)):
            if field == 'track':
                __track__(conf, obj[choice])
            elif field == 'album':
                __album__(conf, obj[choice])
            else:
                __playlist__(conf, obj[choice])
        else:
            os.system('clear')
            Printf.err("Invalid option!")
    except ValueError:
        os.system('clear')
        Printf.err("Invalid option!")


def start(user, conf, string):
    __loadAPI__(user)

    if os.path.exists(string):
        __file__(user, conf, string)
        return

    msg, etype, obj = API.getByString(string)
    if etype == Type.Null or not isNull(msg):
        Printf.err(msg)
        return

    if etype == Type.Album:
        __album__(conf, obj)
    if etype == Type.Track:
        __track__(conf, obj)
    if etype == Type.Video:
        __loadVideoAPI__(user)
        __video__(conf, obj)
    if etype == Type.Artist:
        __artist__(conf, obj)
    if etype == Type.Playlist:
        __playlist__(conf, obj)
