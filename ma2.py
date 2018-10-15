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
from numpy import clip
from math import sin, exp, pi
import csv
import operator
import os

from ma2_track import *
from ma2_pattern import *
from ma2_widgets import *
from ma2_globals import *

Config.set('graphics', 'width', '1600')
Config.set('graphics', 'height', '1000')
#Config.set('graphics', 'fullscreen', 'auto')

class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)

    current_track = None
    current_module = None
    current_pattern = None
    current_note = None
    tracks = []
    patterns = []

    #synths = ['I_Bass', 'I_Synth2', 'I_synthIII', 'I_synthie', 'I_sympf', 'D_Drums', '__GFX', '__None']
    #drumkit = ['SC', 'KIK', 'KIK2', 'SNR', 'SNR2', 'HH', 'SHK', 'MTY1', 'MTY2', 'MTY3', 'MTY4'] 
    
    title = "is it π/2 yet?"
    
    btnTitle = ObjectProperty()
    
    #updateAll = True # ah, fuck it. always update everythig. TODO improve performance... somehow.
    
    #helpers...
    def getTrack(self):                 return self.tracks[self.current_track] if self.current_track is not None else None
    def getLastTrack(self):             return self.tracks[-1] if self.tracks else None
    def isDrumTrack(self):              return (synths[self.getTrack().current_synth][0] == 'D')
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
        self._keyboard_request()

        self.setupInit()
        Clock.schedule_once(self.update, 0)

    def _keyboard_request(self, *args):
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down = self._on_keyboard_down)        
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down = self._on_keyboard_down)
        self._keyboard = None
        
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        
        k = keycode[1]
        #print(k)
        
        if   k == 'escape':                     App.get_running_app().stop() 
        elif k == 'f8':                         self.printDebug()
        elif k == 'tab':                        self.switchActive()

        # THE MOST IMPORTANT KEY!
        elif k == 'f1':                         self.reRandomizeColors()

        elif k == 'f2':                         self.renameSong()

        elif k == 'f11':                        self.editCurve()

        if 'ctrl' in modifiers:
            if k == 'n':                        self.clearSong()
            elif k == 'l':                      self.loadCSV(self.title + '.ma2')
            elif k == 's':                      self.saveCSV(self.title + '.ma2')
            elif k == 'b':                      self.buildGLSL(self.title + '.glsl')

        # for precision work, press 'alt'
        inc_step = 1 if 'alt' not in modifiers else .25

        #vorerst: nur tastatursteuerung - nerdfaktor und so :)
        if(self.theTrkWidget.active):
            if all(x in modifiers for x in ['shift', 'ctrl']):
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
                pass
            
            else:
                if   k == 'left':               self.getTrack().switchModule(-1)
                elif k == 'right':              self.getTrack().switchModule(+1)
                elif k == 'end':                self.getTrack().switchModule(0, to = -1)
                elif k == 'home':               self.getTrack().switchModule(0, to = +0)
                elif k == 'up':                 self.switchTrack(-1)
                elif k == 'down':               self.switchTrack(+1)

                elif k == '+'\
                  or k == 'numpadadd':          self.getTrack().addModule(self.getTrack().getLastModuleOff(), Pattern()) 
                elif k == 'c':                  self.getTrack().addModule(self.getTrack().getLastModuleOff(), self.getPattern())
                elif k == '-'\
                  or k == 'numpadsubstract':    self.getTrack().delModule()

                elif k == 'pageup':             self.getTrack().switchModulePattern(self.getPattern(+1))
                elif k == 'pagedown':           self.getTrack().switchModulePattern(self.getPattern(-1))

                elif k == 'a':                  self.getTrack().switchSynth(-1)
                elif k == 's':                  self.getTrack().switchSynth(+1)
                
                elif k == 'f3':                 self.renameTrack()
                elif k == 'f12':                self.printPatterns()

        if(self.thePtnWidget.active) and self.getPattern():
            if all(x in modifiers for x in ['shift', 'ctrl']):
                if   k == 'left':               self.getPattern().moveNote(-1/32)
                elif k == 'right':              self.getPattern().moveNote(+1/32)

                elif k == 'pageup':             self.getPattern().stretchPattern(+inc_step, scale = True)
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
                  or k == 'numpadadd':          self.addPattern()
                elif k == '*'\
                  or k == 'numpadmul':          self.addPattern(clone_current = True)
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
                elif k == '-'\
                  or k == 'numpadsubstract':    self.getPattern().delNote()
                elif k == 'spacebar':           self.getPattern().setGap(inc = True)
                elif k == 'backspace':          self.getPattern().setGap(dec = True)
                
                
                elif k == 'pageup':             self.getTrack().switchModulePattern(self.getPattern(+1))
                elif k == 'pagedown':           self.getTrack().switchModulePattern(self.getPattern(-1))

                elif k == 'f12':                 self.getPattern().printNoteList()

        # MISSING:
        #       moveAllNotes()

        self.update()
        return True
        
    def update(self, dt = 0):
        #if self.theTrkWidget.active:
            self.theTrkWidget.drawTrackList(self.tracks, self.current_track) 
        #if self.thePtnWidget.active:
            self.thePtnWidget.drawPianoRoll(self.getPattern(), self.getModuleTranspose(), self.isDrumTrack())
            
            self.updateLabels()
            
    def updateLabels(self, dt = 0):
        self.btnTitle.text = 'TITLE: ' + self.title
        self.btnPtnTitle.text = 'PTN: ' + self.getPatternName()
        self.btnPtnInfo.text = 'PTN LEN: ' + str(self.getPatternLen())

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

    def renameTrack(self):
        popup = InputPrompt(self, title = 'RENAME TRACK', title_font = self.font_name, default_text = self.getTrack().name)
        popup.bind(on_dismiss = self.handleRenameTrack)
        popup.open()
    def handleRenameTrack(self, *args):
        self._keyboard_request()
        self.getTrack().name = args[0].text
        self.update()

    def addTrack(self, name, synth = None):
        self.tracks.append(Track(name = name, synth = synth))
        if len(self.tracks) == 1: self.current_track = 0
        self.update()

    def switchTrack(self, inc):
        self.current_track = (self.current_track + inc) % len(self.tracks)
        self.update()
        
    def addPattern(self, name = "", length = None, clone_current = False):
        if name == "":
            popup = InputPrompt(self, title = 'ENTER PATTERN NAME', title_font = self.font_name, default_text = 'som seriösly nju pettorn')
            popup.bind(on_dismiss = self.handlePatternName)
            popup.open()
        if not length:
            length = self.getPatternLen()
        self.patterns.append(Pattern(name = name, length = length))

        if clone_current:
            for n in self.getPattern().notes:
                self.patterns[-1].addNote(n);

    def handlePatternName(self, *args, **kwargs):
        self._keyboard_request()
        self.patterns[-1].name = args[0].text
        self.update()

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
        if not os.path.isfile(filename):
            print(filename,'not around, trying to load test.ma2')
            filename = 'test.ma2'
            if not os.path.isfile(filename):
                print('test.ma2 not around, doing nothing.')
                return
        
        with open(filename) as in_csv:
            in_read = csv.reader(in_csv, delimiter='|')
            
            for r in in_read:
                self.title = r[0]
                self.tracks = []
                self.patterns = []
                synths = []
                drumkit = []
                
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
                    pattern = Pattern(name = r[c+1], length = float(r[c+2]))
                    
                    c += 3
                    for _ in range(int(r[c])):
                        pattern.notes.append(Note(*(float(s) for s in r[c+1:c+4])))
                        c += 4
                        
                    #if pattern.name not in [p.name for p in self.patterns]: # filter for duplicates -- TODO is this a good idea?
                    self.patterns.append(pattern)

                ### reassign modules to patterns
                for t in self.tracks:
                    for m in t.modules:
                        for p in self.patterns:
                            if m.pattern.name == p.name: m.setPattern(p)

                c += 1
                print(int(r[c]))
                for _ in range(int(r[c])):
                    c += 1
                    synths.append(r[c])

                c += 1
                for _ in range(int(r[c])):
                    c += 1
                    drumkit.append(r[c])
                print(drumkit[-1])

    def saveCSV(self, filename):
        out_str = self.title + '|' + str(len(self.tracks)) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.getSynthIndex()) + '|' + str(len(t.modules)) + '|'
            
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                # TODO check: pattern names have to be unique! in str(self.patterns.index(m.pattern.name))
        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + str(p.length) + '|' + str(len(p.notes))
            
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) + '|' + str(n.note_vel)

        out_str += '|' + str(len(synths)) + '|' + '|'.join(synths)
        out_str += '|' + str(len(drumkit)) + '|' + '|'.join(drumkit)

        # write to file
        out_csv = open("test.ma2", "w")
        out_csv.write(out_str)
        out_csv.close()
        
    def buildGLSL(self, filename):
        # brilliant idea: first, treat modules like notes from the old sequencer --> e.g. play only note 24 + module.transpose (then put together -- which note in module?)

        # ignore empty tracks
        tracks = [t for t in self.tracks if t.modules]

        track_sep = [0] + list(accumulate([len(t.modules) for t in tracks]))
        pattern_sep = [0] + list(accumulate([len(p.notes) for p in self.patterns]))
        
        max_mod_off = max(t.getLastModuleOff() for t in tracks)

        float2str = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]

        nT  = str(len(tracks))
        nT1 = str(len(tracks) + 1)
        nM  = str(track_sep[-1])
        nP  = str(len(self.patterns))
        nP1 = str(len(self.patterns) + 1)
        nN  = str(pattern_sep[-1])

        out_str =  'int NO_trks = ' + nT + ';\n'
        out_str += 'int trk_sep[' + nT1 + '] = int[' + nT1 + '](' + ','.join(map(str, track_sep)) + ');\n'
        out_str += 'int trk_syn[' + nT + '] = int[' + nT + '](' + ','.join(str(t.getSynthIndex()+1) for t in tracks) + ');\n'
        out_str += 'float mod_on[' + nM + '] = float[' + nM + '](' + ','.join(float2str(m.mod_on) for t in tracks for m in t.modules) + ');\n'
        out_str += 'float mod_off[' + nM + '] = float[' + nM + '](' + ','.join(float2str(m.getModuleOff()) for t in tracks for m in t.modules) + ');\n'
        out_str += 'int mod_ptn[' + nM + '] = int[' + nM + '](' + ','.join(str(self.patterns.index(m.pattern)) for t in tracks for m in t.modules) + ');\n'
        out_str += 'float mod_transp[' + nM + '] = float[' + nM + '](' + ','.join(float2str(m.transpose) for t in tracks for m in t.modules) + ');\n'
        out_str += 'float inv_NO_tracks = ' + float2str(1./len(tracks)) + ';\n' # was this just for normalization? then call it global_volume or fix it via sigmoid
        out_str += 'float max_mod_off = ' + float2str(max_mod_off) + ';\n'
        out_str += 'int drum_index = ' + str(synths.index('D_Drums')+1) + ';\n'
        out_str += 'float drum_synths = ' + float2str(len(drumkit)) + ';\n'
        out_str += 'int NO_ptns = ' + nP + ';\n'
        out_str += 'int ptn_sep[' + nP1 + '] = int[' + nP1 + '](' + ','.join(map(str, pattern_sep)) + ');\n'
        out_str += 'float note_on[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_on) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'float note_off[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_off) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'float note_pitch[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_pitch) for p in self.patterns for n in p.notes) + ');\n'
        out_str += 'float note_vel[' + nN + '] = float[' + nN + '](' + ','.join(float2str(n.note_vel * .01) for p in self.patterns for n in p.notes) + ');\n'        

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

    def setupInit(self):

        self.addTrack("Bassline", synth = 0)

        self.addPattern("Sündig",2)

        self.tracks[0].addModule(0, self.patterns[0], 0, select = False)
                
        self.getPattern().addNote(Note(0.00,0.50,24), select = False)

        for i in range(8):
            self.addTrack(name = 'Track ' + str(i+2))

        self.current_pattern = 0
        self.current_module = 0
        self.update()
        
    def printDebug(self):
        for t in self.tracks:
            print(t.name, len(t.modules))
            for m in t.modules:
                print(m.mod_on, m.pattern.name)

    def printPatterns(self):
        for p in self.patterns:
            print(p.name, len(p.notes), p.length)

##################### NOW THE MIGHTY SHIT ##################

    def editCurve(self):
        popup = CurvePrompt(self, title = 'EDIT THE CURVE IF U DARE', title_font = self.font_name)
        popup.bind(on_dismiss = self.handleEditCurve)
        popup.open()
    def handleEditCurve(self, *args):
        self._keyboard_request()
        self.title = args[0].text
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

class CurveWidget(Widget):

    w = 1200
    h = 600
    b = 150
    o = 15
    
    res = 100
    
    c_x = 0
    c_y = 0
    
    fit_plot = []
    fit_dots = 5
    
    def __init__(self, parent, **kwargs):
        super(CurveWidget, self).__init__(**kwargs)
        self.c_x = parent.center_x
        self.c_y = parent.center_y
        self.update()
                               
    def on_touch_down(self, touch):
        self.fit_plot.append([touch.x, touch.y])
        
        self.update()

        if len(self.fit_plot) == self.fit_dots:
            print("FIT NOW!")
            
            print(self.fit_plot)
            self.fit_plot = []
            
    def update(self):
        self.canvas.clear()
        with self.canvas:
            
            Color(0,0,0)
            Rectangle(pos=(self.c_x - self.w/2, self.c_y - self.b), size=(self.w, self.h))
            
            Color(1,0,1,.5)
            Line(rectangle = (self.c_x - self.w/2, self.c_y - self.b, self.w, self.h), width = 4)

            plot = []
            for ix in range(self.res):
                plot.append([self.c_x + (self.w-2*self.o)*(ix / (self.res+1) - .5), self.c_y - (self.b+self.o) + (self.h-2*self.o)*self.curve(ix / self.res)])

            Color(.6,.8,.8)
            Line(points = plot, width = 3)
                
            for ic in range(len(self.fit_plot)):
                Color(.1,.3,.2)
                Ellipse(pos = (self.fit_plot[ic][0] - self.o/2, self.fit_plot[ic][1] - self.o/2), size=(self.o, self.o))

    def curve(self,x):
        a = .5
        b = 0
        c = 0.5
        d = -.2
        e = 10
        f = pi/2
        g = -.2
        h = .2
        i = .3
        return clip(a + b*x + c*x*x + d*sin(e*x + f) + g*exp(-h*x), 0, 1)
        
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
