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
        self.randomizeColor()

    # helpers...
    def getNote(self, offset=0):    return self.notes[(self.current_note + offset) % len(self.notes)] if self.notes else None
    def getNoteOn(self, offset=0):  return self.getNote(offset).note_on if self.getNote(offset) else None
    def getNoteOff(self, offset=0): return self.getNote(offset).note_off if self.getNote(offset) else None
    def getFirstNote(self):         return self.notes[0]  if self.notes else None
    def getLastNote(self):          return self.notes[-1] if self.notes else None

    # THE MOST IMPORTANT FUNCTION!
    def randomizeColor(self):
        self.color = Color(random.uniform(.05,.95), .8, .88, mode = 'hsv').rgb
        
    def addNote(self, note = None, select = True, append = False):
        if note is None: note = Note()
        
        note_info = (note.note_on + append * note.note_len, note.note_len, note.note_pitch, note.note_vel)
        
        self.notes.append(Note(*note_info))
        self.notes.sort(key = lambda n: n.note_on)

        if select:
            if append:
                self.current_note += 1
            else:
                self.current_note = len(self.notes) - 1

    def delNote(self):
        if self.notes:
            del self.notes[self.current_note if self.current_note is not None else -1]
            self.current_note = min(self.current_note, len(self.notes)-1)

    def switchNote(self, inc):
        if self.notes:
            self.current_note = (self.current_note + inc) % len(self.notes)
        
    def shiftNote(self, inc):
        if self.notes:
            self.getNote().note_pitch = max(0, min(88, self.getNote().note_pitch + inc)) # TODO find out whether 88 is way too high..

    def shiftAllNotes(self, inc):
        for n in self.notes:
            n.note_pitch = max(0, min(88, n.note_pitch + inc))

    def stretchNote(self, inc):
        # here I had lots of possibilities .. is inc > or < 0? but these where on the monophonic synth. Let's rethink polyphonic!
        if self.notes:
            if inc < 0:
                if self.getNote().note_len <= 1/16:
                    self.getNote().note_len = 1/32
                elif self.getNote().note_len <= -inc:
                    self.getNote().note_len /= 2
                else:
                    self.getNote().note_len -= -inc
            else:
                if self.getNote().note_len <= inc:
                    self.getNote().note_len *= 2
                else:
                    self.getNote().note_len = max(0, min(self.length - self.getNote().note_on, self.getNote().note_len + inc)) # TODO find out whether 88 is way too high..
            
            self.getNote().note_off = self.getNote().note_on + self.getNote().note_len
    
    def moveNote(self, inc):
        # same as with stretch: rethink for special Käses?
        if self.notes and inc > 0:
                if abs(self.getNote().note_len) < abs(inc): inc = abs(inc)/inc * self.getNote().note_len

        # first check wraparound TODO: something doesn't work if you wrap around and then match a note of same note_on and note_len ... anyway. don't care now.
        if self.getNoteOff() == self.length and self.getNote() == self.getLastNote() and inc > 0:
            self.getNote().moveNoteOn(0)
            self.current_note = 0
            
        elif self.getNoteOn() == 0 and self.getNote() == self.getFirstNote() and inc < 0:
            self.getNote().moveNoteOff(self.length)
            self.current_note = len(self.notes) - 1
            
        else:

            self.getNote().note_on = max(0, min(self.length - self.getNote().note_len, self.getNote().note_on + inc)) # TODO find out whether 88 is way too high..
            self.getNote().note_off = self.getNote().note_on + self.getNote().note_len

            if inc > 0 and self.getNoteOn(+1) < self.getNoteOn() and self.current_note < len(self.notes)-1:
                self.current_note += 1

            if inc < 0 and self.getNoteOn(-1) > self.getNoteOn() and self.current_note > 0:
                self.current_note -= 1

        self.notes.sort(key = lambda n: n.note_on)
        #print(*(n.note_on for n in self.notes))


    def stretchPattern(self, inc, scale = False):
        if self.length + inc <= 0: return
    
        old_length = self.length
        self.length = self.length + inc
              
        # fun gimmick: option to really stretch (scale all notes) the pattern ;)
        if scale:
            factor = self.length/old_length
            for n in self.notes:
                n.note_on *= factor
                n.note_off *= factor
                n.note_len *= factor

        # remove notes beyond pattern (TODO after release of shift / after timer?)
        for n in reversed(self.notes):
            if n.note_on > self.length:
                self.notes = self.notes[:-1]
            elif n.note_off > self.length:
                n.note_off = self.length
                n.note_len = n.note_off - n.note_on
            else:
                break

    ### DEBUG ###
    def printNoteList(self):
        for n in self.notes:
            print(n.note_on, n.note_off, n.note_len, n.note_pitch, n.note_vel)

class Note():

    def __init__(self, note_on=0, note_len=1, note_pitch=24, note_vel=100): # set note_len to last default TODO
        self.note_on = note_on
        self.note_off = note_on + note_len
        self.note_len = note_len
        self.note_pitch = int(note_pitch)
        self.note_vel = note_vel
        # some safety checks TODO

    def moveNoteOn(self, to):
        self.note_on = to
        self.note_off = to + self.note_len
        
    def moveNoteOff(self, to):
        self.note_off = to
        self.note_on = to - self.note_len
