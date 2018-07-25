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

import csv
import operator
import os

from ma2_track import *
from ma2_pattern import *

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

    synths = ['I_Bass', 'D_Kick']
    
    title = "is it π/2 yet?"
    
    btnTitle = ObjectProperty()
    
    #updateAll = True # ah, fuck it. always update everythig.
    
    #helpers...
    def getTrack(self):             return self.tracks[self.current_track] if self.current_track is not None else None
    def getLastTrack(self):         return self.tracks[-1] if self.tracks else None
    #def getTrackModules(self):     return self.getTrack().modules
    def getModule(self):            return self.getTrack().getModule() if self.getTrack() else None
    def getModuleTranspose(self):   return self.getModule().transpose if self.getModule() else 0
    #def getNextModule
    #def getPrevModule
    #def getFirstModule
    #def getLastModule
    #def getModuleLen(self):   return self.getTrack().getModuleLen()
    def getPattern(self):      return self.getTrack().getModulePattern() if self.getTrack() else None
    def getPatternLen(self):   return self.getPattern().length if self.getPattern() else None
    #def getPattern(self):     return self.patterns[self.current_pattern] if isinstance(self.current_pattern, int) and self.patterns else None
    #def getNextPattern(self): return self.patterns[(self.current_pattern + 1) % len(patterns)] if isinstance(self.current_pattern, int) and self.patterns else None
    #def getPrevPattern(self): return self.patterns[(self.current_pattern - 1) % len(patterns)] if isinstance(self.current_pattern, int) and self.patterns else None
    #def getLastPattern(self): return self.patterns[-1] if self.patterns else None
    #def getNote
    #def getNextNote
    #def getPrevNote
    #def getLastNote
    #def getSongLength

    def existsPattern(self, pattern): return pattern in self.patterns

    def __init__(self, **kwargs):
        super(Ma2Widget, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down = self._on_keyboard_down)

        if debug: self.setupDebug()
        Clock.schedule_once(self.update, 0)
        Clock.schedule_once(self.updateLabels, 0)
        
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

        if 'ctrl' in modifiers:
            if k == 'n':                        self.clearSong()
            elif k == 'l':                      self.loadCSV("test.ma2")
            elif k == 's':                      self.saveCSV("test.ma2")

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
                
                elif k == 'numpadadd':          self.getTrack().switchModulePattern(+1)
                elif k == 'numpadsubtract':     self.getTrack().switchModulePattern(-1)

            else:
                if   k == 'left':               self.getTrack().switchModule(-1)
                elif k == 'right':              self.getTrack().switchModule(+1)
                elif k == 'end':                self.getTrack().switchModule(0, to = -1)
                elif k == 'home':               self.getTrack().switchModule(0, to = +0)
                elif k == 'up':                 self.switchTrack(-1)
                elif k == 'down':               self.switchTrack(+1)
                
                elif k == 'numpadadd':          self.getTrack().addModule(self.getTrack().getLastModuleOff(), Pattern('nju', length=1), select = True) 
                elif k == 'c':                  self.getTrack().addModule(self.getTrack().getLastModuleOff(), self.getPattern(), select = True)
                elif k == 'numpadsubstract':    self.getTrack().delModule()

        if(self.thePtnWidget.active) and self.getPattern():
            if all(x in modifiers for x in ['shift', 'ctrl']):
                if   k == 'left':               self.getPattern().moveNote(-1/32)
                elif k == 'right':              self.getPattern().moveNote(+1/32)

            elif 'shift' in modifiers:
                if   k == 'left':               self.getPattern().stretchNote(-1/8)
                elif k == 'right':              self.getPattern().stretchNote(+1/8)
                elif k == 'up':                 self.getPattern().shiftAllNotes(+1)
                elif k == 'down':               self.getPattern().shiftAllNotes(-1)

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

        self.update()
        return True
        
    def update(self, dt = 0):
        #if self.theTrkWidget.active:
            self.theTrkWidget.drawTrackList(self.tracks, self.current_track) 
        #if self.thePtnWidget.active:
            self.thePtnWidget.drawPianoRoll(self.getPattern(), self.getModuleTranspose())

    def updateLabels(self, dt = 0):
        self.btnTitle.text = 'TITLE: ' + self.title

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
        print('hjehe', len(self.patterns), self.current_pattern)
        if self.patterns and self.current_pattern is not None:
            del self.patterns[self.current_pattern]
            
            print(*(p.name for p in self.patterns))

    def clearSong(self):
        del self.tracks[:]
        del self.patterns[:]
        self.tracks = [Track(name = 'nju Track', synth = 'I_None')]
        self.patterns = [Pattern(name = 'nju Pattern', length = 1)]
        self.tracks[0].addModule(0, self.patterns[0])
        
        self.current_track = 0
        self.current_module = None
        self.current_pattern = 0
        self.current_note = None
        self.title = 'new Song'

        self.update()

###################### DEBUG FUNCTIONS ######################

    def setupDebug(self):
        #DEBUG: test_list
        self.addTrack("Bassline", synth = "I_Bass")
        self.addTrack("Penetrator", synth = "Shit")
        self.addTrack("DerberScheißkick")
        self.addTrack("...")
        self.addTrack("N R 4")
        self.addTrack("      a n d")
        self.addTrack("             Q M")
        self.addTrack("")
        self.addTrack("      a r e")
        self.addTrack("       ...")
        self.addTrack("")
        self.addTrack("[T][E][A][M]")
        self.addTrack("       (2)(1)(0)")
        
        self.addPattern("bad performance", 7)
        self.addPattern("Lässig",2)
        self.current_pattern = 0
        
        self.tracks[1].addModule(5.5, self.patterns[0],-2)
        self.tracks[0].addModule(0, self.patterns[1], 0)
        self.tracks[0].addModule(2, self.patterns[1], 0)
        self.tracks[0].addModule(4, self.patterns[1], -3)
        self.tracks[0].addModule(6, self.patterns[1], -7)
        
        self.current_module = 0
        
        self.getPattern().addNote(0.00,0.50,24)
        self.getPattern().addNote(0.50,0.25,24)
        self.getPattern().addNote(0.75,0.25,24)
        self.getPattern().addNote(1.00,0.50,24)
        self.getPattern().addNote(1.50,0.50,31)
        
        #self.getPattern().printNoteList()
        
        self.update()
        
    def printDebug(self):
        for t in self.tracks:
            print(t.name, len(t.modules))
            for m in t.modules:
                print(m.mod_on, m.pattern.name)
    
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
                    track = Track(name = r[c], synth = (self.synths[int(r[c+1])] if r[c+1]!='-1' else 'I_None'))

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
            out_str += t.name + '|' + (str(self.synths.index(t.synth)) if t.synth in self.synths else '-1') + '|' + str(len(t.modules)) + '|'
            
            for m in t.modules:
                out_str += m.pattern.name + '|' + str(m.mod_on) + '|' + str(m.transpose) + '|' 
                # TODO check: pattern names have to be unique! in str(self.patterns.index(m.pattern.name))
        
        out_str += str(len(self.patterns))
        
        for p in self.patterns:
            out_str += '|' + p.name + '|' + str(p.length) + '|' + str(len(p.notes))
            
            for n in p.notes:
                out_str += '|' + str(n.noteon) + '|' + str(n.notelen) + '|' + str(n.notepitch) + '|' + str(n.notevel)

        # write to file
        out_csv = open("test.ma2", "w")
        out_csv.write(out_str)
        out_csv.close()
        
        print('out_str = ' + out_str)

###################### HANDLE BUTTONS #######################

#############################################################

    def pressTitle(self):     pass
    def pressTrkAdd(self):    pass
    def pressTrkDel(self):    pass
    def pressTrkInfo(self):   pass
    def pressModAdd(self):    pass
    def pressModDel(self):    pass
    def pressModPtn(self):    pass
    def pressModStart(self):  pass
    def pressModTransp(self): pass
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


class TrackWidget(Widget):
    active = BooleanProperty(True)

    def __init__(self, **kwargs):
        super(TrackWidget, self).__init__(**kwargs)

    def drawTrackList(self, tracklist = [], current_track = None):

        pad_l = 10
        pad_r = 20
        #pad_b = 10
        pad_t = 10
        row_h = 22
        gap_h = 4
        beat_w = 20
        
        font_size = 16
        char_w = 10
        chars_name = 16
        chars_synth = 10

        # TODO: fixed size for now (15 tracks, 64 modules).. extend when it becomes necessary

        grid_l = self.x + pad_l + 2 + char_w*(chars_name+chars_synth+2) + 8

        self.canvas.clear()
        with self.canvas:
            
            if self.active:
                Color(1.,0.,1,.5)
                Line(rectangle = [self.x + 3, self.y + 4, self.width - 7, self.height - 7], width = 1.5)
            
            for i,t in enumerate(tracklist[0:15]):
                #height: 375
                draw_x = self.x + pad_l
                draw_y = self.top - pad_t - (i+1)*row_h - i*gap_h;
                
                Color(*((.2,.2,.2) if i!=current_track else (.5,.2,.2)))
                Rectangle(pos = (draw_x, draw_y), size = (char_w*chars_name + 4,row_h))

                ### TRACK NAME ###
                draw_x += 2
                Color(1,1,1,1)
                label = CoreLabel(text = t.name[0:chars_name], font_size = font_size, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x, draw_y), texture = label.texture)

                ### SYNTH NAME ###
                draw_x += char_w*(chars_name+1) + 4
                Color(.8,.8,.8,1)
                label = CoreLabel(text = t.synth[2:2+chars_synth], font_size = font_size, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x, draw_y), texture = label.texture)
                                
                ### GRID ###
                draw_x = grid_l
                Color(*((.2,.2,.2) if i != current_track else (.5,.2,.2)))
                while draw_x + beat_w <= self.right - pad_r:
                    Rectangle(pos = (draw_x, draw_y), size = (beat_w-1,row_h))
                    draw_x += beat_w
                    
                ### MODULES ###
                for m in t.modules:
                    Color(*m.pattern.color,0.4)
                    Rectangle(pos=(grid_l + beat_w * m.mod_on, draw_y), size=(beat_w * m.pattern.length - 1,row_h))
                    
                    Color(*(0.5+0.5*c for c in m.pattern.color),1)
                    label = CoreLabel(text = m.pattern.name[0:3*int(m.pattern.length)], font_size = 10, font_name = self.font_name)
                    label.refresh()
                    Rectangle(size = label.texture.size, pos = (grid_l + beat_w * m.mod_on, draw_y-1), texture = label.texture)
                    
                    if m.transpose != 0:
                        label = CoreLabel(text = "%+d" % m.transpose, font_size = 10, font_name = self.font_name)
                        label.refresh()
                        Rectangle(size = label.texture.size, pos = (grid_l + beat_w * m.mod_on, draw_y + row_h/2 - 2), texture = label.texture)

                    if m == t.getModule() and i == current_track:
                        Color(1,.5,.5,.8)
                        Line(rectangle = (grid_l + beat_w * m.mod_on - 1 , draw_y - 1, beat_w * m.pattern.length, row_h + 2), width = 1.5)


            draw_x = grid_l
            draw_y = self.top - pad_t - (len(tracklist)+.5)*(row_h+gap_h) - 4

            beat_max = (self.right - pad_r - draw_x) // beat_w
            
            for i in range(beat_max+1):
                Color(.6,.8,.8)
                label = CoreLabel(text = str(i), font_size = 12, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x-label.texture.width/2, draw_y), texture = label.texture)
                
                draw_x += beat_w
            
    
class PatternWidget(Widget):
    active = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super(PatternWidget, self).__init__(**kwargs)

    claviature = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    def isKeyBlack(self, key): return '#' in self.claviature[key % 12]

    def drawPianoRoll(self, pattern = None, transpose = 0):
        
        pad_l = 10
        pad_r = 20
        pad_t = 5
        pad_b = 25
        key_h = 9
        key_w = 32
        font_size = 11
        bars = 4 * (0 if not pattern else pattern.length)
        bar_w = 48
        bar_max = 1
        #for now: no length > 16 bars! TODO

            #all the note_visible functions!
            #function to clearly calculate position of note TODO, draw current note, draw grid TODO but this time, respect pattern length!

        offset_v = 12
        offset_h = 0

        draw_y = self.y + pad_b
        key = offset_v

        self.canvas.clear()
        with self.canvas:
            
            if self.active:
                Color(1.,0.,1,.5)
                Line(rectangle = [self.x + 3, self.y + 4, self.width - 7, self.height - 7], width = 1.5)

            ### KEYBOARD ###
            while draw_y + key_h <= self.top - pad_t:
                draw_x = self.x + pad_l
                
                Color(*((1,1,1) if not self.isKeyBlack(key) else (.1,.1,.1)))
                Rectangle(pos = (draw_x, draw_y), size = (key_w,key_h + 0.5 * (not self.isKeyBlack(key))))

                Color(*((1,1,1) if self.isKeyBlack(key) else (.3,.3,.3)),1)
                label = CoreLabel(text = self.claviature[key % 12] + str(key//12), font_size = font_size, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-2.5), texture = label.texture)                
                Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-3), texture = label.texture)                

                draw_x += 2 + key_w
                Color(*((.1,.1,.1) if self.isKeyBlack(key) else (.1,.3,.2)))
                Rectangle(pos = (draw_x, draw_y), size = (self.right - pad_r - draw_x, key_h))
              
                draw_y += key_h+1
                key += 1

            draw_x = self.x + pad_l + key_w + 2
            draw_y = self.y + pad_b
            draw_h = (key_h+1) * (key - offset_v)

            ### GRID ###
            Color(.6,.8,.8)
            label = CoreLabel(text = "0.00", font_size = 12, font_name = self.font_name)
            label.refresh()
            Rectangle(size = label.texture.size, pos = (draw_x-label.texture.width/2, draw_y - label.texture.height), texture = label.texture)
            for b in range(bars):
                Color(*(0.05,0,0.05,0.8))
                Line(points = [draw_x, draw_y, draw_x, draw_y + draw_h], width = 1.5 if b % 4 == 0 else 1)
                Line(points = [draw_x + .25*bar_w, draw_y, draw_x + .25*bar_w, draw_y + draw_h], width = .3)
                Line(points = [draw_x + .50*bar_w, draw_y, draw_x + .50*bar_w, draw_y + draw_h], width = .3)
                Line(points = [draw_x + .75*bar_w, draw_y, draw_x + .75*bar_w, draw_y + draw_h], width = .3)

                draw_x += bar_w

                Color(.6,.8,.8)
                label = CoreLabel(text = "%.2f" % (.25*(b+1)), font_size = 12, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x-label.texture.width/2, draw_y - label.texture.height), texture = label.texture)

            Color(0,0,0)
            Line(points = [draw_x, draw_y, draw_x, draw_y + draw_h], width = 1.5)

            Color(0,0,0,.3)
            Rectangle(pos = (draw_x, draw_y), size = (self.right - pad_r - draw_x, draw_h))

            ### NOTES ###
            if pattern:
                for n in pattern.notes:
                    Color(*(0,.8,1),.6) # idea: current simultaneous notes in darker in the same pattern view --> makes editing WAY EASIER
                    draw_x = self.x + pad_l + key_w + 2 + 4 * bar_w * n.noteon
                    draw_y = self.y + pad_b + (key_h + 1) * (n.notepitch + transpose - offset_v)
                    Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.notelen - 2, key_h))

                    if n == pattern.getNote():
                        Color(1,1,1,.6)
                        Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.notelen - 2, key_h))
                
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
