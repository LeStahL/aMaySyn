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
import os, sys
import pyperclip

from ma2_track import *
from ma2_pattern import *
from ma2_widgets import *
from ma2_synatize import synatize, synatize_build

Config.set('graphics', 'width', '1600')
Config.set('graphics', 'height', '1000')
#Config.set('graphics', 'fullscreen', 'auto')

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]

synths = ['D_Drums', '__GFX', '__None']
drumkit = ['SideChn']
BPM = 80.;
time_offset = 0.;

class Ma2Widget(Widget):
    theTrkWidget = ObjectProperty(None)
    thePtnWidget = ObjectProperty(None)

    current_track = None
    current_module = None
    current_pattern = None
    current_note = None
    tracks = []
    patterns = []

    synatize_form_list = []
    synatize_main_list = []
    
    title = 'piover2'
    
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

        elif k == 'f5':                         self.loadSynths(update = True)

        elif k == 'f11':                        self.editCurve()

        if 'ctrl' in modifiers:
            if k == 'n':                        self.clearSong()
            elif k == 'l':                      self.loadCSV()
            elif k == 's':                      self.saveCSV()
            elif k == 'b':                      self.buildGLSL()

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
                elif k == 'f4':                 self.changeTrackParameters()
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

    def changeTrackParameters(self):
        par_string = str(self.getTrack().getNorm()) + ' ' + str(self.getTrack().getMaxRelease())
        popup = InputPrompt(self, title = 'ENTER TRACK NORM FACTOR, <SPACE>, MAXIMUM RELEASE [BEATS]"', title_font = self.font_name, default_text = par_string)
        popup.bind(on_dismiss = self.handleChangeTrackParameters)
        popup.open()
    def handleChangeTrackParameters(self, *args):
        self._keyboard_request()
        pars = args[0].text.split()
        self.getTrack().setParameters(norm = pars[0], maxrelease = pars[1])
        self.update()

    def addTrack(self, name, synth = None):
        self.tracks.append(Track(synths, name = name, synth = synth))
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
        
    def setupInit(self):
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

        self.current_pattern = 0
        self.current_module = 0
        self.update()

############## ONLY THE MOST IMPORTANT FUNCTION! ############

    def reRandomizeColors(self):
        for p in self.patterns:
            p.randomizeColor()

################## AND THE OTHER ONE... #####################

    def loadSynths(self, update = False):
        
        global synths
        
        filename = self.title + '.syn'
        if not os.path.exists(filename): filename = 'test.syn'
        
        self.synatize_form_list, self.synatize_main_list, drumkit = synatize(filename)
        
        synths = ['I_' + m['ID'] for m in self.synatize_main_list if m['type']=='main']
        synths.extend(['D_Drums', '__GFX', '__None'])
        
        print(synths)
        
        drumkit.insert(0,'SideChn')
        #drumkit = ['SideChn', 'Kick', 'Kick2', 'Snar', 'HiHt', 'Shak', 'Odd Nois', 'Emty1', 'Emty2', 'Emty3', 'Emty4']
        self.thePtnWidget.updateDrumkit(drumkit)
        
        if update:
            for t in self.tracks: t.updateSynths(synths)
            self.update()

###################### EXPORT FUNCTIONS #####################

    def loadCSV(self, dt=0):
        filename = self.title + '.may'
        
        if not os.path.isfile(filename):
            print(filename,'not around, trying to load test.may')
            filename = 'test.may'
            if not os.path.isfile(filename):
                print('test.may not around, doing nothing.')
                return
        
        self.loadSynths()
        print("... synths were reloaded. now read", filename)

        with open(filename) as in_csv:
            in_read = csv.reader(in_csv, delimiter='|')
            
            for r in in_read:
                self.title = r[0]
                self.tracks = []
                self.patterns = []
                
                c = 2
                ### read tracks -- with modules assigned to dummy patterns
                for _ in range(int(r[1])):
                    track = Track(synths, name = r[c], synth = int(r[c+1]))
                    track.setParameters(norm = float(r[c+2]), maxrelease = float(r[c+3]))

                    c += 4
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

    def saveCSV(self):
        filename = self.title + '.may'
        
        out_str = self.title + '|' + str(len(self.tracks)) + '|'
        
        for t in self.tracks:
            out_str += t.name + '|' + str(t.getSynthIndex()) + '|' + str(t.getNorm()) + '|' + str(t.getMaxRelease()) + '|' + str(len(t.modules)) + '|'
            
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                # TODO check: pattern names have to be unique! in str(self.patterns.index(m.pattern.name))
        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + str(p.length) + '|' + str(len(p.notes))
            
            for n in p.notes:
                out_str += '|' + str(n.note_on) + '|' + str(n.note_len) + '|' + str(n.note_pitch) + '|' + str(n.note_vel)

        # write to file
        out_csv = open(filename, "w")
        out_csv.write(out_str)
        out_csv.close()
        
        out_tmp = open('.last', "w")
        out_tmp.write(self.title)
        out_tmp.close()
        
    def buildGLSL(self):
        filename = self.title + '.glsl'

        # ignore empty tracks
        tracks = [t for t in self.tracks if t.modules]

        track_sep = [0] + list(accumulate([len(t.modules) for t in tracks]))
        pattern_sep = [0] + list(accumulate([len(p.notes) for p in self.patterns]))
        
        max_mod_off = max(t.getLastModuleOff() for t in tracks)

        nT  = str(len(tracks))
        nT1 = str(len(tracks) + 1)
        nM  = str(track_sep[-1])
        nP  = str(len(self.patterns))
        nP1 = str(len(self.patterns) + 1)
        nN  = str(pattern_sep[-1])

        gf = open("framework.matzethemightyemperor")
        glslcode = gf.read()
        gf.close()

        self.loadSynths()
        syncode = synatize_build(self.synatize_form_list, self.synatize_main_list)

        seqcode =  'int NO_trks = ' + nT + ';\n' + 4*' '
        seqcode += 'int trk_sep[' + nT1 + '] = int[' + nT1 + '](' + ','.join(map(str, track_sep)) + ');\n' + 4*' '
        seqcode += 'int trk_syn[' + nT + '] = int[' + nT + '](' + ','.join(str(t.getSynthIndex()+1) for t in tracks) + ');\n' + 4*' '
        seqcode += 'float trk_norm[' + nT + '] = float[' + nT + '](' + ','.join(GLfloat(t.getNorm()) for t in tracks) + ');\n' + 4*' '
        seqcode += 'float trk_rel[' + nT + '] = float[' + nT + '](' + ','.join(GLfloat(t.getMaxRelease()) for t in tracks) + ');\n' + 4*' '
        seqcode += 'float mod_on[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.mod_on) for t in tracks for m in t.modules) + ');\n' + 4*' '
        seqcode += 'float mod_off[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.getModuleOff()) for t in tracks for m in t.modules) + ');\n' + 4*' '
        seqcode += 'int mod_ptn[' + nM + '] = int[' + nM + '](' + ','.join(str(self.patterns.index(m.pattern)) for t in tracks for m in t.modules) + ');\n' + 4*' '
        seqcode += 'float mod_transp[' + nM + '] = float[' + nM + '](' + ','.join(GLfloat(m.transpose) for t in tracks for m in t.modules) + ');\n' + 4*' '
        seqcode += 'float max_mod_off = ' + GLfloat(max_mod_off) + ';\n' + 4*' '
        seqcode += 'int drum_index = ' + str(synths.index('D_Drums')+1) + ';\n' + 4*' '
        seqcode += 'float drum_synths = ' + GLfloat(len(drumkit)) + ';\n' + 4*' '
        seqcode += 'int NO_ptns = ' + nP + ';\n' + 4*' '
        seqcode += 'int ptn_sep[' + nP1 + '] = int[' + nP1 + '](' + ','.join(map(str, pattern_sep)) + ');\n' + 4*' '
        seqcode += 'float note_on[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_on) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        seqcode += 'float note_off[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_off) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        seqcode += 'float note_pitch[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_pitch) for p in self.patterns for n in p.notes) + ');\n' + 4*' '
        seqcode += 'float note_vel[' + nN + '] = float[' + nN + '](' + ','.join(GLfloat(n.note_vel * .01) for p in self.patterns for n in p.notes) + ');\n' + 4*' '  
        seqcode += 'time += '+GLfloat(time_offset)+';\n' + 4*' '

        glslcode = glslcode.replace("//SEQCODE",seqcode).replace("//SYNCODE",syncode).replace("const float BPM = 80.;","const float BPM = "+GLfloat(BPM)+";")
        
        with open(filename, "w") as out_file:
            out_file.write(glslcode)
        
        pyperclip.copy(glslcode)
        
        print()
        print(seqcode)
    
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

# TODO custom button, more nerd-stylish..
