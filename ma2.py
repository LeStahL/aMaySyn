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
from math import sin, exp, pi, floor
from random import random
from datetime import *
from copy import copy, deepcopy
from shutil import move, copyfile
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

class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)
    somePopup = ObjectProperty(None)

    info = {'title': 'piover2', 'BPM': 80., 'B_offset': 0., 'loop_seamless': False}

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

    lastCommand = ''
    lastImportPatternFilename = ''

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
        elif action == 'SONG CHANGE PARAMETERS':        self.changeSongParameters()
        elif action == 'SONG CHANGE LOOPING OPTION':    self.changeSongLoopingOption()
        elif action == 'SYNTH RELOAD':                  self.loadSynths()
        elif action == 'SYNTH RELOAD NEW RANDOMS':      self.loadSynths(reshuffle_randoms = True) 
        elif action == 'CURVE EDIT':                    self.editCurve()
        elif action == 'MUTE':                          self.muteSound()
        elif action == 'SHADER PLAY':                   self.buildGLSL(compileGL = True)
        elif action == 'SHADER RENDER':                 self.buildGLSL(compileGL = True, renderWAV = True)
        elif action == 'SONG CLEAR':                    self.clearSong()
        elif action == 'SONG LOAD':                     self.loadCSV_prompt()
        elif action == 'SONG SAVE':                     self.saveCSV_prompt()
        elif action == 'SHADER CREATE':                 self.buildGLSL()
        elif action == 'UNDO':                          self.stepUndoStack(-1)
        elif action == 'REDO':                          self.stepUndoStack(+1)
        elif action == 'SYNTH SELECT NEXT':             self.getTrack().switchSynth(-1, debug = self.MODE_debug)
        elif action == 'SYNTH SELECT LAST':             self.getTrack().switchSynth(+1, debug = self.MODE_debug)
        elif action == 'PATTERN SELECT NEXT':           self.getTrack().switchModulePattern(self.getPattern(+1))
        elif action == 'PATTERN SELECT LAST':           self.getTrack().switchModulePattern(self.getPattern(-1))
        elif action == 'DIALOG PATTERN IMPORT':         self.importPattern()
#        elif action == 'DIALOG PATTERN EXPORT':         self.exportPattern()
        elif action == 'SYNTH FILE RESET DEFAULT':      self.resetSynthsToDefault()
        elif action == 'TRACK CHANGE PARAMETERS':       self.changeTrackParameters()
        elif action == 'TRACK MUTE':                    self.getTrack().setParameters(mute = not self.getTrack().mute)
        elif action == 'TRACK SOLO':                    self.setTrackSolo()
        elif action == 'ENTER COMMAND':                 self.promptCommand()

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
        self.btnTitle.text = 'TITLE: ' + self.getInfo('title')
        self.btnPtnTitle.text = 'PTN: ' + self.getPatternName() + ' (' + str(self.getSameTypePatternIndex()+1) + '/' + str(len(self.getSameTypePatterns())) + ') ' + pattern_types[self.getPatternSynthType()]
        self.btnPtnInfo.text = 'PTN LEN: ' + str(self.getPatternLen())

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
        state = {'info': deepcopy(self.info), 'tracks': deepcopy(self.tracks), 'patterns': deepcopy(self.patterns), 'current_track': self.current_track}

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

    def changeSongParameters(self):
        par_string = str(self.getInfo('BPM')) + ' ' + str(self.getInfo('B_offset'))
        popup = InputPrompt(self, title = 'ENTER BPM, <SPACE>, BEAT OFFSET', title_font = self.font_name, default_text = par_string)
        popup.bind(on_dismiss = self.handleChangeSongParameters)
        popup.open()
    def handleChangeSongParameters(self, *args):
        self._keyboard_request()
        pars = args[0].text.split()
        self.setInfo('BPM', float(pars[0]))
        try:    self.setInfo('B_offset', float(pars[1]))
        except: self.setInfo('B_offset', 0)
            
        self.theTrkWidget.updateMarker('OFFSET',self.getInfo('B_offset'))
        self.update()

    def changeSongLoopingOption(self):
        self.setInfo('loop_seamless', not self.getInfo('loop_seamless'))
        print('Seamless Looping is now', self.getInfo('loop_seamless'))

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

    def promptCommand(self):
        popup = InputPrompt(self, title = 'ENTER CMD (ask QM how they work)', title_font = self.font_name, default_text = self.lastCommand)
        popup.bind(on_dismiss = self.handleCommandPrompt)
        popup.open()
    def handleCommandPrompt(self, *args):
        self._keyboard_request()
        if args[0].validated:
            executed = self.executeCommand(args[0].text)
            if executed:
                self.lastCommand = args[0].text
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
        self.patterns = [Pattern()]
        self.tracks[0].addModule(self.patterns[0])

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
            
            #e.g. PAR VEL <B_min> <B_max> LIN <value_min> <value_max> <n_digits>
            if cmd[0] == 'par':
                parameter = cmd[1]
                B_min = float(cmd[2])
                B_max = float(cmd[3])
                shape = cmd[4]

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
                        note.setParameter(parameter, lin_value)
                    return True
                
                # RND: random values between [value_min, value_max] between [B_min, B_max] (with n_digits digits)
                elif shape in ['random', 'rnd']:
                    min_value = float(cmd[5])
                    max_value = float(cmd[6])
                    step_size = 1 if len(cmd) < 8 else float(cmd[7])
                    rnd_scale = floor((max_value - min_value)/step_size)
                    for note in affected_notes:
                        rnd_value = min_value + step_size * floor((rnd_scale + 1) * random.random())
                        note.setParameter(parameter, rnd_value)
                    return True

                elif shape == 'reset':
                    for note in affected_notes:
                        note.setParameter(parameter, None)
                    return True

                else:
                    print('COMMAND NOT SUPPORTED:\n', cmd)
                    return False
            else:
                print('COMMAND NOT SUPPORTED:\n', cmd)
                return False
        except Exception as exc:
            print('COMMAND ERRONEOUS (u stupid hobo):\n', cmd, '\n', type(exc))
            return False

############## ONLY THE MOST IMPORTANT FUNCTION! ############

    def reRandomizeColors(self):
        for p in self.patterns:
            p.randomizeColor()

################## AND THE OTHER ONE... #####################

    def loadSynths(self, update = True, reshuffle_randoms = False):
        
        global synths, drumkit
        old_drumkit = drumkit

        synfile = self.getInfo('title') + '.syn'
        if not os.path.exists(synfile): synfile = def_synfile

        self.synatize_form_list, self.synatize_main_list, drumkit, self.stored_randoms, self.synatize_param_list \
            = synatize(synfile, stored_randoms = self.stored_randoms, reshuffle_randoms = reshuffle_randoms)

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

    def synthClone(self, hard = False, drum = False):
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
            print("Current Track is drum track, go do Pattern (TAB) to clone single drums")
            return

        count = 0
        if drum:
            oldID = drumkit[self.getPattern().getDrumIndex()]
            while True:
                formID = oldID + str(count)
                if formID not in drumkit: break
                count += 1
        else:
            oldID = self.getTrack().getSynthName()
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

        self.loadSynths() # TODO: automatically select new synth?

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

    def purgeUnusedPatterns(self):
        actually_used_patterns = [m.pattern for t in self.tracks for m in t.modules]
        for p in self.patterns[:]:
            if p not in actually_used_patterns:
                print("PURGE EMPTY PATTERN:", p.name)
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
                self.setInfo('BPM', float(r[1]))
                self.setInfo('B_offset', float(r[2]))
                self.theTrkWidget.updateMarker('OFFSET', self.getInfo('B_offset'))
                
                c = 4
                ### read tracks -- with modules assigned to dummy patterns
                for _ in range(int(r[3])):
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
                                print(c, "    READ NOTE ", r[c+1], r[c+2], r[c+3], r[c+4], r[c+5], r[c+6])
                            except:
                                print(c, " ERROR WITH REST", r[c+1:])

                        pattern.notes.append(Note(\
                            note_on    = float(r[c+1]),\
                            note_len   = float(r[c+2]),\
                            note_pitch = int(float(r[c+3])),\
                            note_pan   = int(float(r[c+4])),\
                            note_vel   = int(float(r[c+5])),\
                            note_slide = float(r[c+6])))
                        c += 6
                        
                    #if pattern.name not in [p.name for p in self.patterns]: # filter for duplicates -- TODO is this a good idea?
                    self.patterns.append(pattern)

                ### reassign modules to patterns
                for t in self.tracks:
                    for m in t.modules:
                        for p in self.patterns:
                            if m.pattern.name == p.name:
                                m.setPattern(p)
                                

    def saveCSV(self):
        filename = self.getInfo('title') + '.may'
        
        self.purgeUnusedPatterns()

        out_str = '|'.join([self.getInfo('title'), str(self.getInfo('BPM')), str(self.getInfo('B_offset')), str(len(self.tracks))]) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.getSynthFullName()) + '|' + str(t.getNorm()) + t.mute * 'm' + '|' + str(len(t.modules)) + '|'
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + p.synth_type + '|' + str(p.length) + '|' + str(len(p.notes))
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) \
                        +  '|' + str(n.note_pan) + '|' + str(n.note_vel) + '|' + str(n.note_slide)
                
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

    def buildGLSL(self, compileGL = False, renderWAV = False):
        filename = self.getInfo('title') + '.glsl'

        tracks = [t for t in self.tracks if t.modules and not t.mute] if self.track_solo is None else [self.tracks[self.track_solo]]

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
        actually_used_synths = set(t.getSynthName() for t in self.tracks if not t.getSynthType() == '_')
        actually_used_drums = set(n.note_pitch for p in patterns if p.synth_type == 'D' for n in p.notes)
        
        if self.MODE_debug: print("ACTUALLY USED:", actually_used_synths, actually_used_drums)

        self.synatized_code_syn, self.synatized_code_drum, paramcode, filtercode, self.last_synatized_forms = \
            synatize_build(self.synatize_form_list, self.synatize_main_list, self.synatize_param_list, actually_used_synths, actually_used_drums)

	# TODO: would be really nice: option to not re-shuffle the last throw of randoms, but export these to WAV on choice... TODOTODOTODOTODO!
	# TODO LATER: great plans -- live looping ability (how bout midi input?)
        if self.stored_randoms:
            timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M')[2:]
            countID = str(self.getWAVFileCount()) if renderWAV else '(unsaved)'
            with open(self.getInfo('title') + '.rnd', 'a') as of:
                of.write(timestamp + '\t' + countID + '\t' \
                                   + '\t'.join((rnd['id'] + '=' + str(rnd['value'])) for rnd in self.stored_randoms if rnd['store']) + '\n')

        # get release times
        syn_rel = []
        drum_rel = []
        max_rel = 0
        max_drum_rel = 0
        if self.MODE_debug: print(self.synatize_main_list)
        for m in self.synatize_main_list:
            rel = float(m['release']) if 'release' in m else 0
            if m['type'] == 'main':
                syn_rel.append(rel)
                if m['id'] in actually_used_synths:
                    max_rel = max(max_rel, rel)
            elif m['type'] == 'maindrum':
                drum_rel.append(rel)
                max_drum_rel = max(max_drum_rel, rel)

        syn_rel.append(max_drum_rel)

        # number of drums - not required right now, maybe we need to add something later
        nD = str(len(drum_rel))

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
        
        if self.getInfo('loop_seamless'):
            seqcode  = 'float max_mod_off = ' + GLfloat(max_mod_off) + ';\n' + 4*' '
        else:
            seqcode  = 'float max_mod_off = ' + GLfloat(max_mod_off + max_rel) + ';\n' + 4*' '

        seqcode += 'int drum_index = ' + str(synths.index('D_Drums')+1) + ';\n' + 4*' '
        if self.getInfo('B_offset')!=0: seqcode += 'time += '+'{:.4f}'.format(self.getInfo('B_offset')/self.getInfo('BPM')*60)+';\n' + 4*' '

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
            .replace("//SEQCODE", seqcode)\
            .replace("//SYNCODE", self.synatized_code_syn)\
            .replace("//DRUMSYNCODE", self.synatized_code_drum)\
            .replace("//PARAMCODE", paramcode)\
            .replace("//FILTERCODE",filtercode)\
            .replace("//BPMCODE", "const float BPM = "+GLfloat(self.getInfo('BPM'))+";")

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
            song_length = max(t.getLastModuleOff() for t in self.tracks) / float(self.getInfo('BPM')) * 60
            sound_framerate = 44100
            sound_channels = 2
            sound_samplewidth = 2
            total_samples = int(song_length * sound_framerate * sound_channels * sound_samplewidth + 1)

            sfile = wave.open(self.getWAVFileName(self.getWAVFileCount()),'w')
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
    