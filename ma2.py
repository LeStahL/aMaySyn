import kivy
kivy.require('1.10.0') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.core.text import Label as CoreLabel

from itertools import accumulate
import csv
import operator
import os

from ma2_track import *
from ma2_pattern import *
from ma2_widgets import *

Config.set('graphics', 'width', '1600')
Config.set('graphics', 'height', '1000')
#Config.set('graphics', 'fullscreen', 'auto')

debug = True


class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)

    current_track = None
    current_module = None
    current_pattern = None
    current_note = None
    tracks = []
    patterns = []

    synths = ['I_Bass', 'D_Kick', '__GFX', '__None']
    
    title = "is it π/2 yet?"
    
    btnTitle = ObjectProperty()
    
    #updateAll = True # ah, fuck it. always update everythig. TODO improve performance... somehow.
    
    #helpers...
    def getTrack(self):                 return self.tracks[self.current_track] if self.current_track is not None else None
    def getLastTrack(self):             return self.tracks[-1] if self.tracks else None
    def getModule(self, offset=0):      return self.getTrack().getModule(offset) if self.getTrack() else None
    def getModuleTranspose(self):       return self.getModule().transpose if self.getModule() else 0
    def getModulePattern(self):         return self.getModule().pattern if self.getModule() else None
    def getPattern(self, offset=0):     return self.patterns[(self.patterns.index(self.getModulePattern()) + offset) % len(self.patterns)] if self.getModulePattern() in self.patterns else self.patterns[0] if self.patterns else None
    def getPatternLen(self, offset=0):  return self.getPattern(offset).length if self.getPattern(offset) else None
    def getPatternName(self):           return self.getPattern().name if self.getPattern() else 'None'
    def getNote(self):                  return self.getPattern().getNote() if self.getPattern() else None

    def existsPattern(self, pattern):   return pattern in self.patterns

    def __init__(self, **kwargs):
        super(Ma2Widget, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down = self._on_keyboard_down)

        if debug: self.setupDebug()
        Clock.schedule_once(self.update, 0)
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down = self._on_keyboard_down)
        self._keyboard = None
        
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        
        k = keycode[1]
        if 'alt' in modifiers:
            print(k)
        
        if   k == 'escape':                     App.get_running_app().stop() 
        elif k == 'backspace':                  self.printDebug()
        elif k == 'tab':                        self.switchActive()

        # THE MOST IMPORTANT KEY!
        elif k == 'f1':                         self.reRandomizeColors()

        if 'ctrl' in modifiers:
            if k == 'n':                        self.clearSong()
            elif k == 'l':                      self.loadCSV("test.ma2")
            elif k == 's':                      self.saveCSV("test.ma2")
            elif k == 'b':                      self.buildGLSL("test.glsl")

        #vorerst: nur tastatursteuerung - nerdfaktor und so :)
        if(self.theTrkWidget.active):
            if all(x in modifiers for x in ['shift', 'ctrl']):
                if   k == 'left':               self.getTrack().moveAllModules(-1)
                elif k == 'right':              self.getTrack().moveAllModules(+1)
            
            elif 'shift' in modifiers:
                if   k == 'up':                 self.getTrack().transposeModule(+1)
                elif k == 'down':               self.getTrack().transposeModule(-1)
                elif k == 'left':               self.getTrack().moveModule(-1)
                elif k == 'right':              self.getTrack().moveModule(+1)
                
            else:
                if   k == 'left':               self.getTrack().switchModule(-1)
                elif k == 'right':              self.getTrack().switchModule(+1)
                elif k == 'end':                self.getTrack().switchModule(0, to = -1)
                elif k == 'home':               self.getTrack().switchModule(0, to = +0)
                elif k == 'up':                 self.switchTrack(-1)
                elif k == 'down':               self.switchTrack(+1)

                elif k == 'numpadadd':          self.getTrack().addModule(self.getTrack().getLastModuleOff(), Pattern()) 
                elif k == 'c':                  self.getTrack().addModule(self.getTrack().getLastModuleOff(), self.getPattern())
                elif k == 'numpadsubstract':    self.getTrack().delModule()

                elif k == 'pageup':             self.getTrack().switchModulePattern(self.getPattern(+1))
                elif k == 'pagedown':           self.getTrack().switchModulePattern(self.getPattern(-1))

                elif k == 'a':                  self.getTrack().switchSynth(-1)
                elif k == 's':                  self.getTrack().switchSynth(+1)

        if(self.thePtnWidget.active) and self.getPattern():
            if all(x in modifiers for x in ['shift', 'ctrl']):
                if   k == 'left':               self.getPattern().moveNote(-1/32)
                elif k == 'right':              self.getPattern().moveNote(+1/32)

                elif k == 'pageup':             self.getPattern().stretchPattern(+1, scale = True)
                elif k == 'pagedown':           self.getPattern().stretchPattern(-1, scale = True)

            elif 'shift' in modifiers:
                if   k == 'left':               self.getPattern().stretchNote(-1/8)
                elif k == 'right':              self.getPattern().stretchNote(+1/8)
                elif k == 'up':                 self.getPattern().shiftAllNotes(+1)
                elif k == 'down':               self.getPattern().shiftAllNotes(-1)

                elif k == 'pageup':             self.getPattern().stretchPattern(+1)
                elif k == 'pagedown':           self.getPattern().stretchPattern(-1)

            elif 'ctrl' in modifiers:
                if   k == 'left':               self.getPattern().moveNote(-1/8)
                elif k == 'right':              self.getPattern().moveNote(+1/8)
                elif k == 'up':                 self.getPattern().shiftNote(+12)
                elif k == 'down':               self.getPattern().shiftNote(-12)

                elif k == 'numpadadd':          self.addPattern("new")
                elif k == 'numpadsubstract':    self.delPattern()

            else:
                if   k == 'left':               self.getPattern().switchNote(-1)
                elif k == 'right':              self.getPattern().switchNote(+1)
                elif k == 'up':                 self.getPattern().shiftNote(+1)
                elif k == 'down':               self.getPattern().shiftNote(-1)
                
                elif k == 'numpadadd':          self.getPattern().addNote(self.getNote(), append = True)
                elif k == 'c':                  self.getPattern().addNote(self.getNote(), append = False)
                elif k == 'numpadsubstract':    self.getPattern().delNote()
                
                elif k == 'pageup':             self.getTrack().switchModulePattern(self.getPattern(+1))
                elif k == 'pagedown':           self.getTrack().switchModulePattern(self.getPattern(-1))

        self.update()
        return True
        
    def update(self, dt = 0):
        #if self.theTrkWidget.active:
            self.theTrkWidget.drawTrackList(self.tracks, self.current_track) 
        #if self.thePtnWidget.active:
            self.thePtnWidget.drawPianoRoll(self.getPattern(), self.getModuleTranspose())
            
            self.updateLabels()
            
    def updateLabels(self, dt = 0):
        self.btnTitle.text = 'TITLE: ' + self.title
        self.btnPtnTitle.text = 'PTN: ' + self.getPatternName()
        self.btnPtnInfo.text = 'PTN LEN: ' + str(self.getPatternLen())

    def switchActive(self):
        self.theTrkWidget.active = not self.theTrkWidget.active
        self.thePtnWidget.active = not self.thePtnWidget.active

    def addTrack(self, name, synth = None):
        self.tracks.append(Track(name = name, synth = synth))
        if len(self.tracks) == 1: self.current_track = 0
        self.update()

    def switchTrack(self, inc):
        self.current_track = (self.current_track + inc) % len(self.tracks)
        self.update()
        
    def addPattern(self, name, length = None):
        if not length: length = self.getPatternLen()
        self.patterns.append(Pattern(name = name, length = length))

    def delPattern(self):
        if self.patterns and self.current_pattern is not None:
            del self.patterns[self.current_pattern]

    def clearSong(self):
        del self.tracks[:]
        del self.patterns[:]
        self.tracks = [Track(name = 'NJU TREK', synth = 'I_None')]
        self.patterns = [Pattern()]
        self.tracks[0].addModule(0, self.patterns[0])
        
        self.current_track = 0
        self.current_module = None
        self.current_pattern = 0
        self.current_note = None
        self.title = 'new Song'

        self.update()

############## ONLY THE MOST IMPORTANT FUNCTION! ############

    def reRandomizeColors(self):
        for p in self.patterns:
            p.randomizeColor()

###################### EXPORT FUNCTIONS #####################

    def loadCSV(self, filename):
        with open(filename) as in_csv:
            in_read = csv.reader(in_csv, delimiter='|')
            
            for r in in_read:
                self.title = r[0]
                self.tracks = []

                c = 2
                ### read tracks -- with modules assigned to dummy patterns
                for _ in range(int(r[1])):
                    track = Track(name = r[c], synth = int(r[c+1]))

                    c += 2
                    for _ in range(int(r[c])):
                        track.modules.append(Module(float(r[c+2]), Pattern(name=r[c+1]), int(r[c+3])))
                        c += 3

                    self.tracks.append(track)
                    c += 1

                ### read patterns
                for _ in range(int(r[c])):
                    pattern = Pattern(name = r[c+1], length = int(r[c+2]))
                    
                    c += 3
                    for _ in range(int(r[c])):
                        pattern.notes.append(Note(*(float(s) for s in r[c+1:c+4])))
                        c += 4
                        
                    self.patterns.append(pattern)

                ### reassign modules to patterns
                for t in self.tracks:
                    for m in t.modules:
                        for p in self.patterns:
                            if m.pattern.name == p.name: m.setPattern(p)


    def saveCSV(self, filename):
        out_str = self.title + '|' + str(len(self.tracks)) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.current_synth) + '|' + str(len(t.modules)) + '|'
            
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                # TODO check: pattern names have to be unique! in str(self.patterns.index(m.pattern.name))
        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + str(p.length) + '|' + str(len(p.notes))
            
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) + '|' + str(n.note_vel)

        # write to file
        out_csv = open("test.ma2", "w")
        out_csv.write(out_str)
        out_csv.close()
        
        print('out_str = ' + out_str)

    def buildGLSL(self, filename):
        # brilliant idea: first, treat modules like notes from the old sequencer --> e.g. play only note 24 + module.transpose (then put together -- which note in module?)

        # ignore empty tracks
        tracks = [t for t in self.tracks if t.modules]

        track_sep = [0] + list(accumulate([len(t.modules) for t in tracks]))
        pattern_sep = [0] + list(accumulate([len(p.notes) for p in self.patterns]))
        
        max_mod_off = max(t.getLastModuleOff() for t in tracks)

        float2str = lambda f: str(int(f)) + '.' if f==int(f) else str(f)

        nT  = str(len(tracks))
        nT1 = str(len(tracks) + 1)
        nM  = str(track_sep[-1])
        nP  = str(len(self.patterns))
        nP1 = str(len(self.patterns) + 1)
        nN  = str(pattern_sep[-1])

        out_str =  'int NO_trks = ' + nT + ';\n'
        out_str += 'int trk_sep[' + nT1 + '] = int[' + nT1 + '](' + ','.join(map(str, track_sep)) + ');\n'
        out_str += 'int trk_syn[' + nT + '] = int[' + nT + '](' + ','.join(str(t.getSynthIndex()) for t in tracks) + ');\n'
        out_str += 'float mod_on[' + nM + '] = float[' + nM + '](' + ','.join(float2str(m.mod_on) for t in tracks for m in t.modules) + ');\n'
        out_str += 'float mod_off[' + nM + '] = float[' + nM + '](' + ','.join(float2str(m.getModuleOff()) for t in tracks for m in t.modules) + ');\n'
        out_str += 'int mod_ptn[' + nM + '] = int[' + nM + '](' + ','.join(str(self.patterns.index(m.pattern)) for t in tracks for m in t.modules) + ');\n'
        out_str += 'int mod_transp[' + nM + '] = int[' + nM + '](' + ','.join(str(m.transpose) for t in tracks for m in t.modules) + ');\n'
        out_str += 'float inv_NO_tracks = ' + float2str(1./len(tracks)) + ';\n' # was this just for normalization? then call it global_volume or fix it via sigmoid
        out_str += 'float max_mod_off = ' + float2str(max_mod_off) + ';\n'

        out_str += 'int NO_ptns = ' + nP + ';\n'
        out_str += 'int ptn_sep[' + nP1 + '] = int[' + nP1 + '](' + ','.join(map(str, pattern_sep)) + ');\n'
        out_str += 'float note_on[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_on) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'float note_off[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_off) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'int note_pitch[' + nN + '] = int[' + nN + '](' + ','.join(str(int(n.note_pitch)) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'int note_vel[' + nN + '] = int[' + nN + '](' + ','.join(str(int(n.note_vel)) for p in self.patterns for n in p.notes) + ');\n'        

        # TODO: helper functions to find out which ones are the drums

        # TODO: format for the notes, but develop that in parallel with the pattern sequencer itself! (NITODO ~ NEXT IMPORTANT TASK)
        
        print()
        print(out_str)
        
    
###################### HANDLE BUTTONS #######################

#############################################################

    def pressTitle(self):     pass
    def pressTrkAdd(self):    pass
    def pressTrkDel(self):    pass
    def pressTrkInfo(self):   pass
    def pressModAdd(self):    pass
    def pressModDel(self):    pass
    def pressPtnLast(self):   pass
    def pressPtnTitle(self):  pass
    def pressPtnNext(self):   pass
    def pressPtnAdd(self):    pass
    def pressPtnDel(self):    pass
    def pressPtnInfo(self):   pass
    def pressNoteAdd(self):   pass
    def pressNoteDel(self):   pass
    def pressNotePitch(self): pass
    def pressNoteOn(self):    pass
    def pressNoteLen(self):   pass
    def pressNoteVel(self):   pass
    def pressLoadCSV(self):   pass
    def pressSaveCSV(self):   self.saveCSV(self.title + ".ma2")
    def pressBuildCode(self): pass

###################### DEBUG FUNCTIONS ######################

    def setupDebug(self):
        #DEBUG: test_list
        self.addTrack("Bassline", synth = "I_Bass")
        self.addTrack("Penetrator", synth = "Shit")
        self.addTrack("DerberScheißkick")
        self.addTrack("N R 4")
        self.addTrack("        &")
        self.addTrack("             Q M")
        self.addTrack("       'r'")
        self.addTrack("[T][E][A][M]")
        self.addTrack("       (2)(1)(0)")
        
        self.addPattern("bad performance", 7)
        self.addPattern("Lässig",2)
        self.current_pattern = 0
        
        self.tracks[1].addModule(5.5, self.patterns[0],-2, select = False)
        self.tracks[0].addModule(0, self.patterns[1], 0, select = False)
        self.tracks[0].addModule(2, self.patterns[1], 0, select = False)
        self.tracks[0].addModule(4, self.patterns[1], -3, select = False)
        self.tracks[0].addModule(6, self.patterns[1], -7, select = False)
        
        self.current_module = 0
        
        self.getPattern().addNote(Note(0.00,0.50,24), select = False)
        self.getPattern().addNote(Note(0.50,0.25,24), select = False)
        self.getPattern().addNote(Note(1.00,0.50,24), select = False)
        self.getPattern().addNote(Note(1.50,0.50,31), select = False)
        self.getPattern().addNote(Note(0.75,0.25,24), select = False)
        self.getPattern().addNote(Note(0.25,0.75,36), select = False)
        
        #self.getPattern().printNoteList()
        
        self.update()
        
    def printDebug(self):
        for t in self.tracks:
            print(t.name, len(t.modules))
            for m in t.modules:
                print(m.mod_on, m.pattern.name)
    
                
class Ma2App(App):
    title = 'Matze trying to be the Great Emperor again'
    
    def build(self):
        return Ma2Widget()

if __name__ == '__main__':
    Ma2App().run()

# Notes:
# USABILITY EINSPAREN! ERST WENN RELEVANT WIRD. (bin ja aktuell mein eigener Kunde)
# tracks in linear form with array for indexing
# patterns also in linear form with array for indexing
# limit pattern length to 3 letters (or scale with pattern length in monospaced font)
# features like "clone note", "clone pattern", "stretch pattern", etc. just in documentation (or 
# import code function? =O
# song view window, just for visualization of EVERYTHING
# pattern automation
# drums... kP
# TAB oder so: switch between track and pattern editor; rahmen um welches aktiv ist.

# TODO custom button, more nerd-stylish..

