import os
#os.environ['KIVY_NO_CONSOLELOG'] = '1'

import kivy
kivy.require('1.10.1') # replace with your current kivy version !

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
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.animation import Animation
from itertools import accumulate
from functools import partial
from struct import pack, unpack
from numpy import clip, ceil, sqrt
from numpy.random import normal
from math import sin, exp, pi, floor, inf
from random import random, randint
from datetime import *
from copy import copy, deepcopy
from shutil import move, copyfile
from hashlib import md5
import pygame, wave
import csv, re
import operator
import sys
import pyperclip

from ma2_track import *
from ma2_pattern import *
from ma2_widgets import *
from ma2_synatize import synatize, synatize_build
from ma2_keys import interpretKeypress, doesActionChangeState, correctForNumpad
from SFXGLWidget import *

GLfloat = lambda f: str(int(f))  + '.' if f==int(f) else str(f)[0 if f>=1 or f<0 or abs(f)<1e-4 else 1:].replace('-0.','-.')

Window.size = (1600, 1000)

def_synfile = 'default.syn'
def_synths = ['D_Drums', 'G_GFX', '__None']
def_drumkit = ['SideChn']

synths = def_synths
drumkit = def_drumkit

pattern_types = {'I': 'SYNTH', '_': 'NO TYPE', 'D':'DRUMS', 'G':'GFX'}
loop_types = ['full', 'seamless', 'none']

class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)
    somePopup = ObjectProperty(None)

    info = {'title': 'piover2', 'BPM': '0:80', 'B_offset': 0., 'B_stop': inf, 'loop': 'full', 'stereo_delay': 2e-4}

    current_track = None
    tracks = []
    patterns = []
    track_solo = None
    current_param = 0

    synatize_form_list = []
    synatize_main_list = []
    last_synatized_forms = []
    stored_randoms = []
    synatize_param_list = []
    synatized_code_syn = ''
    synatized_code_drum = ''
    synfile = ''
    
    MODE_debug = False
    MODE_numberInput = False
    numberInput = ''
    lastNumberInput = ''

    #first idea for undo: save state at EVERY action
    undo_stack = []
    undo_max_steps = 50
    undo_pos = 0
    MODE_undo = False    
    stateChanged = True

    #headless mode just renders to file
    #./run.sh <ID> -headless
    MODE_headless = False
    outdir = 'out/'
    song_length = 0
    file_extra_information = ''

    lastCommand = ''
    lastSongCommand = ''
    lastImportPatternFilename = ''
    lastFixRandomsList = ''

    #helpers...
    def getTrack(self):                 return self.tracks[self.current_track] if self.current_track is not None else None
    def getLastTrack(self):             return self.tracks[-1] if self.tracks else None
    def getTotalLength(self):           return max(t.getLastModuleOff() for t in self.tracks)
    def getModule(self, offset=0):      return self.getTrack().getModule(offset) if self.getTrack() else None
    def getModuleTranspose(self):       return self.getModule().transpose if self.getModule() else 0
    def getModulePattern(self):         return self.getModule().pattern if self.getModule() else None
    def getModulePatternIndex(self):    return self.patterns.index(self.getModulePattern()) if self.patterns and self.getModulePattern() in self.patterns else -1
    def getInfo(self, key):             return self.info[key] if key in self.info else None
    def setInfo(self, key, value):      self.info[key] = value

    def getPatternLen(self, offset=0):  return self.getPattern(offset).length if self.getPattern(offset) else None
    def getPatternName(self):           return self.getPattern().name if self.getPattern() else 'None'
    def getPatternIndex(self):          return self.patterns.index(self.getPattern()) if self.patterns and self.getPattern() and self.getPattern() in self.patterns else -1
    def getPatternSynthType(self):      return self.getPattern().synth_type if self.getPattern() else '_'
    def getNote(self):                  return self.getPattern().getNote() if self.getPattern() else None
    def existsPattern(self, pattern):   return pattern in self.patterns

    def getTypeOnlyPatterns(self, only_type):
        return [p for p in self.patterns if p.synth_type == only_type]

    def getSameTypePatterns(self):
        return [p for p in self.patterns if p.synth_type in [self.getTrackSynthType(),'_']]
    
    def getSameTypePatternIndex(self):
        return self.getSameTypePatterns().index(self.getPattern()) if self.getPattern() and self.getPattern() in self.getSameTypePatterns() else -1
    
    def getTrackSynthType(self, track=None):
        return synths[(track if track else self.getTrack()).current_synth][0]
    
    def isDrumTrack(self):
        return self.getTrackSynthType() == 'D'
    
    def getDefaultMaxNote(self, ptype=None):
        return 88 if not (ptype[0]=='D' if ptype else self.isDrumTrack()) else len(drumkit)

    def getWAVFileName(self, count):
        return './' + self.outdir + '/' + self.getInfo('title') + '_' + str(count) + '.wav'

    def getWAVFileCount(self):
        if not os.path.isdir('./' + self.outdir): return '001'
        count = 1
        while os.path.isfile(self.getWAVFileName(f'{count:03d}')): count += 1
        return f'{count:03d}'

    def findPatternIndexByName(self, name):
        pattern_names = [p.name for p in self.patterns]
        return pattern_names.index(name) if name in pattern_names else -1

    def getTimeOfBeat(self, beat, bpmlist = None):
        return round(self.getTimeOfBeat_raw(beat, bpmlist = self.getInfo('BPM') if bpmlist is None else ' '.join(bpmlist)), 6)

    def getTimeOfBeat_raw(self, beat, bpmlist):
        beat = float(beat)
        if(type(bpmlist) != str):
            return beat * 60./bpmlist

        bpmdict = {float(part.split(':')[0]): float(part.split(':')[1]) for part in bpmlist.split()}
        if beat < 0:
            return 0
        if len(bpmdict) == 1:
            return beat * 60./bpmdict[0]
        time = 0
        for b in range(len(bpmdict) - 1):
            last_B = [*bpmdict][b]
            next_B = [*bpmdict][b+1]
            if beat < next_B:
                return time + (beat - last_B) * 60./ bpmdict[last_B]
            else:
                time += (next_B - last_B) * 60./ bpmdict[last_B]
        return time + (beat - next_B) * 60./ bpmdict[next_B]

################## OFFICIAL START OF STUFF... ##############

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
        if self.stateChanged:
            self.handleUndoStack()
            self.stateChanged = False

        k = keycode[1]
        keytext = correctForNumpad(keytext, k)

        if k == 'tab' and 'alt' in modifiers: return

        action = interpretKeypress(k, modifiers, self.theTrkWidget.active, self.thePtnWidget.active)

        if action:
            self.stateChanged = doesActionChangeState(action)

        inc_step = 1 if 'alt' not in modifiers else .125 # for precision work, press 'alt'

        if   action == 'EXIT':                          App.get_running_app().stop()
        elif action == 'DEBUG TOGGLE':                  self.toggleDebugMode()
        elif action == 'PANEL SWITCH':                  self.switchActive()
        elif action == 'COLORS RANDOMIZE':              self.reRandomizeColors()  # MOST IMPORTANT FEATURE!
        elif action == 'SONG RENAME':                   self.renameSong()
        elif action == 'ENTER SONG COMMAND':            self.promptSongCommand()
        elif action == 'ENTER COMMAND':                 self.promptCommand()
        elif action == 'SONG CHANGE LOOPING OPTION':    self.changeSongLoopingOption()
        elif action == 'SYNTH RELOAD':                  self.loadSynths()
        elif action == 'SYNTH RELOAD NEW RANDOMS':      self.loadSynths(reshuffle_randoms = True) 
        elif action == 'CURVE EDIT':                    self.editCurve()
        elif action == 'MUTE':                          self.muteSound()
        elif action == 'SHADER PLAY':                   self.buildGLSL(compileGL = True)
        elif action == 'SHADER RENDER':                 self.buildGLSL(compileGL = True, renderWAV = True)
        elif action == 'SHADER RENDER CURRENT MODULE':  self.buildGLSL(compileGL = True, onlyModule = True)            
        elif action == 'SONG CLEAR':                    self.clearSong()
        elif action == 'SONG LOAD':                     self.loadCSV_prompt()
        elif action == 'SONG SAVE':                     self.saveCSV_prompt()
        elif action == 'SHADER CREATE':                 self.buildGLSL()
        elif action == 'UNDO':                          self.stepUndoStack(-1)
        elif action == 'REDO':                          self.stepUndoStack(+1)
        elif action == 'SYNTH SELECT LAST':             self.getTrack().switchSynth(-1, debug = self.MODE_debug)
        elif action == 'SYNTH SELECT NEXT':             self.getTrack().switchSynth(+1, debug = self.MODE_debug)
        elif action == 'SYNTH SELECT':                  self.openSynthDialog()
        elif action == 'SYNTH SELECT RANDOM':           self.switchToRandomSynth()
        elif action == 'PATTERN SELECT NEXT':           self.getTrack().switchModulePattern(self.getPattern(+1))
        elif action == 'PATTERN SELECT LAST':           self.getTrack().switchModulePattern(self.getPattern(-1))
        elif action == 'DIALOG PATTERN IMPORT':         self.importPattern()
#        elif action == 'DIALOG PATTERN EXPORT':         self.exportPattern()
        elif action == 'SYNTH FILE RESET DEFAULT':      self.resetSynthsToDefault()
        elif action == 'TRACK CHANGE PARAMETERS':       self.changeTrackParameters()
        elif action == 'TRACK MUTE':                    self.getTrack().setParameters(mute = not self.getTrack().mute)
        elif action == 'TRACK SOLO':                    self.setTrackSolo()
        elif action == 'PURGE UNUSED PATTERNS':         self.purgeUnusedPatterns()

        if(self.theTrkWidget.active):
            if   action == 'TRACK SHIFT LEFT':          self.getTrack().moveAllModules(-inc_step)
            elif action == 'TRACK SHIFT RIGHT':         self.getTrack().moveAllModules(+inc_step)
            elif action == 'TRACK SHIFT ALL LEFT':      self.moveAllTracks(-inc_step)
            elif action == 'TRACK SHIFT ALL RIGHT':     self.moveAllTracks(+inc_step)
            elif action == 'MOD TRANSPOSE UP':          self.getTrack().transposeModule(+1)
            elif action == 'MOD TRANSPOSE DOWN':        self.getTrack().transposeModule(-1)
            elif action == 'MOD TRANSPOSE OCT UP':      self.getTrack().transposeModule(+12)
            elif action == 'MOD TRANSPOSE OCT DOWN':    self.getTrack().transposeModule(-12)
            elif action == 'MOD SHIFT LEFT':            self.getTrack().moveModule(-inc_step)
            elif action == 'MOD SHIFT RIGHT':           self.getTrack().moveModule(+inc_step)
            elif action == 'MOD SHIFT HOME':            self.getTrack().moveModule(0, move_home = True)
            elif action == 'MOD SHIFT END':             self.getTrack().moveModule(0, move_end = True, total_length = self.getTotalLength())
            elif action == 'MOD SHIFT ANYWHERE':        self.moveModuleAnywhereDialog()
            elif action == 'TRACK ADD NEW':             self.addTrack()
            elif action == 'TRACK ADD CLONE':           self.cloneTrack()
            elif action == 'TRACK DELETE':              self.delTrack()
            elif action == 'MOD SELECT LEFT':           self.getTrack().switchModule(-1)
            elif action == 'MOD SELECT RIGHT':          self.getTrack().switchModule(+1)
            elif action == 'MOD SELECT LAST':           self.getTrack().switchModule(0, to = -1)
            elif action == 'MOD SELECT FIRST':          self.getTrack().switchModule(0, to = +0)
            elif action == 'TRACK SELECT LAST':         self.switchTrack(-1)
            elif action == 'TRACK SELECT NEXT':         self.switchTrack(+1)
            elif action == 'MOD ADD NEW':               self.addModuleWithNewPattern()
            elif action == 'MOD ADD CLONE':             self.getTrack().addModule(self.getPattern(), transpose = self.getModuleTranspose())
            elif action == 'MOD DELETE':                self.getTrack().delModule()
            elif action == 'TRACK RENAME':              self.renameTrack()
            elif action == 'SYNTH CLONE HARD':          self.synthClone(hard = True)
            elif action == 'SYNTH FIX RANDOMS':         self.promptFixRandoms()
            elif action == 'SYNTH EDIT':                self.editSynth()
            elif action == 'SCROLL UP':                 self.theTrkWidget.scroll(axis = 'vertical', inc = -1)
            elif action == 'SCROLL DOWN':               self.theTrkWidget.scroll(axis = 'vertical', inc = +1)
            elif action == 'SCROLL LEFT':               self.theTrkWidget.scroll(axis = 'horizontal', inc = -1)
            elif action == 'SCROLL RIGHT':              self.theTrkWidget.scroll(axis = 'horizontal', inc = +1)
            elif action == 'ZOOM VERT IN':              self.theTrkWidget.scaleByFactor(axis = 'vertical', factor = 1.1)
            elif action == 'ZOOM VERT OUT':             self.theTrkWidget.scaleByFactor(axis = 'vertical', factor = .91)
            elif action == 'ZOOM HORZ OUT':             self.theTrkWidget.scaleByFactor(axis = 'horizontal', factor = .91)
            elif action == 'ZOOM HORZ IN':              self.theTrkWidget.scaleByFactor(axis = 'horizontal', factor = 1.1)

        if(self.thePtnWidget.active) and self.getPattern():
            if   action == 'PATTERN LONGER STRETCH':    self.getPattern().stretchPattern(+inc_step, scale = True)
            elif action == 'PATTERN SHORTER STRETCH':   self.getPattern().stretchPattern(-inc_step, scale = True)
            elif action == 'NOTE SHORTER':              self.getPattern().stretchNote(-inc_step/8)
            elif action == 'NOTE LONGER':               self.getPattern().stretchNote(+inc_step/8)
            elif action == 'NOTES TRANSPOSE ALL UP':    self.getPattern().shiftAllNotes(+1)
            elif action == 'NOTES TRANSPOSE ALL DOWN':  self.getPattern().shiftAllNotes(-1)
            elif action == 'PATTERN LONGER':            self.getPattern().stretchPattern(+inc_step)
            elif action == 'PATTERN SHORTER':           self.getPattern().stretchPattern(-inc_step)
            elif action == 'NOTE GAP ZERO':             self.getPattern().setGap(to = 0)
            elif action == 'NOTE SHIFT ALL LEFT':       self.getPattern().moveAllNotes(-inc_step/8)
            elif action == 'NOTE SHIFT ALL RIGHT':      self.getPattern().moveAllNotes(+inc_step/8)
            elif action == 'NOTE SHIFT LEFT':           self.getPattern().moveNote(-inc_step/8)
            elif action == 'NOTE SHIFT RIGHT':          self.getPattern().moveNote(+inc_step/8)
            elif action == 'NOTE TRANSPOSE OCT UP':     self.getPattern().shiftNote(+12)
            elif action == 'NOTE TRANSPOSE OCT DOWN':   self.getPattern().shiftNote(-12)
            elif action == 'PATTERN ADD NEW':           self.addPattern(select = True)
            elif action == 'PATTERN ADD CLONE':         self.addPattern(select = True, clone_current = True)
            elif action == 'PATTERN DELETE':            self.delPattern()
            elif action == 'NOTE SELECT LEFT':          self.getPattern().switchNote(-1)
            elif action == 'NOTE SELECT RIGHT':         self.getPattern().switchNote(+1)
            elif action == 'NOTE SELECT FIRST':         self.getPattern().switchNote(0, to = 0)
            elif action == 'NOTE SELECT LAST':          self.getPattern().switchNote(0, to = -1)
            elif action == 'NOTE TRANSPOSE UP':         self.getPattern().shiftNote(+1)
            elif action == 'NOTE TRANSPOSE DOWN':       self.getPattern().shiftNote(-1)
            elif action == 'NOTE ADD NEW':              self.getPattern().addNote(self.getNote(), append = True)
            elif action == 'NOTE ADD CLONE':            self.getPattern().addNote(self.getNote(), append = True, clone = True)
            elif action == 'NOTE CLONE SELECTION':      self.getPattern().fillNote(self.getNote())
            elif action == 'NOTE DELETE':               self.getPattern().delNote()
            elif action == 'GAP LONGER':                self.getPattern().setGap(inc = True)
            elif action == 'GAP SHORTER':               self.getPattern().setGap(dec = True)
            elif action == 'NOTE SET PAN':              self.setParameterFromNumberInput('pan')
            elif action == 'NOTE SET VELOCITY':         self.setParameterFromNumberInput('vel')
            elif action == 'NOTE SET SLIDE':            self.setParameterFromNumberInput('slide')
            elif action == 'NOTE SET AUX':              self.setParameterFromNumberInput('aux')
            elif action == 'PATTERN RENAME':            self.renamePattern()
            elif action == 'DEBUG PRINT NOTES':         self.getPattern().printNoteList()
            elif action == 'DRUMSYNTH CLONE HARD':      self.synthClone(drum = True, hard = True)
            elif action == 'DRUMSYNTH FIX RANDOMS':     self.promptFixRandoms(drum = True)
            elif action == 'DRUMSYNTH EDIT':            self.editSynth(drum = True)
            elif action == 'SCROLL UP':                 self.thePtnWidget.scroll(axis = 'vertical', inc = +1, is_drum = self.isDrumTrack())
            elif action == 'SCROLL DOWN':               self.thePtnWidget.scroll(axis = 'vertical', inc = -1, is_drum = self.isDrumTrack())
            elif action == 'SCROLL LEFT':               self.thePtnWidget.scroll(axis = 'horizontal', inc = -1, is_drum = self.isDrumTrack())
            elif action == 'SCROLL RIGHT':              self.thePtnWidget.scroll(axis = 'horizontal', inc = +1, is_drum = self.isDrumTrack())
            elif action == 'ZOOM VERT IN':              self.thePtnWidget.scaleByFactor(axis = 'vertical', factor = 1.1, is_drum = self.isDrumTrack())
            elif action == 'ZOOM VERT OUT':             self.thePtnWidget.scaleByFactor(axis = 'vertical', factor = .91, is_drum = self.isDrumTrack())
            elif action == 'ZOOM HORZ OUT':             self.thePtnWidget.scaleByFactor(axis = 'horizontal', factor = .91, is_drum = self.isDrumTrack())
            elif action == 'ZOOM HORZ IN':              self.thePtnWidget.scaleByFactor(axis = 'horizontal', factor = 1.1, is_drum = self.isDrumTrack())
      
            if keytext:
                if keytext.isdigit() or keytext in ['.', '-']:
                    self.setNumberInput(keytext)
                else:
                    self.setNumberInput('')

        self.update()

        if self.MODE_debug:
            print('DEBUG -- KEY:', k, keytext, modifiers)
            self.printDebug(verbose = True)

        return True
        
    def update(self, dt = 0):
        self.theTrkWidget.drawTrackList(self) 
        self.thePtnWidget.drawPianoRoll(self)
        self.updateLabels()
            
    def updateLabels(self, dt = 0):
        self.btnTitle.text = 'TITLE: ' + self.getInfo('title') + ' (LOOP: ' + self.getInfo('loop') + ')'
        self.btnPtnTitle.text = 'PTN: ' + self.getPatternName() + ' (' + str(self.getSameTypePatternIndex()+1) + '/' + str(len(self.getSameTypePatterns())) + ') ' + pattern_types[self.getPatternSynthType()]
        self.btnPtnInfo.text = 'PTN LEN: ' + str(self.getPatternLen())
        note = self.getNote()
        self.btnNoteInfo.text = 'NOTE INFO: --' if note is None else 'NOTE INFO:  [' + str(note.note_on) + '..' + str(note.note_off) + ']   PITCH ' + str(note.note_pitch) \
            + '   VEL ' + str(note.note_vel) + '   PAN ' + str(note.note_pan) + '   SLIDE ' + str(note.note_slide) + '   AUX ' + str(note.note_aux)

    def mainBackgroundColor(self):
        if self.MODE_debug:
            return(1,.3,0,.1)
        else:
            return (0,0,0,1)

    def switchActive(self):
        self.theTrkWidget.active = not self.theTrkWidget.active
        self.thePtnWidget.active = not self.thePtnWidget.active

    def muteSound(self):
        try:
            pygame.mixer.stop()
        except:
            pass

    def handleUndoStack(self):
        # is this everything I need to store?
        state = {
            'info': deepcopy(self.info),
            'tracks': deepcopy(self.tracks),
            'patterns': deepcopy(self.patterns),
            'current_track': self.current_track,
            'track_solo': self.track_solo
            }

        if self.MODE_undo:
            self.MODE_undo = False        
            self.undo_stack = self.undo_stack[:len(self.undo_stack) + self.undo_pos]
            self.undo_pos = 0

        if not self.undo_stack:
            self.undo_stack = [state]
        elif len(self.undo_stack) < self.undo_max_steps:
            self.undo_stack.append(state)
        else:
            self.undo_stack = self.undo_stack[1:] + [state]

    def stepUndoStack(self, inc):
        self.MODE_undo = True

        if not self.undo_stack: return
        if inc < 0 and self.undo_pos == 1 - len(self.undo_stack): return
        if inc > 0 and self.undo_pos == 0: return

        self.undo_pos += inc
        state = self.undo_stack[self.undo_pos-1]

        # DAMN! HAVE TO REBUILD TO NOT BREAK INTEGRITY...
        self.info = state['info']
        self.tracks = state['tracks']
        self.current_track = state['current_track']
        self.track_solo = state['track_solo']
        self.patterns = []
        for p in state['patterns']:
            self.patterns.append(p)
            for t in self.tracks:
                for m in t.modules:
                    if m.pattern.name == p.name:
                        m.setPattern(p)
        self.update()

    def renameSong(self):
        popup = InputPrompt(self, title = 'RENAME SONG', title_font = self.font_name, default_text = self.getInfo('title'))
        popup.bind(on_dismiss = self.handleRenameSong)
        popup.open()
    def handleRenameSong(self, *args):
        self._keyboard_request()
        self.setInfo('title', args[0].text)
        self.update()

    def tryToSetBPM(self, bpmlist):
        if type(bpmlist) == str:
            bpmlist = bpmlist.split()            
        if len(bpmlist) == 1:
            if ':' not in bpmlist[0]:
                bpmlist = ['0:' + bpmlist[0]]
            elif bpmlist[0].split(':')[0] != '0':
                bpmlist = [self.getInfo('BPM')] + bpmlist

        try:
            bpmlist.sort(key = lambda k: float(k.split(':')[0]))
            bpmdict = {}
            for part in bpmlist:
                if len(part.split(':')) != 2:
                    raise
                if part.split(':')[0] in bpmdict:
                    raise
                bpmdict.update({float(part.split(':')[0]): float(part.split(':')[1])})
            # now... everything in input is good? good.
            self.theTrkWidget.removeMarkersContaining('BPM')
            for beat in bpmdict:
                marker_label = 'BPM' + GLfloat(bpmdict[beat])
                if marker_label[-1] == '.':
                    marker_label = marker_label[:-1]
                self.theTrkWidget.updateMarker(marker_label, beat, style = 'BPM')
            self.setInfo('BPM', ' '.join(bpmlist))
            return True

        except:
            print("couldn't set BPM as", bpmlist, "try again sometime...", sep="\n")
            return False

    def changeSongLoopingOption(self):
        loop = self.getInfo('loop')
        if loop == loop_types[-1]:
            self.setInfo('loop', loop_types[0])
        else:
            self.setInfo('loop', loop_types[loop_types.index(loop) + 1])
        print('Looping mode is now', self.getInfo('loop'))

    def renameTrack(self):
        popup = InputPrompt(self, title = 'RENAME TRACK', title_font = self.font_name, default_text = self.getTrack().name)
        popup.bind(on_dismiss = self.handleRenameTrack)
        popup.open()
    def handleRenameTrack(self, *args):
        self._keyboard_request()
        self.getTrack().name = args[0].text
        self.update()

    def changeTrackParameters(self):
        par_string = str(100 * self.getTrack().getNorm())
        popup = InputPrompt(self, title = 'ENTER TRACK NORM FACTOR IN %', title_font = self.font_name, default_text = par_string)
        popup.bind(on_dismiss = self.handleChangeTrackParameters)
        popup.open()
    def handleChangeTrackParameters(self, *args):
        self._keyboard_request()
        pars = args[0].text.split()
        self.getTrack().setParameters(norm = 0.01 * float(pars[0]))
        self.update()


    def promptSongCommand(self):
        popup = InputPrompt(self, title = 'ENTER BPM / OFFSET / STOP / STEREO ...', title_font = self.font_name, default_text = self.lastSongCommand)
        popup.bind(on_dismiss = self.handlePromptSongCommand)
        popup.open()
    def handlePromptSongCommand(self, *args):
        self._keyboard_request()
        if args[0].validated:
            executed = self.executeCommand(args[0].text)
            if executed:
                self.lastSongCommand = args[0].text
        self.update()

    def promptCommand(self):
        popup = InputPrompt(self, title = 'ENTER CMD (ask QM how they work)', title_font = self.font_name, default_text = self.lastCommand)
        popup.bind(on_dismiss = self.handlePromptCommand)
        popup.open()
    def handlePromptCommand(self, *args):
        self._keyboard_request()
        if args[0].validated:
            executed = self.executeCommand(args[0].text)
            if executed:
                self.lastCommand = args[0].text
        self.update()


    def addTrack(self, name = 'NJU TREK', synth = None):
        if not self.tracks:
            self.tracks.append(Track(synths, name = name, synth = synth))
            self.current_track = 0
        elif self.current_track:
            self.current_track += 1
            self.tracks.insert(self.current_track, Track(synths, name = name, synth = synth))
        self.update()

    def cloneTrack(self):
        clone = Track(synths, name = '^ CLONE')
        clone.cloneTrack(self.getTrack())
        self.current_track += 1
        self.tracks.insert(self.current_track, clone)
        print("lol")
        self.update()

    def switchTrack(self, inc):
        #when switching tracks, fix pattern types
        for m in self.getTrack().modules:
            m.pattern.setTypeParam(synth_type = self.getTrackSynthType(self.getTrack()))
        self.current_track = (self.current_track + inc) % len(self.tracks)
        self.update()

    def delTrack(self):
        if self.tracks and self.current_track is not None:
            del self.tracks[self.current_track]
            self.current_track = min(self.current_track, len(self.tracks)-1)
            if not self.tracks:
                self.clearSong(no_renaming = True)

    def moveAllTracks(self, inc):
        for t in self.tracks:
            if t.modules and t.getFirstModuleOn() + inc < 0:
                return
        for t in self.tracks:
            t.moveAllModules(inc)

    def setTrackSolo(self):
        if self.track_solo:
            self.track_solo = None
        else:
            self.track_solo = self.current_track
            self.getTrack().setParameters(mute = False)

    def moveModuleAnywhereDialog(self):
        popup = InputPrompt(self, title = 'BEAT TO MOVE TO (EMPTY TO CANCEL)', title_font = self.font_name, default_text = '')
        popup.bind(on_dismiss = self.handleMoveModuleAnywhere)
        popup.open()
    def handleMoveModuleAnywhere(self, *args):
        self._keyboard_request()
        if args[0] == '':
            return
        self.getTrack().moveModuleAnywhere(float(args[0].text.split()[0]))
        self.update()

    def getPattern(self, offset=0):
        if self.patterns and self.getModulePattern():
            if self.getModulePattern() in self.patterns:
                if offset == 0:
                    return self.patterns[self.patterns.index(self.getModulePattern())]
                else:
                    if self.MODE_debug:
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

    def replacePatternByNameIfPossible(self, newPattern):
            find_index = self.findPatternIndexByName(newPattern.name)
            if find_index == -1:
                self.patterns.append(newPattern)
            else:
                self.patterns[find_index].replaceWith(newPattern)
                print("Replaced Pattern at index", find_index)

            if self.MODE_debug:
                self.patterns[find_index].printNoteList()

    def handlePatternName(self, *args, **kwargs):
        self._keyboard_request()
        p = self.patterns[-1]
        p.name = args[0].text
        while [i.name for i in self.patterns].count(p.name) > 1: p.name += '.' #unique names
        self.update()

    def addModuleWithNewPattern(self):
        self.addPattern()
        self.getTrack().addModule(self.patterns[-1]) 

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
        self.patterns = []
        self.current_track = 0

        if not no_renaming: self.renameSong()
        self.loadSynths()

    def setNumberInput(self, key):
        if not key:
            self.MODE_numberInput = False

        if not self.MODE_numberInput:
            self.numberInput = ''
            self.MODE_numberInput = True

        if key.isdigit():
            self.numberInput += key
        elif key == '.' and '.' not in self.numberInput:
            self.numberInput += key
        elif key == '-':
            self.numberInput = ('-' + self.numberInput).replace('--','')

    def setParameterFromNumberInput(self, parameter):
        if self.numberInput:
            self.lastNumberInput = self.numberInput
        self.getPattern().getNote().setParameter(parameter, self.lastNumberInput)

    def setupInit(self):

        if '-headless' in sys.argv: self.MODE_headless = True
        if '-debug' in sys.argv: self.toggleDebugMode()
        
        self.loadSynths(update = False)
        self.setupTest()
        
        if len(sys.argv) > 1:
            self.setInfo('title', sys.argv[1].split('.')[0])
        elif os.path.exists('.last'):
            with open('.last') as in_tmp:
                self.setInfo('title', in_tmp.read())

        Clock.schedule_once(self.loadCSV, 0)

        if self.MODE_headless:
            if not os.path.isdir('./' + self.outdir): os.mkdir(self.outdir)
            Clock.schedule_once(self.instantCompileGLSL, 0.1)

        self.update()

############ ONE OF MY NICER IDEAS: COMMAND PROMPT ##########
    def executeCommand(self, cmd_str = ''):
        try:
            cmd = [s.lower() for s in cmd_str.split()]
            
            #e.g. SET VEL <B_min> <B_max> LIN <value_min> <value_max> <stepsize>
            # or TRANSFORM VEL <B_min> <B_max> LIN <shift> <scale> <stepsize>
            if cmd[0] == 'set':
                parameter = cmd[1]
                B_min = float(cmd[2])
                B_max = float(cmd[3])
                shape = cmd[4].lower()

                if not self.getPattern() or not self.getPattern().notes:
                    affected_notes = []
                else:
                    affected_notes = [n for n in self.getPattern().notes if n.note_on >= B_min and n.note_on < B_max]

                # CONST: set all values to const for notes in [B_min, B_max]
                if shape == 'const':
                    const_value = float(cmd[5])
                    for note in affected_notes:
                        note.setParameter(parameter, const_value)
                    return True

                # LIN: interpolate linearly from (B_min, value_min) to (B_max, value_max)
                elif shape in ['linear', 'lin']:
                    min_value = float(cmd[5])
                    max_value = float(cmd[6])
                    step_size = 1 if len(cmd) < 8 else float(cmd[7])
                    for note in affected_notes:
                        lin_delta = (max_value - min_value) * (note.note_on - B_min) / (B_max - B_min)
                        lin_value = min_value + step_size * floor(lin_delta / step_size)
                        note.setParameter(parameter, round(lin_value, 2))
                    return True
                
                # RND: random values between [value_min, value_max] between [B_min, B_max] (stepsize is resolution)
                elif shape in ['random', 'rnd']:
                    min_value = float(cmd[5])
                    max_value = float(cmd[6])
                    step_size = 1 if len(cmd) < 8 else float(cmd[7])
                    rnd_scale = floor((max_value - min_value)/step_size)
                    for note in affected_notes:
                        rnd_value = min_value + step_size * floor((rnd_scale + 1) * random.random())
                        note.setParameter(parameter, round(rnd_value, 2))
                    return True

                elif shape == 'reset':
                    for note in affected_notes:
                        note.setParameter(parameter, None)
                    return True

                else:
                    print('COMMAND NOT SUPPORTED:\n', cmd)
                    return False

            # or TRANSFORM VEL <B_min> <B_max> LIN <shift> <scale> <stepsize>
            elif cmd[0] == 'transform':
                parameter = cmd[1]
                B_min = float(cmd[2])
                B_max = float(cmd[3])
                shape = cmd[4].lower()

                if not self.getPattern() or not self.getPattern().notes:
                    affected_notes = []
                else:
                    affected_notes = [n for n in self.getPattern().notes if n.note_on >= B_min and n.note_on < B_max]

                # LIN: linear transformation
                if shape in ['linear', 'lin']:
                    lin_shift = float(cmd[5])
                    lin_scale = float(cmd[6])
                    # I don't know why it gets executed twice, but don't care because I want to switch to Qt anyway
                    # replace lin_scale -> sqrt(lin_scale)
                    # replace lin_shift -> lin_shift/(sqrt(lin_scale)+1)
                    step_size = 1 if len(cmd) < 8 else float(cmd[7])
                    for note in affected_notes:
                        current_value = note.getParameter(parameter)
                        transformed_value = lin_shift/(sqrt(lin_scale)+1) + sqrt(lin_scale) * current_value
                        transformed_value = step_size * round(transformed_value / step_size)
                        note.setParameter(parameter, round(transformed_value, 3))
                    return True

                if shape == 'clamp':
                    min_value = float(cmd[5])
                    max_value = float(cmd[6])
                    for note in affected_notes:
                        current_value = note.getParameter(parameter)
                        note.setParameter(parameter, clip(current_value, min_value, max_value))
                    return True

                else:
                    print('COMMAND NOT SUPPORTED:\n', cmd)
                    return False

            elif cmd[0] == 'randomize':
                # randomize: spread values around their current value in a gaussian fashion
                # e.g RANDOMIZE POS <B_min> <B_max> <spread> [<stepsize>]
                parameter = cmd[1].lower()
                B_min = float(cmd[2])
                B_max = float(cmd[3])

                if not self.getPattern() or not self.getPattern().notes:
                    affected_notes = []
                else:
                    affected_notes = [n for n in self.getPattern().notes if n.note_on >= B_min and n.note_on < B_max]

                gauss_spread = float(cmd[4])
                step_size = 1 if parameter not in ['pos', 'len'] else 1/32
                if len(cmd) > 5:
                    parse_ratio = cmd[5].split('/')
                    if len(parse_ratio) == 2:
                        step_size = float(parse_ratio[0]) / float(parse_ratio[1])
                    else:
                        step_size = float(cmd[5])

                if parameter in ['pos', 'len']:
                    min_value = 0
                    max_value = self.getPatternLen()
                    precision = 6
                else:
                    min_value = None
                    max_value = None
                    precision = 2

                for note in affected_notes:
                    current_value = note.getParameter(parameter)
                    rnd_value = step_size * round(normal(0, gauss_spread) / step_size)
                    note.setParameter(parameter, round(current_value + rnd_value, precision), min_value = min_value, max_value = max_value)
                return True

            elif cmd[0] == 'bpm':
                if len(cmd) == 1:
                    self.lastSongCommand = 'BPM ' + self.getInfo('BPM')
                    return False
                else:
                    return self.tryToSetBPM(cmd[1:])

            elif cmd[0] == 'offset':
                if len(cmd) == 1:
                    self.lastSongCommand = 'OFFSET ' + str(self.getInfo('B_offset'))
                    return False
                else:
                    value = float(cmd[1])
                    if value > 0:
                        self.setInfo('B_offset', value)
                        self.theTrkWidget.updateMarker('OFFSET', self.getInfo('B_offset'))
                    else:
                        self.setInfo('B_offset', 0)
                        self.theTrkWidget.removeMarkersContaining('OFFSET')
                    return True

            elif cmd[0] == 'stop':
                if len(cmd) == 1:
                    self.lastSongCommand = 'STOP ' + str(self.getInfo('B_stop'))
                    return False
                else:
                    value = float(cmd[1])
                    if value > self.getInfo('B_offset') and value <= self.getTotalLength():
                        self.setInfo('B_stop', value)
                        self.theTrkWidget.updateMarker('STOP', self.getInfo('B_stop'))
                    else:
                        self.setInfo('B_stop', inf)
                        self.theTrkWidget.removeMarkersContaining('STOP')
                    return True

            elif cmd[0] == 'stereo':
                if len(cmd) == 1:
                    self.lastSongCommand = 'STEREO ' + str(self.getInfo('stereo_delay'))
                    return False
                else:
                    value = float(cmd[1])
                    print("stereo_delay was", self.getInfo('stereo_delay'), "- is now", value)
                    self.setInfo('stereo_delay', value)
                    return True
                    
            else:
                print('COMMAND NOT SUPPORTED:\n', cmd)
                return False

        except Exception as exc:
            print('COMMAND ERRONEOUS (u stupid hobo):\n', cmd, '\n', type(exc))
            raise
            return False

############## ONLY THE MOST IMPORTANT FUNCTION! ############

    def reRandomizeColors(self):
        for p in self.patterns:
            p.randomizeColor()

################## AND THE OTHER ONE... #####################

    def loadSynths(self, update = True, reshuffle_randoms = False):
        
        global synths, drumkit
        old_drumkit = drumkit

        self.synfile = self.getInfo('title') + '.syn'
        if not os.path.exists(self.synfile): self.synfile = def_synfile

        self.synatize_form_list, self.synatize_main_list, drumkit, self.stored_randoms, self.synatize_param_list \
            = synatize(self.synfile, stored_randoms = self.stored_randoms, reshuffle_randoms = reshuffle_randoms)

        synths = ['I_' + m['id'] for m in self.synatize_main_list if m['type']=='main']
        synths.extend(def_synths)

        drumkit = def_drumkit + drumkit
        self.thePtnWidget.updateDrumkit(drumkit)

        #print('LOAD:', synths, drumkit)

        if update:
            for t in self.tracks:
                t.updateSynths(synths)
            for p in self.getTypeOnlyPatterns('D'):
                p.updateDrumkit(old_drumkit, drumkit)
            self.update()

    def resetSynthsToDefault(self):
        synfile = self.getInfo('title') + '.syn'
        if os.path.exists(synfile): copyfile(synfile, synfile + '.bak')
        copyfile(def_synfile, synfile)
        print("New", synfile, "copied from", def_synfile, "and old version kept as", synfile + '.bak')

    def synthClone(self, hard = False, drum = False, formID = None):
        self.loadSynths()
        if not self.synatized_code_syn:
            print("No code in memory! Compile once before you clone!")
            return
        if not hard: # soft cloning would be "copy every relevant line in the synfile, not the synatized_forms"
            print("soft cloning not yet implemented for synths or drum synths!")
            return
        if drum and self.getTrackSynthType() != 'D':
            return
        if not drum and self.getTrackSynthType() == 'D':
            print("Current Track is drum track, go do Pattern (SHIFT+TAB) to clone single drums")
            return

        count = 0
        if drum:
            oldID = drumkit[self.getPattern().getDrumIndex()]
            if formID is None:
                while True:
                    formID = oldID + str(count)
                    if formID not in drumkit: break
                    count += 1
        else:
            oldID = self.getTrack().getSynthName()
            if formID is None:
                while True:
                    formID = oldID + '.' + str(count)
                    print("TRYING", formID, synths)
                    if 'I_' + formID not in synths: break
                    count += 1

        try:
            formTemplate = next(form for form in self.last_synatized_forms if form['id'] == oldID)
            formType = formTemplate['type']
            formMode = formTemplate['mode']
            formBody = ' '.join(key + '=' + formTemplate[key] for key in formTemplate if key not in  ['type', 'id', 'mode'])
            if formMode: formBody += ' mode=' + ','.join(formMode)
        except StopIteration:
            print("Current (drum) synth is not compiled yet. Do so and try again.")
            return
        except:
            print("could not CLONE HARD:", formID, formTemplate)
            raise

        synfile = self.getInfo('title') + '.syn'
        if not os.path.exists(synfile): copyfile(def_synfile, synfile)
        with open(synfile, mode='a') as filehandle:
            filehandle.write('\n' + formType + 4*' ' + formID + 4*' ' + formBody)

        self.loadSynths()


    def promptFixRandoms(self, drum = False):
        prompt_title = 'Enter List of blah=.1337 etc. to fix '
        if drum:
            if self.getTrackSynthType() != 'D': return
            formID = drumkit[self.getPattern().getNote().note_pitch]
            prompt_title += 'DRUM ' + formID
        else:
            formID = self.getTrack().getSynthName()
            prompt_title += 'SYNTH ' + formID
        popup = InputPrompt(self, title = prompt_title, title_font = self.font_name, default_text = self.lastFixRandomsList, extra_parameters = {'formID': formID, 'drum': drum})
        popup.bind(on_dismiss = self.handlePromptFixRandoms)
        popup.open()
    def handlePromptFixRandoms(self, *args):
        self._keyboard_request()
        if args[0].validated:
            self.synthCloneWithFixedRandoms(args[0].text, **args[0].extra_parameters)
            self.lastFixRandomsList = args[0].text
        self.update()

    def synthCloneWithFixedRandoms(self, fixlist, formID, drum):
        if drum:
            pretend_synths, pretend_drums = ('D_Drums', formID)
        else:
            pretend_synths, pretend_drums = ('I_' + formID, None)

        fixed_randoms = {}
        fixlist = fixlist.replace('\t', ' ').replace('\n', '')
        for fix in fixlist.split():
            if '=' in fix:
                random_ID, random_fix = fix.split('=')
                fixed_randoms.update({random_ID: float(random_fix)})

        for form in self.stored_randoms:
            if form['id'] in fixed_randoms:
                form['value'] = fixed_randoms[form['id']]
                print("found", form['id'], form['value'], '\n')

        formID = formID + '.' + md5(fixlist.encode('utf8')).hexdigest()[0:4]

        self.synatize_form_list, self.synatize_main_list, drumkit, self.stored_randoms, self.synatize_param_list\
            = synatize(self.synfile, stored_randoms = self.stored_randoms, reshuffle_randoms = False)
        self.synatized_code_syn, self.synatized_code_drum, paramcode, filtercode, self.last_synatized_forms\
            = synatize_build(self.synatize_form_list, self.synatize_main_list, self.synatize_param_list, pretend_synths, pretend_drums)

        self.synthClone(hard = True, drum = drum, formID = formID)


    def synthDeactivate(self, drum = False):
        if drum:
            if self.getTrackSynthType() != 'D': return
            formID = drumkit[self.getPattern().getNote().note_pitch]
        else:
            formID = self.getTrack().getSynthName()

        synfile = self.getInfo('title') + '.syn'
        tmpfile = '.' + synfile
        if not os.path.exists(synfile): copyfile(def_synfile, synfile)
        move(synfile, tmpfile)
        with open(tmpfile, mode='r') as tmp_handle:
            with open(synfile, mode='w') as new_handle:
                for line in tmp_handle.readlines():
                    lineparse = line.split()
                    if len(lineparse)>2 and lineparse[0] in ['main', 'maindrum'] and lineparse[1] == formID:
                        new_handle.write('#' + line)
                    else:
                        new_handle.write(line)

        #TODO: some feature to reactivate ;)
        self.loadSynths()

    def synthChangeName(self, newID, drum = False):
        if drum:
            if self.getTrackSynthType() != 'D': return
            formID = drumkit[self.getPattern().getNote().note_pitch]
        else:
            if self.getTrackSynthType() == 'D': return
            formID = self.getTrack().getSynthName()

        synfile = self.getInfo('title') + '.syn'
        tmpfile = '.' + synfile
        if not os.path.exists(synfile): copyfile(def_synfile, synfile)
        move(synfile, tmpfile)
        with open(tmpfile, mode='r') as tmp_handle:
            with open(synfile, mode='w') as new_handle:
                for line in tmp_handle.readlines():
                    lineparse = line.split()
                    if len(lineparse)>2 and lineparse[0] in ['main', 'maindrum'] and lineparse[1] == formID:
                        new_handle.write(line.replace(' '+formID+' ', ' '+newID+' '))
                    else:
                        new_handle.write(line)
        if drum:
            drumkit[drumkit.index(formID)] = newID
        else:
            synths[synths.index(self.getTrack().getSynthFullName())] = self.getTrack().getSynthType() + '_' + newID
        self.loadSynths()

    def editSynth(self, drum = False):
        if drum and self.getTrack().getSynthType() != 'D': return
        if not drum and self.getTrack().getSynthType() != 'I': return

        popup = EditSynthDialog(synth_name = self.getTrack().getSynthName() if not drum else drumkit[self.getPattern().getDrumIndex()], is_drum = drum)
        popup.bind(on_dismiss = self.handlePopupDismiss)
        popup.open()

    def purgeEmptyPatterns(self):
        actually_used_patterns = [m.pattern for t in self.tracks for m in t.modules]
        for p in self.patterns[:]:
            if p.isEmpty() and p not in actually_used_patterns:
                print("PURGE EMPTY PATTERN:", p.name)
                self.patterns.remove(p)

    def purgeUnusedPatterns(self):
        actually_used_patterns = [m.pattern for t in self.tracks for m in t.modules]
        for p in self.patterns[:]:
            if p not in actually_used_patterns:
                print("PURGE UNUSED PATTERN:", p.name)
                self.patterns.remove(p)

############### UGLY KIVY EXPORT FUNCTIONS #####################

    def loadCSV_prompt(self, no_prompt = False):
        if no_prompt:
            self.loadCSV()
        else:
            popup = InputPrompt(self, title = 'WHICH TRACK IS IT, WHICH YOU DESIRE?', title_font = self.font_name, default_text = self.getInfo('title'))
            popup.bind(on_dismiss = self.loadCSV_handleprompt)
            popup.open()
    def loadCSV_handleprompt(self, *args):
        self._keyboard_request()
        self.setInfo('title', args[0].text.replace('.may',''))
        self.loadCSV()
        self.update()

    def saveCSV_prompt(self, no_prompt = False):
        if no_prompt:
            self.saveCSV()
        else:
            popup = InputPrompt(self, title = 'SAVE ASS', title_font = self.font_name, default_text = self.getInfo('title'))
            popup.bind(on_dismiss = self.saveCSV_handleprompt)
            popup.open()
    def saveCSV_handleprompt(self, *args):
        self._keyboard_request()
        self.setInfo('title', args[0].text.replace('.may',''))
        self.saveCSV()
        self.update()

################## ACTUAL EXPORT FUNCTIONS ###################

    def loadCSV(self, dt = 0):
        filename = self.getInfo('title') + '.may'
                
        if not os.path.isfile(filename):
            print(filename,'not around, start new track of that name')
            self.clearSong(no_renaming = True)
            return
                    
        self.loadSynths(update = False)
        print("... synths were reloaded. now read", filename)

        with open(filename) as in_csv:
            in_read = csv.reader(in_csv, delimiter='|')
            
            for r in in_read:
                self.tracks = []
                self.patterns = []
                self.setInfo('title', r[0])
                self.tryToSetBPM(r[1])
                B_offset = float(r[2])
                B_stop = float(r[3])

                self.setInfo('B_offset', B_offset)
                if B_offset > 0:
                    self.theTrkWidget.updateMarker('OFFSET', B_offset)
                B_stop = B_stop if B_stop > 0 else inf
                self.setInfo('B_stop', B_stop)
                if B_stop < inf:
                    self.theTrkWidget.updateMarker('STOP', B_stop)
                
                c = 5 # adjust this if you add some stored value beforehand
                ### read tracks -- with modules assigned to dummy patterns
                for _ in range(int(r[c-1])):
                    track = Track(synths, name = r[c], synth = synths.index(r[c+1]) if r[c+1] in synths else -1)
                    track.setParameters(norm = float(r[c+2].replace('m','')), mute = ('m' in r[c+2]))

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
                    
                    if self.MODE_debug: print(c, "READ PATTERN ", r[c+1], r[c+2], r[c+3], r[c+4])

                    c += 4
                    for _ in range(int(r[c])):
                        if self.MODE_debug:
                            try:
                                print(c, "    READ NOTE ", r[c+1], r[c+2], r[c+3], r[c+4], r[c+5], r[c+6], r[c+7])
                            except:
                                print(c, " ERROR WITH REST", r[c+1:])

                        pattern.notes.append(Note(\
                            note_on    = float(r[c+1]),\
                            note_len   = float(r[c+2]),\
                            note_pitch = int(float(r[c+3])),\
                            note_pan   = int(float(r[c+4])),\
                            note_vel   = int(float(r[c+5])),\
                            note_slide = float(r[c+6]),\
                            note_aux   = float(r[c+7])))
                        c += 7
                        
                    #if pattern.name not in [p.name for p in self.patterns]: # filter for duplicates -- TODO is this a good idea?
                    self.patterns.append(pattern)

                ### reassign modules to patterns
                for t in self.tracks:
                    for m in t.modules:
                        for p in self.patterns:
                            if m.pattern.name == p.name:
                                m.setPattern(p)

                ### further information ###
                c += 1
                self.track_solo = None if r[c] == '-1' else int(float(r[c]))
                c += 1
                self.setInfo('loop', r[c] if r[c] in loop_types else loop_types[0])
                c += 1
                self.lastImportPatternFilename = r[c] if os.path.isfile(r[c]) else ''
                c += 1
                self.setInfo('stereo_delay', float(r[c]))
                                

    def saveCSV(self):
        filename = self.getInfo('title') + '.may'
        
        self.purgeEmptyPatterns()

        out_str = '|'.join([self.getInfo('title'), str(self.getInfo('BPM')), str(self.getInfo('B_offset')), str(self.getInfo('B_stop')), str(len(self.tracks))]) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.getSynthFullName()) + '|' + str(t.getNorm()) + t.mute * 'm' + '|' + str(len(t.modules)) + '|'
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + p.synth_type + '|' + str(p.length) + '|' + str(len(p.notes))
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) \
                        +  '|' + str(n.note_pan) + '|' + str(n.note_vel) + '|' + str(n.note_slide) + '|' + str(n.note_aux)
                
        out_str += '|' + (str(int(self.track_solo)) if self.track_solo is not None else '-1') \
                 + '|' + self.getInfo('loop') \
                 + '|' + self.lastImportPatternFilename \
                 + '|' + str(self.getInfo('stereo_delay'))

        # write to file
        out_csv = open(filename, "w")
        out_csv.write(out_str)
        out_csv.close()
        print(filename, "written.")
        
        out_last = open('.last', "w")
        out_last.write(self.getInfo('title'))
        out_last.close()

    def instantCompileGLSL(self, delta):
        self.buildGLSL(compileGL = True, renderWAV = True)

    def buildGLSL(self, compileGL = False, renderWAV = False, onlyModule = False):
        filename = self.getInfo('title') + '.glsl'

        if onlyModule:
            test_track = deepcopy(self.tracks[self.current_track])
            test_module = deepcopy(self.getModule())
            test_module.move(0)
            test_track.modules = [test_module]
            tracks = [test_track]
            patterns = [test_module.pattern]
            actually_used_patterns = patterns
            loop_mode = 'seamless'
            offset = 0
            max_mod_off = test_module.getModuleOff()

            # might need to shift
            module_shift = self.getModule().mod_on
            for part in self.getInfo('BPM').split():
                bpm_point = float(part.split(':')[0])
                if bpm_point <= module_shift:
                    bpm_list = ['0:' + part.split(':')[1]]
                else:
                    bpm_list.append(str(bpm_point - module_shift) + ':' + part.split(':')[1])
                print(part, module_shift, bpm_list)

            if self.MODE_debug:
                print(test_track)
                print(tracks)
                print(patterns)

        else:
            tracks = [t for t in self.tracks if t.modules and not t.mute] if self.track_solo is None else [self.tracks[self.track_solo]]
            actually_used_patterns = [m.pattern for t in tracks for m in t.modules]
            patterns = [p for p in self.patterns if p in actually_used_patterns]
            loop_mode = self.getInfo('loop')
            offset = self.getInfo('B_offset')
            max_mod_off = min(max(t.getLastModuleOff() for t in tracks), self.getInfo('B_stop'))
            bpm_list = self.getInfo('BPM').split()

        if self.MODE_headless:
            loop_mode = 'full'

        track_sep = [0] + list(accumulate([len(t.modules) for t in tracks]))
        pattern_sep = [0] + list(accumulate([len(p.notes) for p in patterns]))

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
        actually_used_synths = set(t.getSynthName() for t in tracks if not t.getSynthType() == '_')
        actually_used_drums = set(n.note_pitch for p in patterns if p.synth_type == 'D' for n in p.notes)
        
        if self.MODE_debug: print("ACTUALLY USED:", actually_used_synths, actually_used_drums)

        self.synatized_code_syn, self.synatized_code_drum, paramcode, filtercode, self.last_synatized_forms = \
            synatize_build(self.synatize_form_list, self.synatize_main_list, self.synatize_param_list, actually_used_synths, actually_used_drums)

        if self.MODE_headless:
            print("ACTUALLY USED SYNTHS:", actually_used_synths)
            names_of_actually_used_drums = [drumkit[d] for d in actually_used_drums] 
            print("ACTUALLY USED DRUMS:", names_of_actually_used_drums)
            if len(actually_used_drums) == 1:
                self.file_extra_information += names_of_actually_used_drums[0] + '_'

	# TODO: would be really nice: option to not re-shuffle the last throw of randoms, but export these to WAV on choice... TODOTODOTODOTODO!
	# TODO LATER: great plans -- live looping ability (how bout midi input?)
        if self.stored_randoms:
            timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')[2:]
            countID = self.file_extra_information + (str(self.getWAVFileCount()) if renderWAV else '(unsaved)')
            with open(self.getInfo('title') + '.rnd', 'a') as of:
                of.write(timestamp + '\t' + countID + '\t' \
                                   + '\t'.join((rnd['id'] + '=' + str(rnd['value'])) for rnd in self.stored_randoms if rnd['store']) + '\n')

        # get release and predraw times
        syn_rel = []
        syn_pre = []
        drum_rel = []
        max_rel = 0
        max_drum_rel = 0
        if self.MODE_debug: print(self.synatize_main_list)
        for m in self.synatize_main_list:
            rel = float(m['release']) if 'release' in m else 0
            pre = float(m['predraw']) if 'predraw' in m else 0
            if m['type'] == 'main':
                syn_rel.append(rel)
                syn_pre.append(pre)
                if m['id'] in actually_used_synths:
                    max_rel = max(max_rel, rel)
            elif m['type'] == 'maindrum':
                drum_rel.append(rel)
                max_drum_rel = max(max_drum_rel, rel)

        syn_rel.append(max_drum_rel)
        syn_pre.append(0)

        nD = str(len(drum_rel)) # number of drums - not required right now, maybe we need to add something later
        drum_index = str(synths.index('D_Drums')+1)

        # get slide times
        syn_slide = []
        for m in self.synatize_main_list:
            if m['type'] == 'main':
                syn_slide.append((float(m['slidetime']) if 'slidetime' in m else 0))
        syn_slide.append(0) # because of drums

        defcode  = '#define NTRK ' + nT + '\n'
        defcode += '#define NMOD ' + nM + '\n'
        defcode += '#define NPTN ' + nP + '\n'
        defcode += '#define NNOT ' + nN + '\n'
        defcode += '#define NDRM ' + nD + '\n'

        # construct arrays for beat / time correspondence
        pos_B = [B for B in (float(part.split(':')[0]) for part in bpm_list) if B < max_mod_off] + [max_mod_off]
        pos_t = [self.getTimeOfBeat(B, bpm_list) for B in pos_B]
        pos_BPS = []
        pos_SPB = []
        for b in range(len(pos_B)-1):
            pos_BPS.append(round((pos_B[b+1] - pos_B[b]) / (pos_t[b+1] - pos_t[b]), 4))
            pos_SPB.append(round(1./pos_BPS[-1], 4))

        ntime = str(len(pos_B))
        ntime_1 = str(len(pos_B)-1)

        beatheader = '#define NTIME ' + ntime + '\n'
        beatheader += 'const float pos_B[' + ntime + '] = float[' + ntime + '](' + ','.join(map(GLfloat, pos_B)) + ');\n'
        beatheader += 'const float pos_t[' + ntime + '] = float[' + ntime + '](' + ','.join(map(GLfloat, pos_t)) + ');\n'
        beatheader += 'const float pos_BPS[' + ntime_1 + '] = float[' + ntime_1 + '](' + ','.join(map(GLfloat, pos_BPS)) + ');\n'
        beatheader += 'const float pos_SPB[' + ntime_1 + '] = float[' + ntime_1 + '](' + ','.join(map(GLfloat, pos_SPB)) + ');'

        self.song_length = self.getTimeOfBeat(max_mod_off, bpm_list)
        if loop_mode == 'full':
            self.song_length = self.getTimeOfBeat(max_mod_off + max_rel, bpm_list)

        time_offset = self.getTimeOfBeat(offset, bpm_list)
        self.song_length -= time_offset

        loopcode = ('time = mod(time, ' + GLfloat(self.song_length) + ');\n' + 4*' ') if loop_mode != 'none' else ''
        
        if offset != 0: loopcode += 'time += ' + GLfloat(time_offset) + ';\n' + 4*' '

        print("START TEXTURE")
        
        fmt = '@e'
        tex = b''

        # TODO:make it more pythonesk with something like
        # tex += ''.join(pack(fmt, float(s)) for s in track_sep)
        # etc.

        for s in track_sep:
            tex += pack(fmt, float(s))
        for t in tracks:
            tex += pack(fmt, float(t.getSynthIndex()+1))
        for t in tracks:
            tex += pack(fmt, float(t.getNorm()))
        for t in tracks:
            tex += pack(fmt, float(syn_rel[t.getSynthIndex()]))
        for t in tracks:
            tex += pack(fmt, float(syn_pre[t.getSynthIndex()]))
        for t in tracks:
            tex += pack(fmt, float(syn_slide[t.getSynthIndex()]))
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.mod_on))
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.getModuleOff()))
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(patterns.index(m.pattern))) # this could use some purge-non-used-patterns beforehand...
        for t in tracks:
            for m in t.modules:
                tex += pack(fmt, float(m.transpose))
        for s in pattern_sep:
            tex += pack(fmt, float(s))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_on))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_off))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_pitch))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_pan * .01))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_vel * .01))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_slide))
        for p in patterns:
            for n in p.notes:
                tex += pack(fmt, float(n.note_aux))
        for d in drum_rel:
            tex += pack(fmt, float(d))
               
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

        glslcode = glslcode\
            .replace("//DEFCODE", defcode)\
            .replace("//SYNCODE", self.synatized_code_syn)\
            .replace("//DRUMSYNCODE", self.synatized_code_drum)\
            .replace("DRUM_INDEX", drum_index)\
            .replace("//PARAMCODE", paramcode)\
            .replace("//FILTERCODE",filtercode)\
            .replace("//LOOPCODE", loopcode)\
            .replace("//BEATHEADER", beatheader)\
            .replace("STEREO_DELAY", GLfloat(self.getInfo('stereo_delay')))

        glslcode = glslcode.replace('e+00','').replace('-0.)', ')').replace('+0.)', ')')
        glslcode = self.purgeExpendables(glslcode)

        with open("template.textureheader") as f:
            texheadcode = f.read()
            f.close()

        glslcode_frag = '#version 130\n' + glslcode.replace("//TEXTUREHEADER", texheadcode)

        with open("sfx.frag", "w") as out_file:
            out_file.write(glslcode_frag)
            
        print("GLSL CODE WRITTEN (sfx.frag) -- NR4-compatible fragment shader")

        # for "standalone" version
        tex_n = str(int(ceil(texlength/2)))
        texcode = 'const float sequence_texture[' + tex_n + '] = float[' + tex_n + '](' + ','.join(map(GLfloat, arrayf)) + ');\n'

        glslcode = glslcode.replace("//TEXCODE",texcode).replace('//TEXTUREHEADER', 'float rfloat(int off){return sequence_texture[off];}\n')

        with open(filename, "w") as out_file:
            out_file.write(glslcode)

        print("GLSL CODE WRITTEN (" + filename + ") - QM-compatible standalone fragment shader")

        pyperclip.copy(glslcode)
        
        if compileGL or renderWAV:
            self.compileShader(glslcode, renderWAV)

    def purgeExpendables(self, code):
        chars_before = len(code)
        purged_code = ''

        while True:
            func_list = {}
            for i,l in enumerate(code.splitlines()):
                func_head = re.findall('(?<=float )\w*(?=[ ]*\(.*\))', l)
                if func_head:
                    func_list.update({func_head[0]:i})

            print(func_list)

            expendable = []
            self.printIfDebug("The following functions will be purged")
            for f in func_list.keys():
                #print(f, code.count(f), len(re.findall(f + '[ \n]*\(', code)))
                if len(re.findall(f + '[ \n]*\(', code)) == 1:
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

            for e in expendable: code = code.replace(e + '\n', '')
            
            if code == purged_code:
                break
            else:
                purged_code = code
                self.printIfDebug('try to purge next iteration')

        purged_code = re.sub('\n[\n]*\n', '\n\n', purged_code)

        chars_after = len(purged_code)
        print('// total purge of', chars_before-chars_after, 'chars.')
        
        return purged_code
    
###################### HANDLE BUTTONS #######################

# HAHA. no. we don't handle buttons.

#############################################################

    def pressTitle(self):     pass
    def pressTrkInfo(self):   pass
    def pressPtnTitle(self):  pass
    def pressPtnInfo(self):   pass
    def pressLoadCSV(self):   self.loadCSV()
    def pressSaveCSV(self):   self.saveCSV()
    def pressBuildCode(self): self.buildGLSL()

###################### DEBUG FUNCTIONS ######################

    def setupTest(self):
        self.addTrack("Bassline", synth = 0)
        self.addPattern("Sündig",2)
        self.tracks[0].addModule(self.patterns[0])
        self.getPattern().addNote(Note(0.00,0.50,24))
        for i in range(8):
            self.addTrack(name = 'Track ' + str(i+2))
        
    def toggleDebugMode(self):
        self.MODE_debug = not self.MODE_debug
        print('DEBUG MODE IS', 'ON' if self.MODE_debug else 'OFF')
        
    def printIfDebug(self, *messages):
        if self.MODE_debug:
            print(*messages)
        
    def printDebug(self, verbose = True):
        print('DEBUG -- TRACKS:')
        if verbose:  
            for t in self.tracks:
                print(t.name, len(t.modules), t.getSynthFullName(), t.getSynthIndex(), t.getSynthType())
                for m in t.modules:
                    print(' '*4, m.pattern.name, '@', m.mod_on)
                
        print('DEBUG -- current track', self.current_track, '/', self.getTrack().name, '/', self.getTrackSynthType())
        print('DEBUG -- same/none type patterns:', [p.name for p in self.getSameTypePatterns()])

        print('DEBUG -- PATTERNS:')
        if verbose:
            for p in self.patterns:
                print(p.name, len(p.notes), p.length)
                for n in p.notes:
                    print(' '*4, 'ON', n.note_on, 'LEN', n.note_len, 'PCH', n.note_pitch, 'VEL', n.note_vel)
            
        print('DEBUG -- current pattern', self.getPatternIndex(), '/', self.getPatternName())

        print('DEBUG -- undo:', len(self.undo_stack), '/', self.undo_max_steps, '/', self.undo_pos, '/', self.MODE_undo)              

################### NOW THE MIGHTY SHIT ###################

    def importPattern(self):
        popup = ImportPatternDialog(filename = self.lastImportPatternFilename)
        popup.bind(on_dismiss = self.handleImportPattern)
        popup.open()
    def handleImportPattern(self, *args):
        if args[0].return_pattern:
            print("Imported Pattern:", args[0].return_pattern.name)
            self.replacePatternByNameIfPossible(args[0].return_pattern)
            self.lastImportPatternFilename = args[0].XML_filename
            print("... imported from", self.lastImportPatternFilename)
        self._keyboard_request()
        self.update()

    def exportPattern(self):
        #TODO - export to XML, remember LMMS_lengthscale!
        pass

    def openSynthDialog(self):
        if self.isDrumTrack(): return
        self.loadSynths()
        popup = SelectSynthDialog(synths = synths, current_synth = self.getTrack().getSynthIndex())
        popup.bind(on_dismiss = self.handleSynthDialog)
        popup.open()
    def handleSynthDialog(self, *args):
        print("Switch Synth To:", args[0].selected_synth)
        self.getTrack().switchSynth(0, switch_to = args[0].selected_synth)
        self._keyboard_request()
        self.update()

    def switchToRandomSynth(self):
        self.getTrack().switchSynth(0, switch_to = randint(0, len(synths) - 4)) # Assumption: last three are drums / gfx / none, and randint() includes endpoints.
        self.update()
    
    def editCurve(self):
        popup = CurvePrompt(self, title = 'EDIT THE CURVE IF U DARE', title_font = self.font_name)
        popup.bind(on_dismiss = self.handleEditCurve)
        popup.open()
        
    def handleEditCurve(self, *args):
        self.handlePopupDismiss()

    def handlePopupDismiss(self, *args):
        self._keyboard_request()
        self.update()        

    def compileShader(self, shader, renderWAV):
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
 
        if not self.MODE_headless:
            pygame.mixer.pre_init(frequency=int(44100), size=-16, channels=2, buffer=4096)
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.stop()
            pygame.mixer.Sound(buffer=self.music).play()
        
        endtime = datetime.datetime.now()
        el = endtime - starttime

        print("Execution time", str(el.total_seconds()) + 's')

        if renderWAV:
            # determine number of samples for one songlength
            sound_framerate = 44100
            sound_channels = 2
            sound_samplewidth = 2
            total_samples = int(self.song_length * sound_framerate * sound_channels * sound_samplewidth + 1)

            sfile = wave.open(self.getWAVFileName(self.file_extra_information + self.getWAVFileCount()),'w')
            sfile.setframerate(sound_framerate)
            sfile.setnchannels(sound_channels)
            sfile.setsampwidth(sound_samplewidth)
            sfile.writeframesraw(self.music[:total_samples])
            sfile.close()

        if self.MODE_headless:
            App.get_running_app().stop()

        self.update()

class InputPrompt(ModalView):
    
    text = ''
    validated = False
    extra_parameters = {}

    def __init__(self, parent, **kwargs):
        title = kwargs.pop('title')
        title_font = kwargs.pop('title_font')
        default_text = kwargs.pop('default_text')
        self.extra_parameters = kwargs.pop('extra_parameters') if 'extra_parameters' in kwargs else {}
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
        self.validated = True
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
    