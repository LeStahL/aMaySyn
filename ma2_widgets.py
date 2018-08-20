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

from ma2_track import *
from ma2_pattern import *
from ma2_globals import drumkit

class TrackWidget(Widget):
    active = BooleanProperty(True)

    def __init__(self, **kwargs):
        super(TrackWidget, self).__init__(**kwargs)

    def drawTrackList(self, tracklist = [], current_track = None):

        pad_l = 10
        pad_r = 20
        #pad_b = 10
        pad_t = 15
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
                label = CoreLabel(text = t.getSynthName()[2:2+chars_synth], font_size = font_size, font_name = self.font_name)
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
                    Color(*m.pattern.color, 0.4)
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

    def drawPianoRoll(self, pattern = None, transpose = 0, isDrum = False):
        
        pad_l = 10
        pad_r = 20
        pad_t = 5
        pad_b = 22
        key_h = 9 if not isDrum else 25
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

        if isDrum:
            offset_v = 0
            key = 0

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
                if not isDrum:
                    label = CoreLabel(text = self.claviature[key % 12] + str(key//12), font_size = font_size, font_name = self.font_name)
                    label.refresh()
                    Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-2.5), texture = label.texture)                
                    Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-3), texture = label.texture)                
                else:
                    label_len = len(drumkit[key])
                    label1 = CoreLabel(text = drumkit[key][0:4], font_size = font_size, font_name = self.font_name)
                    label1.refresh()
                    if label_len < 5:
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-1.5 + .5*label1.height), texture = label1.texture)                
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-2 + .5*label1.height), texture = label1.texture)
                    else:
                        label2 = CoreLabel(text = drumkit[key][4:8], font_size = font_size, font_name = self.font_name)
                        label2.refresh()
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-3.5 + label1.height), texture = label1.texture)                
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-4 + label1.height), texture = label1.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+2, draw_y-1.5), texture = label2.texture)                
                        Rectangle(size = label2.texture.size, pos = (draw_x+2, draw_y-2), texture = label2.texture)                

                draw_x += 2 + key_w
                Color(*((.1,.1,.1) if self.isKeyBlack(key) else (.1,.3,.2)))
                Rectangle(pos = (draw_x, draw_y), size = (self.right - pad_r - draw_x, key_h))
              
                draw_y += key_h+1
                key += 1
                
                if isDrum and key > len(drumkit) - 1: break

            draw_x = self.x + pad_l + key_w + 2
            draw_y = self.y + pad_b
            draw_h = (key_h+1) * (key - offset_v)

            ### GRID ###
            Color(.6,.8,.8)
            label = CoreLabel(text = "0.00", font_size = 12, font_name = self.font_name)
            label.refresh()
            Rectangle(size = label.texture.size, pos = (draw_x-label.texture.width/2, draw_y - label.texture.height), texture = label.texture)
            for b in range(int(bars)):
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
                    Color(*pattern.color,.55) # idea: current simultaneous notes in darker in the same pattern view --> makes editing WAY EASIER (TODO)
                    draw_x = self.x + pad_l + key_w + 2 + 4 * bar_w * n.note_on
                    draw_y = self.y + pad_b + (key_h + 1) * ((n.note_pitch + transpose - offset_v) if not isDrum else (n.note_pitch % len(drumkit)))
                    Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.note_len - 2, key_h))

                    if n == pattern.getNote():
                        Color(1,1,1,.6)
                        Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.note_len - 2, key_h))
