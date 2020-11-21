#!/usr/bin/env python

#-*- coding: utf-8 -*-
from aigpy.progressHelper import ProgressTool
from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio
from threading import Thread


class Song(Thread):     

    def __init__(self, f, *args, **kwargs):
        self.volModifier = 0
        self.chunk_count = 0
        self.stream = None
        self.seg = AudioSegment.from_file(f)
        self.playcb = lambda x: x
        self.stopcb = lambda x: x
        self.is_paused = True
        self.p = PyAudio()
        Thread.__init__(self, *args, **kwargs)        
        self.start()
    
    def pause(self):
        self.is_paused = True

    def play(self):
        self.is_paused = False

    def __get_stream(self):
        return self.p.open(format=self.p.get_format_from_width(self.seg.sample_width),
                           channels=self.seg.channels,
                           rate=self.seg.frame_rate,
                           output=True)

    def stop(self):
        if(self.stream == None):
            return
        self.chunk_count = len(self.chunks)        

    def canFinish(self):
        return self.is_paused and self.chunk_count >= len(self.chunks)

    def run(self):
        self.stream = self.__get_stream()
        
        self.chunks = make_chunks(self.seg, 100)       
        
        while self.chunk_count < len(self.chunks):
            if not self.is_paused:
                chunk_data = (self.chunks[self.chunk_count]).apply_gain(-self.volModifier)
                data = chunk_data._data
                self.chunk_count += 1
                self.playcb(self.chunk_count)
            else:
                free = self.stream.get_write_available()
                data = chr(0)*free
            self.stream.write(data)
        

        self.stream.stop_stream()
        self.p.terminate()
        self.stopcb(0)
        self.is_paused = True    