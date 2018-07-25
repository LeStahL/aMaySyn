import kivy
kivy.require('1.10.0') # replace with your current kivy version !
from kivy.app import App
from kivy.graphics import Color

import random

class Pattern():
    
    def __init__(self, name = 'NJU', length = 1):
        self.name = name
        self.notes = []
        self.length = length if length > 0 else 1 # after adding, jump to "len field" in order to change it if required TODO
        self.current_note = 0
        self.color = Color(random.uniform(.05,.95), 1, .8, mode = 'hsv').rgb

    # helpers...
    def getNote(self, offset=0):      return self.notes[ (self.current_note + offset) % len(self.notes)] if self.notes else None
    #def getFirstNote(self): return self.notes[0]  if len(self.notes) > 0 else None
    #def getLastNote(self):  return self.notes[-1] if len(self.notes) > 0 else None
        
    def addNote(self, noteon, notelen, notepitch, notevel=100):
        self.notes.append(Note(noteon, notelen, notepitch, notevel)) #actually, don't append, but insert at the right position TODO --> check ordering, noteons should be ordered (POLYPHONY THIS TIME!)

    def switchNote(self, inc):
        if self.notes:
            self.current_note = (self.current_note + inc) % len(self.notes)
        
    def shiftNote(self, inc):
        if self.notes:
            self.getNote().notepitch = max(0, min(88, self.getNote().notepitch + inc)) # TODO find out whether 88 is way too high..

    def shiftAllNotes(self, inc):
        for n in self.notes:
            n.notepitch = max(0, min(88, n.notepitch + inc))

    def stretchNote(self, inc):
        # here I had lots of possibilities .. is inc > or < 0? but these where on the monophonic synth. Let's rethink polyphonic!
        if self.notes:
            if inc < 0:
                if self.getNote().notelen <= 1/16:
                    self.getNote().notelen = 1/32
                elif self.getNote().notelen <= -inc:
                    self.getNote().notelen /= 2
                else:
                    self.getNote().notelen -= -inc
            else:
                if self.getNote().notelen <= inc:
                    self.getNote().notelen *= 2
                else:
                    self.getNote().notelen = max(0, min(self.length - self.getNote().noteon, self.getNote().notelen + inc)) # TODO find out whether 88 is way too high..
            
            self.getNote().noteoff = self.getNote().noteon + self.getNote().notelen
    
    def moveNote(self, inc):
        # same as with stretch: rethink for special Käses?
        if self.notes and inc != 0:
            if abs(self.getNote().notelen) < abs(inc): inc = abs(inc)/inc * self.getNote().notelen

            self.getNote().noteon = max(0, min(self.length - self.getNote().notelen, self.getNote().noteon + inc)) # TODO find out whether 88 is way too high..
            self.getNote().noteoff = self.getNote().noteon + self.getNote().notelen
    
    # HEUTE NOCH: diese beiden funktionen und die load/save funktionen (export to code dann morgen aufm stammtisch schreiben!)

    ### DEBUG ###
    def printNoteList(self):
        for n in self.notes:
            print(n.noteon, n.noteoff, n.notelen, n.notepitch, n.notevel)


class Note():

    def __init__(self, noteon=0, notelen=1, notepitch=24, notevel=100): # set notelen to last default TODO
        self.noteon = noteon
        self.noteoff = noteon + notelen
        self.notelen = notelen
        self.notepitch = int(notepitch)
        self.notevel = notevel
        # some safety checks TODO

