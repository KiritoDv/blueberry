#!/usr/bin/env python

#-*- coding: utf-8 -*-
import strawberry

class Strawberry():     

    def __init__(self, f, *args, **kwargs):
        self.volume = 0        
        self.file = f        
        self.playcb = lambda x: x
        self.stopcb = lambda x: x
    
    def load(self):
        strawberry.load_player(path=self.file)

    def play(self):
        strawberry.set_play_status(True);

    def pause(self):
        strawberry.set_play_status(False);

    def is_paused(self):
        return not strawberry.paused()

    def stop(self):
        strawberry.close_player()

    def get_volume(self):
        return self.volume

    def set_volume(self, vol):
        self.volume = vol
        strawberry.set_volume(vol);

    def set_vol(self, vol):
        self.volume = vol

    def canFinish(self):
        return not strawberry.running();

    def getMaxFrames(self):
        return strawberry.get_max_frames()

    def start(self):
        
        strawberry.init_player()
        self.set_volume(self.volume)

        self.volume = strawberry.get_volume()

        while strawberry.running():
            self.playcb(strawberry.get_current_frames())
        
        self.stop()
        self.stopcb(0)

