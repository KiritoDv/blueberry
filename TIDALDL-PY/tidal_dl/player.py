#!/usr/bin/env python

#-*- coding: utf-8 -*-
from aigpy.progressHelper import ProgressTool
from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio
from threading import Thread

class Song(Thread):     

    def __init__(self, f, *args, **kwargs):
        self.vol_modifier = 30
        self.seg = AudioSegment.from_file(f) - self.vol_modifier
        self.callback = lambda x: x
        self.__is_paused = True
        self.p = PyAudio()
        Thread.__init__(self, *args, **kwargs)
        self.start()

    def pause(self):
        self.__is_paused = True

    def play(self):
        self.__is_paused = False

    def __get_stream(self):
        return self.p.open(format=self.p.get_format_from_width(self.seg.sample_width),
                           channels=self.seg.channels,
                           rate=self.seg.frame_rate,
                           output=True)

    def run(self):
        stream = self.__get_stream()
        chunk_count = 0
        self.chunks = make_chunks(self.seg, 100)        
        
        while chunk_count < len(self.chunks):
            if not self.__is_paused:
                data = (self.chunks[chunk_count])._data
                chunk_count += 1
                self.callback(chunk_count)
            else:
                free = stream.get_write_available()
                data = chr(0)*free
            stream.write(data)

        stream.stop_stream()
        self.p.terminate()