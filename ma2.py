import os
#os.environ['KIVY_NO_CONSOLELOG'] = '1'

import kivy
kivy.require('1.10.0') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.text import Label as CoreLabel
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.animation import Animation
from itertools import accumulate
from functools import partial
from struct import pack, unpack
from numpy import clip, ceil, sqrt
from math import sin, exp, pi
from datetime import *
import pygame, wave
import csv, re
import operator
import sys
import pyperclip

from ma2_track import *
from ma2_pattern import *
from ma2_widgets import *
from ma2_synatize import synatize, synatize_build
from SFXGLWidget import *

GLfloat = lambda f: str(int(f))  + '.' if f==int(f) else str(f)[0 if f>=1 or f<0 or abs(f)<1e-4 else 1:].replace('-0.','-.')

Config.set('graphics', 'width', '1600')
Config.set('graphics', 'height', '1000')
#Config.set('kivy', 'log_level', 'warning')

def_synths = ['D_Drums', 'G_GFX', '__None']
def_drumkit = ['SideChn']

synths = def_synths
drumkit = def_drumkit

pattern_types = {'I': 'SYNTH', '_': 'NO TYPE', 'D':'DRUMS', 'G':'GFX'}

class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)

    current_track = None
    current_module = None
    current_note = None
    tracks = []
    patterns = []

    synatize_form_list = []
    synatize_main_list = []
    
    title = 'piover2'
    BPM = 80.;
    B_offset = 0.;
    
    btnTitle = ObjectProperty()
    
    debugMode = False
    numberInputMode = False
    numberInput = ''
    
    #updateAll = True # ah, fuck it. always update everythig. TODO improve performance... somehow.
    
    #helpers...
    def getTrack(self):                 return self.tracks[self.current_track] if self.current_track is not None else None
    def getLastTrack(self):             return self.tracks[-1] if self.tracks else None
    def getModule(self, offset=0):      return self.getTrack().getModule(offset) if self.getTrack() else None
    def getModuleTranspose(self):       return self.getModule().transpose if self.getModule() else 0
    def getModulePattern(self):         return self.getModule().pattern if self.getModule() else None
    def getModulePatternIndex(self):    return self.patterns.index(self.getModulePattern()) if self.patterns and self.getModulePattern() in self.patterns else -1
    def getPatternLen(self, offset=0):  return self.getPattern(offset).length if self.getPattern(offset) else None
    def getPatternName(self):           return self.getPattern().name if self.getPattern() else 'None'
    def getPatternIndex(self):          return self.patterns.index(self.getPattern()) if self.patterns and self.getPattern() and self.getPattern() in self.patterns else -1
    def getPatternSynthType(self):      return self.getPattern().synth_type if self.getPattern() else '_'
    def getNote(self):                  return self.getPattern().getNote() if self.getPattern() else None
    def existsPattern(self, pattern):   return pattern in self.patterns
    def getSameTypePatterns(self): return [p for p in self.patterns if p.synth_type in [self.getTrackSynthType(),'_']]
    def getSameTypePatternIndex(self): return self.getSameTypePatterns().index(self.getPattern()) if self.getPattern() and self.getPattern() in self.getSameTypePatterns() else -1
    def getTrackSynthType(self, track=None): return synths[(track if track else self.getTrack()).current_synth][0]
    def isDrumTrack(self):              return self.getTrackSynthType() == 'D'
    def getDefaultMaxNote(self, ptype=None): return 88 if not (ptype[0]=='D' if ptype else self.isDrumTrack()) else len(drumkit)

    def __init__(self, **kwargs):
        super(Ma2Widget, self).__init__(**kwargs)
        self._keyboard_request()

        self.setupInit()
        Clock.schedule_once(self.update, 0)

    def _keyboard_request(self, *args):
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down = self._on_keyboard_down)        
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down = self._on_keyboard_down)
        self._keyboard = None
        
    def _on_keyboard_down(self, keyboard, keycode, keytext, modifiers):
        
        k = keycode[1]
        
        if   k == 'escape':                     App.get_running_app().stop() 
        elif k == 'f8':                         self.toggleDebugMode()
        elif k == 'tab':                        self.switchActive()

        # THE MOST IMPORTANT KEY!
        elif k == 'f1':                         self.reRandomizeColors()

        elif k == 'f2':                         self.renameSong()
        elif k == 'f3':                         self.changeSongParameters()

        elif k == 'f5':                         self.loadSynths(update = True)

        elif k == 'f11':                        self.editCurve()

        elif k == 'f12':                        pygame.mixer.stop()

        if 'shift' in modifiers and 'ctrl' in modifiers:
            if k == 'b':                        self.buildGLSL(compileGL = True)

        elif 'ctrl' in modifiers:
            if k == 'n':                        self.clearSong()
            elif k == 'l':                      self.loadCSV_prompt()
            elif k == 's':                      self.saveCSV_prompt()
            elif k == 'b':                      self.buildGLSL()
            elif k == 'u':                      self.saveCSV(backup = True)
            elif k == 'z':                      self.loadCSV(backup = True)

        elif 'shift' in modifiers:
            pass

        else:
            if k == 'a':                        self.getTrack().switchSynth(-1, debug = self.debugMode)
            elif k == 's':                      self.getTrack().switchSynth(+1, debug = self.debugMode)

            elif k == 'pagedown':               self.getTrack().switchModulePattern(self.getPattern(+1))
            elif k == 'pageup':                 self.getTrack().switchModulePattern(self.getPattern(-1))

        # for precision work, press 'alt'
        inc_step = 1 if 'alt' not in modifiers else .25

        #vorerst: nur tastatursteuerung - nerdfaktor und so :)
        if(self.theTrkWidget.active):
            if 'shift' in modifiers and 'ctrl' in modifiers:
                if   k == 'left':               self.getTrack().moveAllModules(-inc_step)
                elif k == 'right':              self.getTrack().moveAllModules(+inc_step)
            
            elif 'shift' in modifiers:
                if   k == 'up':                 self.getTrack().transposeModule(+1)
                elif k == 'down':               self.getTrack().transposeModule(-1)
                elif k == 'left':               self.getTrack().moveModule(-inc_step)
                elif k == 'right':              self.getTrack().moveModule(+inc_step)
                elif k == 'home':               self.getTrack().moveModule(0, move_home = True)
                elif k == 'end':                self.getTrack().moveModule(0, move_end = True)

            elif 'ctrl' in modifiers:
                if k == '+'\
                  or k == 'numpadadd':          self.addTrack()
                elif k == '-'\
                  or k == 'numpadsubstract':    self.delTrack()
            
            else:
                if   k == 'left':               self.getTrack().switchModule(-1)
                elif k == 'right':              self.getTrack().switchModule(+1)
                elif k == 'end':                self.getTrack().switchModule(0, to = -1)
                elif k == 'home':               self.getTrack().switchModule(0, to = +0)
                elif k == 'up':                 self.switchTrack(-1)
                elif k == 'down':               self.switchTrack(+1)

                elif k == '+'\
                  or k == 'numpadadd':          self.addModuleWithNewPattern(self.getTrack().getLastModuleOff)
                elif k == 'c':                  self.getTrack().addModule(self.getTrack().getLastModuleOff(), self.getPattern(), transpose = self.getModuleTranspose())
                elif k == '-'\
                  or k == 'numpadsubstract':    self.getTrack().delModule()
                
                elif k == 'f6':                 self.renameTrack()
                elif k == 'f7':                 self.changeTrackParameters()
                elif k == 'f9':                 self.printPatterns()

        if(self.thePtnWidget.active) and self.getPattern():
            if 'shift' in modifiers and 'ctrl' in modifiers:
                if   k == 'pageup':             self.getPattern().stretchPattern(+inc_step, scale = True)
                elif k == 'pagedown':           self.getPattern().stretchPattern(-inc_step, scale = True)

            elif 'shift' in modifiers:
                if   k == 'left':               self.getPattern().stretchNote(-inc_step/8)
                elif k == 'right':              self.getPattern().stretchNote(+inc_step/8)
                elif k == 'up':                 self.getPattern().shiftAllNotes(+1)
                elif k == 'down':               self.getPattern().shiftAllNotes(-1)

                elif k == 'pageup':             self.getPattern().stretchPattern(+inc_step)
                elif k == 'pagedown':           self.getPattern().stretchPattern(-inc_step)
                
                elif k == 'backspace':          self.getPattern().setGap(to = 0)

            elif 'ctrl' in modifiers:
                if   k == 'left':               self.getPattern().moveNote(-inc_step/8)
                elif k == 'right':              self.getPattern().moveNote(+inc_step/8)
                elif k == 'up':                 self.getPattern().shiftNote(+12)
                elif k == 'down':               self.getPattern().shiftNote(-12)

                elif k == '+'\
                  or k == 'numpadadd':          self.addPattern(select = True)
                elif k == '*'\
                  or k == 'numpadmul':          self.addPattern(select = True, clone_current = True)
                elif k == '-'\
                  or k == 'numpadsubstract':    self.delPattern()

            else:
                if   k == 'left':               self.getPattern().switchNote(-1)
                elif k == 'right':              self.getPattern().switchNote(+1)
                elif k == 'home':               self.getPattern().switchNote(0, to = 0)
                elif k == 'end':                self.getPattern().switchNote(0, to = -1)

                elif k == 'up':                 self.getPattern().shiftNote(+1)
                elif k == 'down':               self.getPattern().shiftNote(-1)
                
                elif k == '+'\
                  or k == 'numpadadd':          self.getPattern().addNote(self.getNote(), append = True)
                elif k == 'c':                  self.getPattern().addNote(self.getNote(), append = True, clone = True)
                elif k == '*'\
                  or k == 'numpadmul':          self.getPattern().fillNote(self.getNote())
                elif k == '-'\
                  or k == 'numpadsubstract':    self.getPattern().delNote()
                elif k == 'spacebar':           self.getPattern().setGap(inc = True)
                elif k == 'backspace':          self.getPattern().setGap(dec = True)

                elif k == 'v':                  self.getPattern().getNote().setVelocity(self.numberInput)

                elif k == 'f6':                 self.renamePattern()
                elif k == 'f9':                 self.getPattern().printNoteList()
            
            if keytext.isdigit():               self.setNumberInput(keytext)
            else:                               self.setNumberInput('')

        # MISSING:
        #       moveAllNotes()
        #       scrolling in track view / note view / unlimited size
        #       mouse support
        #       openGL linking
        #       prompt for new song title before loading/saving (doesn't work at the moment because the BG app doesn't wait for the input)

        self.update()

        if self.debugMode:
            print('DEBUG -- KEY:', k, keytext, modifiers)
            self.printDebug()

        return True
        
    def update(self, dt = 0):
        self.theTrkWidget.drawTrackList(self) 
        self.thePtnWidget.drawPianoRoll(self)
        self.updateLabels()
            
    def updateLabels(self, dt = 0):
        self.btnTitle.text = 'TITLE: ' + self.title
        self.btnPtnTitle.text = 'PTN: ' + self.getPatternName() + ' (' + str(self.getSameTypePatternIndex()+1) + '/' + str(len(self.getSameTypePatterns())) + ') ' + pattern_types[self.getPatternSynthType()]
        self.btnPtnInfo.text = 'PTN LEN: ' + str(self.getPatternLen())

    def mainBackgroundColor(self):
        if self.debugMode:
            return(1,.3,0,.1)
        else:
            return (0,0,0,1)

    def switchActive(self):
        self.theTrkWidget.active = not self.theTrkWidget.active
        self.thePtnWidget.active = not self.thePtnWidget.active

    def renameSong(self):
        popup = InputPrompt(self, title = 'RENAME SONG', title_font = self.font_name, default_text = self.title)
        popup.bind(on_dismiss = self.handleRenameSong)
        popup.open()
    def handleRenameSong(self, *args):
        self._keyboard_request()
        self.title = args[0].text
        self.update()

    def changeSongParameters(self):
        par_string = str(self.BPM) + ' ' + str(self.B_offset)
        popup = InputPrompt(self, title = 'ENTER BPM, <SPACE>, STARTING BEAT', title_font = self.font_name, default_text = par_string)
        popup.bind(on_dismiss = self.handleChangeSongParameters)
        popup.open()
    def handleChangeSongParameters(self, *args):
        self._keyboard_request()
        pars = args[0].text.split()
        self.BPM = float(pars[0])
        self.B_offset = float(pars[1])
        self.theTrkWidget.updateMarker('OFFSET',self.B_offset)
        self.update()

    def renameTrack(self):
        popup = InputPrompt(self, title = 'RENAME TRACK', title_font = self.font_name, default_text = self.getTrack().name)
        popup.bind(on_dismiss = self.handleRenameTrack)
        popup.open()
    def handleRenameTrack(self, *args):
        self._keyboard_request()
        self.getTrack().name = args[0].text
        self.update()

    def changeTrackParameters(self):
        par_string = str(self.getTrack().getNorm())
        popup = InputPrompt(self, title = 'ENTER TRACK NORM FACTOR', title_font = self.font_name, default_text = par_string)
        popup.bind(on_dismiss = self.handleChangeTrackParameters)
        popup.open()
    def handleChangeTrackParameters(self, *args):
        self._keyboard_request()
        pars = args[0].text.split()
        self.getTrack().setParameters(norm = pars[0])
        self.update()

    def addTrack(self, name = 'NJU TREK', synth = None):
        self.tracks.append(Track(synths, name = name, synth = synth))
        if len(self.tracks) == 1: self.current_track = 0
        self.update()

    def switchTrack(self, inc):
        #when switching tracks, fix pattern types
        for m in self.getTrack().modules:
            m.pattern.setTypeParam(synth_type = self.getTrackSynthType(self.getTrack()))
        self.current_track = (self.current_track + inc) % len(self.tracks)
        self.update()

    def delTrack(self):
        if self.tracks and self.current_track is not None:
            if len(self.tracks) == 1: self.tracks.append(Track(synths)) # have to have one
            del self.tracks[self.current_track]
            self.current_track = min(self.current_track, len(self.tracks)-1)

    def getPattern(self, offset=0):
        if self.patterns and self.getModulePattern():
            if self.getModulePattern() in self.patterns:
                if offset == 0:
                    return self.patterns[self.patterns.index(self.getModulePattern())]
                else:
                    if self.debugMode:
                        return self.patterns[(self.patterns.index(self.getModulePattern()) + offset) % len(self.patterns)]
                    else:
                        patterns = self.getSameTypePatterns()
                        current_type_pattern = patterns[(patterns.index(self.getModulePattern()) + offset) % len(patterns)]
                        return current_type_pattern
            else:
                return self.patterns[0]
        else:
            return None
        
    def addPattern(self, name = "", length = None, select = False, clone_current = False):
        if name == "":
            popup = InputPrompt(self, title = 'ENTER PATTERN NAME', title_font = self.font_name, default_text = 'som seriösly nju pettorn')
            popup.bind(on_dismiss = self.handlePatternName)
            popup.open()
        if not length:
            length = self.getPatternLen()
            
        self.patterns.append(Pattern(name = name, length = length, synth_type = self.getTrackSynthType(), max_note = self.getDefaultMaxNote()))

        if clone_current:
            for n in self.getPattern().notes:
                self.patterns[-1].addNote(n);

        if select:
            self.getTrack().switchModulePattern(self.patterns[-1])

    def handlePatternName(self, *args, **kwargs):
        self._keyboard_request()
        p = self.patterns[-1]
        p.name = args[0].text
        while [i.name for i in self.patterns].count(p.name) > 1: p.name += '.' #unique names
        self.update()

    def addModuleWithNewPattern(self, mod_on):
        self.addPattern()
        self.getTrack().addModule(self.getTrack().getLastModuleOff(), self.patterns[-1]) 

    def renamePattern(self):
        popup = InputPrompt(self, title = 'ENTER PATTERN NAME', title_font = self.font_name, default_text = self.getPatternName())
        popup.bind(on_dismiss = self.handlePatternRename)
        popup.open()

    def handlePatternRename(self, *args, **kwargs):
        self._keyboard_request()
        p = self.getPattern()
        p.name = args[0].text
        while [i.name for i in self.patterns].count(p.name) > 1: p.name += '.' #unique names
        self.update()

    def delPattern(self):
        if self.patterns and self.getPattern() is not None:
            if len(self.patterns) == 1: self.patterns.append(Pattern()) # have to have one
            pattern_to_delete = self.getPattern()
            for t in self.tracks: t.prepareForPatternDeletion(self.getPattern())
            del self.patterns[self.patterns.index(pattern_to_delete)]

    def clearSong(self, no_renaming = False):
        del self.tracks[:]
        del self.patterns[:]
        self.tracks = [Track(synths = ['__None'], name = 'NJU TREK')]
        self.patterns = [Pattern()]
        self.tracks[0].addModule(0, self.patterns[0])
        
        self.current_track = 0
        self.current_module = None
        self.current_note = None

        if not no_renaming: self.renameSong()
        self.loadSynths(update = True)

    def setNumberInput(self, key):
        if key.isdigit():
            if not self.numberInputMode: self.numberInput = ''
            self.numberInputMode = True
            self.numberInput += key
        else:
            self.numberInputMode = False

    def setupInit(self):
        if '-debug' in sys.argv: self.toggleDebugMode()
        
        self.loadSynths()
        self.setupSomething()
        
        if len(sys.argv) > 1:
            self.title = sys.argv[1]
        elif os.path.exists('.last'):
            with open('.last') as in_tmp:
                self.title = in_tmp.read()
        else:
            pass

        self.loadSynths()
        Clock.schedule_once(self.loadCSV, 0)

        self.current_module = 0
        self.update()

############## ONLY THE MOST IMPORTANT FUNCTION! ############

    def reRandomizeColors(self):
        for p in self.patterns:
            p.randomizeColor()

################## AND THE OTHER ONE... #####################

    def loadSynths(self, update = False):
        
        global synths, drumkit
        
        filename = self.title + '.syn'
        if not os.path.exists(filename): filename = 'test.syn'
        
        self.synatize_form_list, self.synatize_main_list, drumkit = synatize(filename)
        
        synths = ['I_' + m['id'] for m in self.synatize_main_list if m['type']=='main']
        synths.extend(def_synths)
        
        drumkit = def_drumkit + drumkit
        self.thePtnWidget.updateDrumkit(drumkit)

        print('LOAD:', synths, drumkit)
        
        if update:
            for t in self.tracks: t.updateSynths(synths)
            self.update()

############### UGLY KIVY EXPORT FUNCTIONS #####################

    def loadCSV_prompt(self, backup = False, no_prompt = False):
        if backup or no_prompt:
            self.loadCSV(backup = backup)
        else:
            popup = InputPrompt(self, title = 'WHICH TRACK IS IT, WHICH YOU DESIRE?', title_font = self.font_name, default_text = self.title)
            popup.bind(on_dismiss = self.loadCSV_handleprompt)
            popup.open()
    def loadCSV_handleprompt(self, *args):
        self._keyboard_request()
        self.title = args[0].text.replace('.may','')
        self.loadCSV()
        self.update()

    def saveCSV_prompt(self, backup = False, no_prompt = False):
        if backup or no_prompt:
            self.saveCSV(backup = backup)
        else:
            popup = InputPrompt(self, title = 'SAVE ASS', title_font = self.font_name, default_text = self.title)
            popup.bind(on_dismiss = self.saveCSV_handleprompt)
            popup.open()
    def saveCSV_handleprompt(self, *args):
        self._keyboard_request()
        self.title = args[0].text.replace('.may','')
        self.saveCSV()
        self.update()

################## ACTUAL EXPORT FUNCTIONS ###################

    def loadCSV(self, dt = 0, backup = False):
        filename = self.title + '.may'
        if backup: filename = '.' + filename
                
        if not os.path.isfile(filename):
            if backup: return
            print(filename,'not around, start new track of that name')
            self.clearSong(no_renaming = True)
            return
                    
        self.loadSynths()
        print("... synths were reloaded. now read", filename)

        with open(filename) as in_csv:
            in_read = csv.reader(in_csv, delimiter='|')
            
            for r in in_read:
                self.title = r[0]
                self.tracks = []
                self.patterns = []
                self.BPM = float(r[1])
                self.B_offset = float(r[2])
                
                c = 4
                ### read tracks -- with modules assigned to dummy patterns
                for _ in range(int(r[3])):
                    track = Track(synths, name = r[c], synth = synths.index(r[c+1]) if r[c+1] in synths else -1)
                    track.setParameters(norm = float(r[c+2]))

                    c += 3
                    for _ in range(int(r[c])):
                        track.modules.append(Module(float(r[c+2]), Pattern(name=r[c+1]), int(r[c+3])))
                        c += 3

                    self.tracks.append(track)
                    c += 1

                ### read patterns
                for _ in range(int(r[c])):
                    pattern_type = r[c+2] if r[c+2] in pattern_types else '_'
                    pattern = Pattern(name = r[c+1], length = float(r[c+3]), synth_type = pattern_type, max_note = self.getDefaultMaxNote(pattern_type))
                    
                    c += 4
                    for _ in range(int(r[c])):
                        pattern.notes.append(Note(*(float(s) for s in r[c+1:c+4])))
                        c += 4
                        
                    #if pattern.name not in [p.name for p in self.patterns]: # filter for duplicates -- TODO is this a good idea?
                    self.patterns.append(pattern)

                ### reassign modules to patterns
                for t in self.tracks:
                    for m in t.modules:
                        for p in self.patterns:
                            if m.pattern.name == p.name:
                                m.setPattern(p)
                                

    def saveCSV(self, backup = False):
        filename = self.title + '.may'
        if backup: filename = '.' + filename
        
        out_str = '|'.join([self.title, str(self.BPM), str(self.B_offset), str(len(self.tracks))]) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.getSynthName()) + '|' + str(t.getNorm()) + '|' + str(len(t.modules)) + '|'
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + p.synth_type + '|' + str(p.length) + '|' + str(len(p.notes))
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) + '|' + str(n.note_vel)
                
        # write to file
        out_csv = open(filename, "w")
        out_csv.write(out_str)
        out_csv.close()
        print(filename, "written.")
        
        if not backup:
            out_tmp = open('.last', "w")
            out_tmp.write(self.title)
            out_tmp.close()

    def buildGLSL(self, compileGL = False):
        filename = self.title + '.glsl'

        # ignore empty tracks
        tracks = [t for t in self.tracks if t.modules]

        actually_used_patterns = [m.pattern for t in tracks for m in t.modules]
        patterns = [p for p in self.patterns if p in actually_used_patterns]

        track_sep = [0] + list(accumulate([len(t.modules) for t in tracks]))
        pattern_sep = [0] + list(accumulate([len(p.notes) for p in patterns]))
        
        max_mod_off = max(t.getLastModuleOff() for t in tracks)

        nT  = str(len(tracks))
        nT1 = str(len(tracks) + 1)
        nM  = str(track_sep[-1])
        nP  = str(len(patterns))
        nP1 = str(len(patterns) + 1)
        nN  = str(pattern_sep[-1])
        
        gf = open("template.matzethemightyemperor")
        glslcode = gf.read()
        gf.close()

        self.loadSynths()
        actually_used_synths = set(t.getSynthName()[2:] for t in self.tracks)
        actually_used_drums = set(n.note_pitch for p in patterns if p.synth_type == 'D' for n in p.notes)
        
        syncode, filtercode = synatize_build(self.synatize_form_list, self.synatize_main_list, actually_used_synths, actually_used_drums)

        # get release times
        syn_rel = []
        max_rel = 0
        max_drum_rel = 0
        print(self.synatize_main_list)
        for m in self.synatize_main_list:
            if m['type'] == 'main':
                syn_rel.append((float(m['release']) if 'release' in m else 0))
                if m['id'] in actually_used_synths:
                    max_rel = max(max_rel, syn_rel[-1])
            elif m['type'] == 'maindrum':
                max_drum_rel = max(max_drum_rel, (float(m['release']) if 'release' in m else 0))

        syn_rel.append(max_drum_rel)

        defcode  = '#define NTRK ' + nT + '\n'
        defcode += '#define NMOD ' + nM + '\n'
        defcode += '#define NPTN ' + nP + '\n'
        defcode += '#define NNOT ' + nN + '\n'
        
        #TODO: solve question - do I want max_mod_off here (perfect looping) or max_mod_off+max_rel (can listen to whole release decaying..)??
        seqcode  = 'float max_mod_off = ' + GLfloat(max_mod_off) + ';\n' + 4*' '
        seqcode += 'int drum_index = ' + str(synths.index('D_Drums')+1) + ';\n' + 4*' '
        if self.B_offset!=0: seqcode += 'time += '+'{:.4f}'.format(self.B_offset/self.BPM*60)+';\n' + 4*' '

        print("START TEXTURE")
        
        fmt = '@e'
        tex = b''
        #seqcode += 'int trk_sep[' + nT1 + '] = int[' + nT1 + '](' + ','.join(map(str, track_sep)) + ');\n' + 4*' '
        for s in track_sep:
            tex += pack(fmt, float(s))
        #seqcode += 'int trk_syn[' + nT + '] = int[' + nT + '](' + ','.join(str(t.getSynthIndex()+1) for t in tracks) + ');\n' + 4*' '
        for t in tracks:
            tex += pack(fmt, float(t.getSynthIndex()+1))
        #seqcode += 'float trk_norm[' + nT + '] = float[' + nT + '](' + ','.join(GLfloat(t.getNorm()) for t in tracks) + ');\n' + 4*' '
        for t in tracks:
            tex += pack(fmt, float(t.getNorm()))
        #seqcode += 'float trk_rel[' + nT + '] = float[' + nT + '](' + ','.join(GLfloat(syn_rel[t.getSynthIndex()]) for t in tracks) + ');\n' + 4*' '
        for t in tracks:
            tex += pack(fmt, float(syn_rel[t.getSynthIndex()]))
        #seqcode += 'float mod_on[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.mod_on) for t in tracks for m in t.modules) + ');\n' + 4*' '
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.mod_on))
        #seqcode += 'float mod_off[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.getModuleOff()) for t in tracks for m in t.modules) + ');\n' + 4*' '
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.getModuleOff()))
        #seqcode += 'int mod_ptn[' + nM + '] = int[' + nM + '](' + ','.join(str(self.patterns.index(m.pattern)) for t in tracks for m in t.modules) + ');\n' + 4*' '
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(patterns.index(m.pattern))) # this could use some purge-non-used-patterns beforehand...
        #seqcode += 'float mod_transp[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.transpose) for t in tracks for m in t.modules) + ');\n' + 4*' '
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.transpose))
        #seqcode += 'int ptn_sep[' + nP1 + '] = int[' + nP1 + '](' + ','.join(map(str, pattern_sep)) + ');\n' + 4*' '
        for s in pattern_sep:
            tex += pack(fmt, float(s))
        #seqcode += 'float note_on[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_on) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_on))
        #seqcode += 'float note_off[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_off) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_off))
        #seqcode += 'float note_pitch[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_pitch) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_pitch))
        #seqcode += 'float note_vel[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_vel * .01) for p in self.patterns for n in p.notes) + ');\n' + 4*' '  
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_vel * .01))
                
        texlength = int(len(tex))
        while ((texlength % 4) != 0):
            tex += bytes(10)
            texlength += 1

        texs = str(int(ceil(sqrt(float(texlength)/4.))))

        # Generate output header file
        array = []
        arrayf = []
        for i in range(int(ceil(texlength/2))):
            array += [ unpack('@H', tex[2*i:2*i+2]) ][0] 
            arrayf += [ unpack(fmt, tex[2*i:2*i+2]) ][0]

        text = "// Generated by tx210 / aMaySyn (c) 2018 NR4&QM/Team210\n\n#ifndef SEQUENCE_H\n#define SEQUENCE_H\n\n"
        text += "// Data:\n//"
        for val in arrayf:
            text += ' ' + str(val) + ','
        text += '\n'
        text += "const unsigned short sequence_texture[{:d}]".format(int(ceil(texlength/2)))+" = {"
        for val in array[:-1]:
            text += str(val) + ',' 
        text += str(array[-1]) + '};\n'
        text += "const int sequence_texture_size = " + str(texs) + ";"
        text += '\n#endif\n'

        # Write to file
        with open("sequence.h", "wt") as f:
            f.write(text)
            f.close()

        print("TEXTURE FILE WRITTEN (sequence.h)")

        glslcode = glslcode.replace("//DEFCODE",defcode).replace("//SEQCODE",seqcode).replace("//SYNCODE",syncode)\
                           .replace("//BPMCODE","const float BPM = "+GLfloat(self.BPM)+";").replace("//FILTERCODE",filtercode)

        glslcode = self.purgeExpendables(glslcode)

        with open("template.textureheader") as f:
            texheadcode = f.read()
            f.close()

        glslcode_frag = '#version 130\n' + glslcode.replace("//TEXTUREHEADER", texheadcode)

        with open("sfx.frag", "w") as out_file:
            out_file.write(glslcode_frag)
            
        print("GLSL CODE WRITTEN (sfx.frag) -- NR4-compatible fragment shader")

        # "for shadertoy" version
        tex_n = str(int(ceil(texlength/2)))
        texcode = 'const float sequence_texture[' + tex_n + '] = float[' + tex_n + '](' + ','.join(map(GLfloat, arrayf)) + ');\n'

        glslcode = glslcode.replace("//TEXCODE",texcode).replace('//TEXTUREHEADER', 'float rfloat(int off){return sequence_texture[off];}\n')

        with open(filename, "w") as out_file:
            out_file.write(glslcode)

        print("GLSL CODE WRITTEN (" + filename + ") - QM-compatible standalone fragment shader")

        pyperclip.copy(glslcode)
        
        if compileGL:
            self.compileShader(glslcode)

    def purgeExpendables(self, code):
        func_list = {}
        for i,l in enumerate(code.splitlines()):
            func_head = re.findall('(?<=float )\w*(?=[ ]*\(.*\))', l)
            if func_head:
                func_list.update({func_head[0]:i})

        expendable = []
        self.printIfDebug("The following functions will be purged")
        for f in func_list.keys():
            if code.count(f) == 1:
                f_from = code.find('float '+f)
                if f_from == -1: continue
                f_iter = f_from
                n_open = 0
                n_closed = 0
                while True:
                    n_open += int(code[f_iter] == '{')
                    n_closed += int(code[f_iter] == '}')
                    f_iter += 1
                    if n_open > 0 and n_closed == n_open: break

                expendable.append(code[f_from:f_iter])
                self.printIfDebug(f, 'line', func_list[f], '/', f_iter-f_from, 'chars')

        chars_before = len(code)
        for e in expendable: code = code.replace(e + '\n', '')
        chars_after = len(code)

        print('// total purge of', chars_before-chars_after, 'chars.')
        
        return code
    
###################### HANDLE BUTTONS #######################

# HAHA. no. we don't handle buttons.

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
    def pressLoadCSV(self):   self.loadCSV()
    def pressSaveCSV(self):   self.saveCSV()
    def pressBuildCode(self): self.buildGLSL()

###################### DEBUG FUNCTIONS ######################

    def setupSomething(self):
        self.addTrack("Bassline", synth = 0)
        self.addPattern("Sündig",2)
        self.tracks[0].addModule(0, self.patterns[0], 0, select = False)
        self.getPattern().addNote(Note(0.00,0.50,24), select = False)
        for i in range(8):
            self.addTrack(name = 'Track ' + str(i+2))
        
    def toggleDebugMode(self):
        self.debugMode = not self.debugMode
        print('DEBUG MODE IS', 'ON' if self.debugMode else 'OFF')
        
    def printIfDebug(self, *messages):
        if self.debugMode:
            print(*messages)
        
    def printDebug(self):
        print('DEBUG -- TRACKS:')        
        for t in self.tracks:
            print(t.name, len(t.modules))
            for m in t.modules:
                print('    MODULE @',m.mod_on, m.pattern.name)
                
        print('DEBUG -- current track', self.current_track, '/', self.getTrack().name, '/', self.getTrackSynthType())
        print('DEBUG -- same/none type patterns:', [p.name for p in self.getSameTypePatterns()])

        print('DEBUG -- PATTERNS:')
        for p in self.patterns:
            print(p.name, len(p.notes), p.length)
            
        print('DEBUG -- current pattern', self.getPatternIndex(), '/', self.getPatternName())

##################### NOW THE MIGHTY SHIT ##################

    def editCurve(self):
        popup = CurvePrompt(self, title = 'EDIT THE CURVE IF U DARE', title_font = self.font_name)
        popup.bind(on_dismiss = self.handleEditCurve)
        popup.open()
    def handleEditCurve(self, *args):
        self._keyboard_request()
        self.update()        

    def compileShader(self, shader, render_to_file = False):
        if not shader:
            shader = '''vec2 mainSound( float time ){ return vec2( sin(2.*radians(180.)*fract(440.0*time)) * exp(-3.0*time) ); }''' #assign for test purposes
        
        full_shader = '#version 130\n uniform float iTexSize;\n uniform float iBlockOffset;\n uniform float iSampleRate;\n\n' + shader

        self.music = None

        starttime = datetime.datetime.now()

        glwidget = SFXGLWidget(self)                 
        self.log = glwidget.newShader(full_shader)
        print(self.log)
        self.music = glwidget.music
        del glwidget

        if self.music == None :
            print('music is empty.')
            return
 
        pygame.mixer.pre_init(frequency=int(44100), size=-16, channels=2, buffer=4096)
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.stop()
        pygame.mixer.Sound(buffer=self.music).play()
        
        endtime = datetime.datetime.now()
        el = endtime - starttime

        print("Execution time", str(el.total_seconds()) + 's')

        if render_to_file:
            sfile = wave.open('file.wav','w')
            sfile.setframerate(44100)
            sfile.setnchannels(2)
            sfile.setsampwidth(2)
            sfile.writeframesraw(self.music)
            sfile.close()        

        self.update()

class InputPrompt(ModalView):
    
    text = ''

    def __init__(self, parent, **kwargs):
        title = kwargs.pop('title')
        title_font = kwargs.pop('title_font')
        default_text = kwargs.pop('default_text')
        self.text = default_text
        super(InputPrompt, self).__init__(**kwargs)

        self.auto_dismiss = False
        
        self.size_hint = (None, None)
        self.size = (500, 110)
        self.background = './transparent.png'
        
        content = BoxLayout(orientation = 'vertical')
        title = Label(text = title, font_name = title_font, size_hint=(None,.2), pos_hint={'center_x':.5, 'top':0})
        content.add_widget(title)
        tfield = TextInput(text = default_text, size_hint=(.9, None), height=36, pos_hint={'center_x':.5, 'bottom':0}, multiline=False, font_name = title_font)
        tfield.focus = True
        tfield.select_all()
        content.add_widget(tfield)

        self.add_widget(content)
       
        tfield.bind(on_text_validate = self.release)
        tfield.bind(focus = self.dismiss)
        
    def release(self, *args):
        self.text = args[0].text
        self.dismiss()

class CurvePrompt(ModalView):
    
    text = ''

    def __init__(self, parent, **kwargs):
        title = kwargs.pop('title')
        title_font = kwargs.pop('title_font')
        super(CurvePrompt, self).__init__(**kwargs)

        self.auto_dismiss = False
        
        self.size_hint = (None, None)
        self.size = (parent.width, parent.height*.8)
        self.background = './transparent.png'
        
        content = BoxLayout(orientation = 'vertical')
        title = Label(text = title, font_name = title_font, size_hint=(None,0.01), pos_hint={'center_x':.5, 'top':0})
        content.add_widget(title)

        cfield = CurveWidget(parent = self)
        content.add_widget(cfield)
               
        tfield = TextInput(text = 'hehe. hehe.', size_hint=(.9, None), height=36, pos_hint={'center_x':.5, 'bottom':0}, multiline=False, font_name = title_font)
        tfield.focus = True
        tfield.select_all()
        content.add_widget(tfield)

        self.add_widget(content)

        tfield.bind(on_text_validate = self.release)
        #tfield.bind(focus = self.dismiss)
        
    def _curveprompt_keydown(self, key, scancode, codepoint, modifiers):
        print("HA!")
        
    def release(self, *args):
        self.text = args[0].text
        self.dismiss()

       
class Ma2App(App):
    title = 'Matze trying to be the Great Emperor again'
    
    def build(self):
        return Ma2Widget()

if __name__ == '__main__':
    Ma2App().run()
