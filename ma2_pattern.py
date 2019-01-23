import kivy
kivy.require('1.10.0') # replace with your current kivy version !
from kivy.app import App
from kivy.graphics import Color

import random

class Pattern():
    
    def __init__(self, name = 'NJU', length = 1, synth_type = '_', max_note = 0):
        self.name = name
        self.notes = []
        self.length = length if length and length > 0 else 1 # after adding, jump to "len field" in order to change it if required TODO
        self.current_note = 0
        self.current_gap = 0
        self.randomizeColor()
        self.setTypeParam(synth_type = synth_type, max_note = max_note if max_note > 0 else 88)

    def setTypeParam(self, synth_type = None, max_note = None):
        if synth_type:
            self.synth_type = synth_type
        if max_note:
            self.max_note = max_note
            for n in self.notes:
                n.note_pitch = n.note_pitch % max_note

    # helpers...
    def getNote(self, offset=0):    return self.notes[(self.current_note + offset) % len(self.notes)] if self.notes else None
    def getNoteOn(self, offset=0):  return self.getNote(offset).note_on if self.getNote(offset) else None
    def getNoteOff(self, offset=0): return self.getNote(offset).note_off if self.getNote(offset) else None
    def getFirstNote(self):         return self.notes[0]  if self.notes else None
    def getLastNote(self):          return self.notes[-1] if self.notes else None
    def getFirstTaggedNote(self):   return next(i for i in range(len(self.notes)) if self.notes[i].tagged)

    # THE MOST IMPORTANT FUNCTION!
    def randomizeColor(self):
        self.color = Color(random.uniform(.05,.95), .8, .88, mode = 'hsv').rgb
        
    def addNote(self, note = None, select = True, append = False, clone = False):
        if note is None:
            note = Note()
            append = False
        if clone: select = False
        
        note = Note(note.note_on + append * note.note_len + self.current_gap, note.note_len, note.note_pitch % self.max_note, note.note_vel)
        note.tag()
        
        if note.note_off > self.length: return
        
        self.notes.append(note)
        self.notes.sort(key = lambda n: (n.note_on, n.note_pitch))
        self.current_note = self.getFirstTaggedNote()
        self.untagAllNotes()
        # cloning: since we have polyphonic mode now, we can not just assign the right gap - have to do it via space/backspace - will be changed to polyphonic cloning
        if not clone: self.setGap(to = 0)

    def fillNote(self, note = None): #this is for instant pattern creation... copy the content during the current note (plus gap) and repeat it as long as the pattern allows to
        if note is None: return

        copy_span = note.note_len + self.current_gap
        copy_pos = note.note_off + self.current_gap
        note.tag()
    
        notes_to_copy = [n for n in self.notes if n.note_on <= copy_pos and n.note_off > note.note_on]
        print("yanked some notes, ", len(notes_to_copy), notes_to_copy)

        while copy_pos + copy_span <= self.length:
            for n in notes_to_copy:
                copy_on = copy_pos + n.note_on - note.note_on
                copy_len = n.note_len
                
                if n.note_on < note.note_on:
                    copy_on = copy_pos
                    copy_len = n.note_len - (note.note_on - n.note_on)
                if n.note_off > note.note_off:
                    copy_len = note.note_off - n.note_on
                    
                self.notes.append(Note(copy_on, copy_len, n.note_pitch, n.note_vel))
                
            copy_pos += copy_span 
            
        self.notes.sort(key = lambda n: (n.note_on, n.note_pitch))
        self.current_note = self.getFirstTaggedNote()
        self.untagAllNotes()

    def delNote(self):
        if self.notes:
            old_note = self.current_note
            old_pitch = self.notes[old_note].note_pitch
            
            del self.notes[self.current_note if self.current_note is not None else -1]

            if self.current_note > 0:
                self.current_note = min(self.current_note-1, len(self.notes)-1)

            if self.synth_type == 'D':
                for n in self.notes[old_note:] + self.notes[0:old_note-1]:
                    if n.note_pitch == old_pitch:
                        n.tag()
                        self.notes.sort(key = lambda n: (n.note_on, n.note_pitch))
                        self.current_note = self.getFirstTaggedNote()
                        self.untagAllNotes()
                        break

    def setGap(self, to = 0, inc = False, dec = False):
        if self.notes:
            if inc:
                self.current_gap += self.getNote().note_len
            elif dec:
                self.current_gap = max(self.current_gap - self.getNote().note_len, 0)
            elif to is not None:
                self.current_gap = to
            else:
                pass

    def untagAllNotes(self):
        for n in self.notes:
            n.tagged = False

    def switchNote(self, inc, to = -1):
        if self.notes:
            if inc != 0:
                self.current_note = (self.current_note + inc) % len(self.notes)
            else:
                self.current_note = (len(self.notes) + to) % len(self.notes)
        
    def shiftNote(self, inc):
        if self.notes:
            self.getNote().note_pitch = (self.getNote().note_pitch + inc) % self.max_note

    def shiftAllNotes(self, inc):
        notes = self.notes if not self.synth_type == 'D' else [n for n in self.notes if n.note_pitch == self.getNote().note_pitch]
        if notes:
            for n in notes:
                n.note_pitch = (n.note_pitch + inc) % self.max_note

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
                    self.getNote().note_len = max(0, min(self.length - self.getNote().note_on, self.getNote().note_len + inc))
            
            self.getNote().note_off = self.getNote().note_on + self.getNote().note_len
    
    def moveNote(self, inc):
        # same as with stretch: rethink for special Käses?
        if self.notes:
                if abs(self.getNote().note_len) < abs(inc): inc = abs(inc)/inc * self.getNote().note_len

        self.getNote().tag()

        if self.getNoteOff() == self.length and inc > 0:
            self.getNote().moveNoteOn(0)
            
        elif self.getNoteOn() == 0 and inc < 0:
            self.getNote().moveNoteOff(self.length)
            
        else:
            self.getNote().note_on = max(0, min(self.length - self.getNote().note_len, self.getNote().note_on + inc))
            self.getNote().note_off = self.getNote().note_on + self.getNote().note_len

        self.notes.sort(key = lambda n: (n.note_on, n.note_pitch))
        self.current_note = self.getFirstTaggedNote()
        self.untagAllNotes()

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
        self.tagged = False
        # some safety checks TODO

    def moveNoteOn(self, to):
        self.note_on = to
        self.note_off = to + self.note_len
        
    def moveNoteOff(self, to):
        self.note_off = to
        self.note_on = to - self.note_len

    def tag(self):
        self.tagged = True
