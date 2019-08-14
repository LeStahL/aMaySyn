import kivy
kivy.require('1.10.0') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.modalview import ModalView
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.text import Label as CoreLabel
from math import pi, sin, exp, ceil, sqrt
from random import randint

import xml.etree.ElementTree as ET
from ma2_selectableRV import *
from ma2_patternRV import *

import numpy as np
from scipy import optimize

from ma2_track import *
from ma2_pattern import *

mixcolor = lambda t1,t2: tuple((v1+v2)/2 for v1,v2 in zip(t1,t2))
strfloat = lambda f: str(int(f)) if f==int(f) else str(f)

LMMS_scalenotes = 192
LMMS_scalebars = 4

class TrackWidget(Widget):
    active = BooleanProperty(True)

    marker_list = []
    scale_h = 1
    scale_v = 1
    offset_h = 0
    offset_v = 0

    def __init__(self, **kwargs):
        super(TrackWidget, self).__init__(**kwargs)

    def drawTrackList(self, parent):

        tracklist = parent.tracks
        current_track = parent.current_track
        paramlist = parent.synatize_param_list
        current_param = parent.current_param

        pad_l = 10
        pad_r = 20
        pad_t = 9
        row_h = int(21 * self.scale_v)
        gap_h = 4
        beat_w = int(20 * self.scale_h)

        pad_b = 10
        paramview_h = 0 # 2 * row_h + 1 * gap_h
        trackview_h = self.height - paramview_h - pad_b

        font_size = 16
        char_w = 10
        chars_name = 13
        chars_synth = 13
        font_size_small = int(11 * min(self.scale_v, self.scale_h))

        max_visible_tracks = int((trackview_h - 2. * font_size) / (row_h + gap_h))
        number_visible_tracks = min(len(tracklist), max_visible_tracks)
        self.offset_v = min(self.offset_v, abs(len(tracklist) - max_visible_tracks))

        # TODO: fixed size for now (15 tracks, 64 modules).. extend when it becomes necessary

        grid_l = self.x + pad_l + 2 + char_w*(chars_name+chars_synth+2) + 8

        self.canvas.clear()
        with self.canvas:
            
            Color(*parent.mainBackgroundColor())
            Rectangle(pos = self.pos, size = self.size)

            if self.active:
                Color(1.,0.,1,.5)
                Line(rectangle = [self.x + 3, self.y + 4, self.width - 7, self.height - 7], width = 1.5)
            
            for i,t in enumerate(tracklist[self.offset_v:self.offset_v+number_visible_tracks]):
                index = i + self.offset_v
                draw_x = self.x + pad_l
                draw_y = self.top - pad_t - (i+1) * row_h - i * gap_h
                
                Color(*((.2,.2,.2) if index != current_track else (.5,.2,.2)))
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
                label = CoreLabel(text = t.getSynthName()[:chars_synth], font_size = font_size, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x, draw_y), texture = label.texture)
                                
                ### GRID ###
                draw_x = grid_l
                Color(*((.2,.2,.2) if index != current_track else (.5,.2,.2)), 1 - 0.5 * t.mute)
                max_visible_beats = 0
                while draw_x + beat_w <= self.right - pad_r:
                    Rectangle(pos = (draw_x, draw_y), size = (beat_w-1,row_h))
                    draw_x += beat_w
                    max_visible_beats += 1

                ### TRACK INFO ###
                Color(1,1,1,.7)
                volume_label = str(int(100 * t.par_norm)) + '%'
                if t.mute or (parent.track_solo is not None and parent.track_solo != i):
                    volume_label = "MUTE"
                elif parent.track_solo == i:
                    Color(1,.4,.4,1)
                    volume_label = "SOLO " + volume_label

                label = CoreLabel(text = volume_label, font_size = font_size, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (self.right - pad_r - label.width, draw_y), texture = label.texture)

                ### MODULES ###
                for m in t.modules:
                    mod_on = m.mod_on - self.offset_h
                    mod_len = m.pattern.length
                    if mod_on < 0:
                        mod_len += mod_on
                        mod_on = 0
                    if mod_len <= 0 or mod_on > max_visible_beats:
                        continue

                    Color(*m.pattern.color, 0.4)
                    Rectangle(pos=(grid_l + beat_w * mod_on, draw_y), size=(beat_w * mod_len - 1,row_h))
                    
                    Color(*(0.5+0.5*c for c in m.pattern.color),1)
                    label = CoreLabel(text = m.pattern.name[0:3*int(m.pattern.length)], font_size = font_size_small, font_name = self.font_name)
                    label.refresh()
                    Rectangle(size = label.texture.size, pos = (grid_l + beat_w * mod_on, draw_y-1), texture = label.texture)
                    
                    if m.transpose != 0:
                        label = CoreLabel(text = "%+d" % m.transpose, font_size = font_size_small, font_name = self.font_name)
                        label.refresh()
                        Rectangle(size = label.texture.size, pos = (grid_l + beat_w * mod_on, draw_y + row_h/2 - 2), texture = label.texture)

                    if m == t.getModule() and index == current_track:
                        Color(1,.5,.5,.8)
                        Line(rectangle = (grid_l + beat_w * mod_on - 1 , draw_y - 1, beat_w * mod_len, row_h + 2), width = 1.5)

            draw_x = grid_l
            draw_y = self.top - pad_t - (number_visible_tracks+.5)*(row_h+gap_h) - 4

            beat_max = (self.right - pad_r - draw_x) // beat_w
            
            # BEAT ENUMERATION
            for i in range(beat_max+1):
                Color(.6,.8,.8)
                label = CoreLabel(text = str(i + self.offset_h), font_size = 12, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x-label.width/2, draw_y+2), texture = label.texture)

                draw_x += beat_w
            
            # MARKERS
            for m in self.marker_list:
                marker_pos = m['pos'] - self.offset_h
                if marker_pos < 0 or marker_pos > max_visible_beats: continue
                    
                draw_x = grid_l + marker_pos * beat_w

                if m['style'] == 'BPM':
                    line_bottom = draw_y - 10
                    line_top = draw_y
                    Color(.3,.3,.7,.7)
                    m_text = m['label'][3:]
                else:
                    line_bottom = draw_y + 2
                    line_top = self.top - pad_t
                    Color(.7,0,.1,.7)
                    m_text = m['label']
                Line(points = [draw_x, line_bottom, draw_x, line_top], width=1.5)

                label = CoreLabel(text = m_text, font_size = font_size_small, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x - label.width/2, line_bottom - font_size_small - 6), texture = label.texture)
                Rectangle(size = label.texture.size, pos = (draw_x - label.width/2 - .5, line_bottom - font_size_small - 6), texture = label.texture)

#            ### PARAMETER VIEW ### -- damn, this makes little sense because I need so much information about the parameter segments themselves... --> next aMaySyn version!
#            Color(.5, .4, 0)
#            draw_x = self.x + pad_l
#            draw_y = self.top - self.height + pad_b            
#            Rectangle(pos = (draw_x, draw_y), size = (char_w*chars_name + 4,paramview_h))
#            draw_x += 2
#            Color(1,1,1,1)
#            label = CoreLabel(text = "PARAMETER", font_size = font_size, font_name = self.font_name)
#            label.refresh()
#            Rectangle(size = label.texture.size, pos = (draw_x, draw_y), texture = label.texture)
#            draw_x += char_w*(chars_name+1) + 4
#            Color(.8,.8,.8,1)
#            label = CoreLabel(text = paramlist[current_param]['id'], font_size = font_size, font_name = self.font_name)
#            label.refresh()
#            Rectangle(size = label.texture.size, pos = (draw_x, draw_y), texture = label.texture)
#                                
#            ### GRID ###
#            draw_x = grid_l
#            Color(.25,.2,.0)
#            while draw_x + beat_w <= self.right - pad_r:
#                Rectangle(pos = (draw_x, draw_y), size = (beat_w-1,row_h))
#                draw_x += beat_w


    def addMarker(self, label, position, style = ''):
        self.marker_list.append({'label': label, 'pos': position, 'style': style})
        
        markers_to_remove = [m for m in self.marker_list if m['pos']<0]
        for m in markers_to_remove:
            self.marker_list.remove(m)

    def removeMarkersContaining(self, label):
        markers_to_remove = [m for m in self.marker_list if label in m['label']]
        for m in markers_to_remove:
            self.marker_list.remove(m)

    def scroll(self, axis, inc):
        if axis == 'horizontal':
            self.offset_h = max(0, self.offset_h + inc)
        elif axis == 'vertical':
            self.offset_v = max(0, self.offset_v + inc)
        else:
            print("tried scrolling on some weird axis:", axis)

    def scaleByFactor(self, axis, factor):
        if axis == 'horizontal':
            self.scale_h = round(self.scale_h * factor, 2)
        elif axis == 'vertical':
            self.scale_v = round(self.scale_v * factor, 2)
        else:
            print("tried scaling by some weird axis:", axis)


class PatternWidget(Widget):
    active = BooleanProperty(False)

    drumkit = []
    scale_h = 1
    scale_v = 1
    offset_h = 0
    offset_v = 12
    scale_drum_h = 1
    scale_drum_v = 1
    offset_drum_h = 0
    offset_drum_v = 0
    # TODO: before automatic scrolling: prompt to enter offset_h, offset_v, scale_h, scale_v; AND also cut off everything not on screen
    
    def __init__(self, **kwargs):
        super(PatternWidget, self).__init__(**kwargs)

    claviature = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    def isKeyBlack(self, key): return '#' in self.claviature[key % 12]

    def drawPianoRoll(self, parent):

        pattern = parent.getPattern()
        transpose = 0 # don't display parent.getModuleTranspose() anymore
        isDrum = parent.isDrumTrack()

        def isKeyBlack(key): return self.isKeyBlack(key) if not isDrum else (key % 2 == 0)

        if isDrum:
            offset_v = self.offset_drum_v
            offset_h = self.offset_drum_h
            scale_v = self.scale_drum_v
            scale_h = self.scale_drum_h
            key = offset_v
            transpose = 0
        else:
            offset_v = self.offset_v
            offset_h = self.offset_h
            scale_v = self.scale_v
            scale_h = self.scale_h
            key = offset_v

        pad_l = 10
        pad_r = 20
        pad_t = 8
        pad_b = 22
        key_h = int(9 * scale_v * (1 if not isDrum else 3))
        key_w = int(32 * scale_h)
        font_size = int(11 * min(scale_h, scale_v))
        par_font_size = font_size * sqrt(scale_h)
        bars = 4 * (0 if not pattern else max(0, pattern.length - offset_h))
        bar_w = int(48 * scale_h)

        #all the note_visible functions!
        #function to clearly calculate position of note TODO, draw current note, draw grid TODO but this time, respect pattern length!

        draw_y = self.y + pad_b
        number_keys_visible = int((self.top - pad_t - self.y - pad_b)/(key_h+1))

        if isDrum:
            self.offset_drum_v = max(0, min(self.offset_drum_v, len(self.drumkit) - number_keys_visible))
            offset_v = self.offset_drum_v
            key = offset_v

        self.canvas.clear()
        with self.canvas:
            
            Color(*parent.mainBackgroundColor())
            Rectangle(pos = self.pos, size = self.size)
            
            if self.active:
                Color(1.,0.,1,.5)
                Line(rectangle = [self.x + 3, self.y + 4, self.width - 7, self.height - 4], width = 1.5)

            ### KEYBOARD ###
            while draw_y + key_h <= self.top - pad_t:
                draw_x = self.x + pad_l
                
                Color(*((1,1,1) if not isKeyBlack(key) else (.1,.1,.1)))
                Rectangle(pos = (draw_x, draw_y), size = (key_w,key_h + 0.5 * (not isKeyBlack(key))))

                if pattern and pattern.notes and key == (pattern.getNote().note_pitch + transpose) % (len(self.drumkit) if isDrum else 100):
                    Color(.7,1,.3,.6)
                    Rectangle(pos = (draw_x, draw_y), size = (key_w, key_h + 0.5 * (not isKeyBlack(key))))

                Color(*((1,1,1) if isKeyBlack(key) else (.3,.3,.3)),1)
                if not isDrum:
                    label = CoreLabel(text = self.claviature[key % 12] + str(key//12), font_size = font_size, font_name = self.font_name)
                    label.refresh()
                    Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-2.5), texture = label.texture)
                    Rectangle(size = label.texture.size, pos = (draw_x+2, draw_y-3), texture = label.texture)
                else:
                    label_len = len(self.drumkit[key])
                    if label_len < 5:
                        label1 = CoreLabel(text = self.drumkit[key][0:4], font_size = font_size, font_name = self.font_name)
                        label1.refresh()
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-1 + .5*label1.height), texture = label1.texture)
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-1.5 + .5*label1.height), texture = label1.texture)
                    elif label_len < 9:
                        label1 = CoreLabel(text = self.drumkit[key][0:4], font_size = font_size, font_name = self.font_name)
                        label1.refresh()
                        label2 = CoreLabel(text = self.drumkit[key][4:8], font_size = font_size, font_name = self.font_name)
                        label2.refresh()
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-2 + label1.height), texture = label1.texture)
                        Rectangle(size = label1.texture.size, pos = (draw_x+2, draw_y-2.5 + label1.height), texture = label1.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+2, draw_y), texture = label2.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+2, draw_y-.5), texture = label2.texture)
                    elif label_len < 11:
                        label1 = CoreLabel(text = self.drumkit[key][0:5], font_size = font_size-1, font_name = self.font_name)
                        label1.refresh()
                        label2 = CoreLabel(text = self.drumkit[key][5:10], font_size = font_size-1, font_name = self.font_name)
                        label2.refresh()
                        Rectangle(size = label1.texture.size, pos = (draw_x+1, draw_y-1.5 + label1.height), texture = label1.texture)
                        Rectangle(size = label1.texture.size, pos = (draw_x+1, draw_y-2 + label1.height), texture = label1.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+1, draw_y+.5), texture = label2.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+1, draw_y), texture = label2.texture)
                    else:
                        label1 = CoreLabel(text = self.drumkit[key][0:5], font_size = font_size-1, font_name = self.font_name)
                        label1.refresh()
                        label2 = CoreLabel(text = self.drumkit[key][5:10], font_size = font_size-1, font_name = self.font_name)
                        label2.refresh()
                        label3 = CoreLabel(text = self.drumkit[key][10:15], font_size = font_size-1, font_name = self.font_name)
                        label3.refresh()
                        Rectangle(size = label1.texture.size, pos = (draw_x+1, draw_y-11.5 + 2*label1.height), texture = label1.texture)
                        Rectangle(size = label1.texture.size, pos = (draw_x+1, draw_y-11 + 2*label1.height), texture = label1.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+1, draw_y-7 + label2.height), texture = label2.texture)
                        Rectangle(size = label2.texture.size, pos = (draw_x+1, draw_y-6.5 + label2.height), texture = label2.texture)
                        Rectangle(size = label3.texture.size, pos = (draw_x+1, draw_y-3), texture = label3.texture)
                        Rectangle(size = label3.texture.size, pos = (draw_x+1, draw_y-2.5), texture = label3.texture)

                draw_x += 2 + key_w
                Color(*((.1,.1,.1) if isKeyBlack(key) else (.1,.3,.2)))
                Rectangle(pos = (draw_x, draw_y), size = (self.right - pad_r - draw_x, key_h))
              
                draw_y += key_h+1
                key += 1
                
                if isDrum and key > len(self.drumkit) - 1: break

            draw_x = self.x + pad_l + key_w + 2
            draw_y = self.y + pad_b
            draw_h = (key_h+1) * (key - offset_v)

            ### GRID ###
            Color(.6,.8,.8)
            label = CoreLabel(text = "%.2f" % offset_h, font_size = 12, font_name = self.font_name)
            label.refresh()
            Rectangle(size = label.texture.size, pos = (draw_x-label.width/2, draw_y - label.height), texture = label.texture)
            for b in range(int(bars)):
                Color(0.05,0,0.05,0.8)
                Line(points = [draw_x, draw_y, draw_x, draw_y + draw_h], width = 1.5 if b % 4 == 0 else 1)
                Line(points = [draw_x + .25*bar_w, draw_y, draw_x + .25*bar_w, draw_y + draw_h], width = .3)
                Line(points = [draw_x + .50*bar_w, draw_y, draw_x + .50*bar_w, draw_y + draw_h], width = .3)
                Line(points = [draw_x + .75*bar_w, draw_y, draw_x + .75*bar_w, draw_y + draw_h], width = .3)

                draw_x += bar_w

                Color(.6,.8,.8)
                label = CoreLabel(text = "%.2f" % (.25*(b + 1) + offset_h), font_size = 12, font_name = self.font_name)
                label.refresh()
                Rectangle(size = label.texture.size, pos = (draw_x-label.width/2, draw_y - label.height), texture = label.texture)

            Color(0,0,0)
            Line(points = [draw_x, draw_y, draw_x, draw_y + draw_h], width = 1.5)

            Color(0,0,0,.3)
            Rectangle(pos = (draw_x, draw_y), size = (self.right - pad_r - draw_x, draw_h))

            ### NOTES ###
            if pattern:
                
                showVelocities = False
                for n in pattern.notes:
                    if n.note_vel != 100:
                        showVelocities = True
                        break

                for n in pattern.notes:
                    note_on = n.note_on - offset_h
                    draw_x = self.x + pad_l + key_w + 2 + 4 * bar_w * note_on
                    draw_y = self.y + pad_b + (key_h + 1) * ((n.note_pitch + transpose - offset_v) if not isDrum else (n.note_pitch - offset_v))

                    if note_on < 0 or draw_x > self.right - pad_r: continue
                    if draw_y < self.y + pad_b: continue

                    Color(*pattern.color,.55) # idea: current simultaneous notes in darker in the same pattern view --> makes editing WAY EASIER (TODO)
                    Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.note_len - 2, key_h))

                    if n == pattern.getNote():
                        Color(1,1,1,.6)
                        Rectangle(pos = (draw_x + 1, draw_y), size = (4 * bar_w * n.note_len - 2, key_h))
                        
                        if pattern.current_gap:
                            Color(1,1,1,.4)
                            Rectangle(pos = (draw_x + 4 * bar_w * n.note_len - 1, draw_y), size = (4 * bar_w * pattern.current_gap, key_h / 4))

                    if n.note_pan != 0:
                        Color(*(mixcolor((1,1,1),pattern.color)))
                        label = CoreLabel(text = strfloat(n.note_pan), font_size = par_font_size + (-1 if n.note_len >= .125 else -2), font_name = self.font_name)
                        label.refresh()
                        Rectangle(size = label.texture.size, \
                                  pos = (draw_x + 4 * bar_w * n.note_len - label.width - 2, draw_y - .25*label.height - (1 if not isDrum else 0.5) * key_h), \
                                  texture = label.texture)

                    vel_and_aux_info = ''
                    if n.note_aux != 0:
                        vel_and_aux_info = '(' + strfloat(n.note_aux) + ')'
                    if showVelocities:
                        vel_and_aux_info += strfloat(n.note_vel)
                    if vel_and_aux_info != '':
                        Color(*(mixcolor((0,0,0),pattern.color) if n == pattern.getNote() else mixcolor((1,1,1),pattern.color)))
                        label = CoreLabel(text = vel_and_aux_info, font_size = par_font_size + (-1 if n.note_len >= .125 else -2), font_name = self.font_name)
                        label.refresh()
                        Rectangle(size = label.texture.size, \
                                  pos = (draw_x + 4 * bar_w * n.note_len - label.width - 2, draw_y - .25*label.height + 1), \
                                  texture = label.texture)

                    if n.note_slide != 0:
                        Color(*(mixcolor((1,1,1),pattern.color)))
                        label = CoreLabel(text = strfloat(n.note_slide), font_size = par_font_size + (-1 if n.note_len >= .125 else -2), font_name = self.font_name)
                        label.refresh()
                        Rectangle(size = label.texture.size, \
                                  pos = (draw_x + 4 * bar_w * n.note_len - label.width - 2, draw_y - .25*label.height + 1 + key_h), \
                                  texture = label.texture)

            ### NUMBERINPUT ###
            Color(1,0,1,.9)
            label = CoreLabel(text = parent.numberInput, font_size = 12, font_name = self.font_name)
            label.refresh()
            Rectangle(size = label.texture.size, pos = (self.x + self.width - pad_r - label.width, self.y + pad_b - label.height), texture = label.texture)

    def scroll(self, axis, inc, is_drum = False):
        if is_drum:
            if axis == 'horizontal':
                self.offset_drum_h = max(0, self.offset_drum_h + inc)
            elif axis == 'vertical':
                self.offset_drum_v = max(0, self.offset_drum_v + inc)
            else:
                print("tried scrolling on some weird axis:", axis)            
        else:
            if axis == 'horizontal':
                self.offset_h = max(0, self.offset_h + inc)
            elif axis == 'vertical':
                self.offset_v = max(0, self.offset_v + inc)
            else:
                print("tried scrolling on some weird axis:", axis)

    def scaleByFactor(self, axis, factor, is_drum = False):
        if is_drum:
            if axis == 'horizontal':
                self.scale_drum_h = round(self.scale_drum_h * factor, 2)
            elif axis == 'vertical':
                self.scale_drum_v = round(self.scale_drum_v * factor, 2)
            else:
                print("tried scaling by some weird axis:", axis)
        else:
            if axis == 'horizontal':
                self.scale_h = round(self.scale_h * factor, 2)
            elif axis == 'vertical':
                self.scale_v = round(self.scale_v * factor, 2)
            else:
                print("tried scaling by some weird axis:", axis)

                
    def updateDrumkit(self, drumkit):
        if len(drumkit) < len(self.drumkit):
            self.offset_drum_v += len(self.drumkit) - len(drumkit)
        self.drumkit = drumkit

                            
#    def updateScale(self, scale_v = None, scale_h = None, delta_h = 0, delta_v = 0):
#        if scale_v and scale_v > 0: self.scale_v = scale_v
#        if scale_h and scale_h > 0: self.scale_h = scale_h
#        if delta_h > 0: self.scale_v += delta_h
#        if delta_v > 0: self.scale_h += delta_v
#        # not accessible yet, but probably implemented :)



class CurveWidget(Widget):

    w = 1200
    h = 600
    b = 150
    o = 15
    
    res = 100
    
    c_x = 0
    c_y = 0
    
    fit_plot = []
    fit_dots = 8
    
    latest_pars = [.5, 0, 0.5, -.2, 10, pi/2, -.2, .2] # I like this one
    
    def __init__(self, parent, **kwargs):
        super(CurveWidget, self).__init__(**kwargs)
        self.c_x = parent.center_x
        self.c_y = parent.center_y
        self.update()
                               
    # TODO: don't remove points, but make them drag'n'droppable!
    def on_touch_down(self, touch):
        self.fit_plot.append([touch.x, touch.y])
        
        self.update()

        if len(self.fit_plot) == self.fit_dots:
            print("FIT NOW!")
            
            def testfunc(x, p0, p1, p2, p3, p4, p5, p6, p7):
                return self.automation_curve(x, pars=[p0,p1,p2,p3,p4,p5,p6,p7])
            
            x_data = [self.coord_plot2internal(f)[0] for f in self.fit_plot]
            y_data = [self.coord_plot2internal(f)[1] for f in self.fit_plot]
            
            try:
                pars, par_covars = optimize.curve_fit(testfunc, x_data, y_data, self.latest_pars)
            except RuntimeError as e:
                print('Shit.', e)
            else:
                self.latest_pars = pars
            
            self.fit_plot = []
            self.update()

    def coord_internal2plot(self, iCoord):
        return (self.c_x + (self.w-2*self.o)*iCoord[0], self.c_y - (self.b+self.o) + (self.h-2*self.o)*iCoord[1])
    
    def coord_plot2internal(self, pCoord): #float?
        return ((pCoord[0] - self.c_x)/(self.w-2*self.o), (pCoord[1] - self.c_y + (self.b+self.o))/(self.h-2*self.o))
    
    def update(self):
        self.canvas.clear()
        with self.canvas:
            
            Color(0,0,0)
            Rectangle(pos=(self.c_x - self.w/2, self.c_y - self.b), size=(self.w, self.h))
            
            Color(1,0,1,.5)
            Line(rectangle = (self.c_x - self.w/2, self.c_y - self.b, self.w, self.h), width = 4)

            plot = []
            for ix in range(self.res):
                plot.append(self.coord_internal2plot((ix / (self.res+1) - .5, self.automation_curve(ix / self.res))))

            Color(.6,.8,.8)
            Line(points = plot, width = 3)
                
            for ic in range(len(self.fit_plot)):
                Color(.1,.3,.2)
                Ellipse(pos = (self.fit_plot[ic][0] - self.o/2, self.fit_plot[ic][1] - self.o/2), size=(self.o, self.o))

    def automation_curve(self,x,pars=[]):
        if not pars or len(pars)!=8:
            pars = self.latest_pars

        return np.clip(pars[0] + pars[1]*x + pars[2]*x*x + pars[3]*np.sin(pars[4]*x + pars[5]) + pars[6]*np.exp(-pars[7]*x), 0, 1)
 

class EditSynthDialog(ModalView):
    synthNameInput = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.synth_name = kwargs.pop('synth_name')
        self.synth_isdrum = kwargs.pop('is_drum')
        super(EditSynthDialog, self).__init__(**kwargs)
        self.synthNameInput.text = self.synth_name
        self.synthNameInput.select_all()
        
        self.root = App.get_running_app().root

    def synthChangeName(self, name):
        self.root.synthChangeName(name, drum = self.synth_isdrum)

    def synthDeactivate(self):
        self.root.synthDeactivate(drum = self.synth_isdrum)


class ImportPatternDialog(ModalView):
    importPatternFilenameInput = ObjectProperty(None)
    importPatternList = ObjectProperty(None)
    importPatternButton = ObjectProperty(None)

    XML_filename = None
    return_pattern = None

    def __init__(self, **kwargs):
        lastFilename = kwargs.pop('filename')
        super(ImportPatternDialog, self).__init__(**kwargs)
        if lastFilename:
            self.importPatternFilenameInput.text = lastFilename
            self.parseFile()

    def parseFile(self):
        self.XML_filename = self.importPatternFilenameInput.text
        try:
            open(self.XML_filename, 'r').close()
        except FileNotFoundError:
            self.importPatternList.data = self.importPatternList.empty_data
            self.importPatternFilenameInput.text = "FILE NOT FOUND (i guess you're one of the dumber ones)"
            self.importPatternFilenameInput.select_all()
            self.XML_filename = None
            return
        
        XML_root = ET.parse(self.XML_filename).getroot()
        pattern_data = []
        for element in XML_root.iter():
                if element.tag == 'pattern':
                        elem_name = element.attrib['name']
                        elem_pos = float(element.attrib['pos'])/LMMS_scalenotes
                        pattern_data.append({'text': elem_name + ' @ ' + strfloat(elem_pos+1), 'element': element})

        self.importPatternList.data = pattern_data

    def clearFile(self):
        self.importPatternList.data = self.importPatternList.empty_data
        self.importPatternFilenameInput.text = ""
        self.importPatternFilenameInput.focus = True

    def parsePattern(self):
        if not self.importPatternList.data: return

        XML_data = self.importPatternList.getSelectedData()
        print(XML_data)
        if not XML_data or not XML_data['text']:
            return

        self.return_pattern = Pattern(name = XML_data['text'], synth_type = 'I')
        pattern_length = 1

        for elem_note in XML_data['element']:
            print(elem_note.tag, elem_note.attrib, end='')
            if elem_note.tag == 'note':
                note_on = float(elem_note.attrib['pos'])/LMMS_scalenotes
                note_len = float(elem_note.attrib['len'])/LMMS_scalenotes
                self.return_pattern.notes.append(
                    Note(
                        note_on    = note_on,
                        note_len   = note_len,
                        note_pitch = int(float(elem_note.attrib['key'])),
                        note_pan   = int(float(elem_note.attrib['pan'])),
                        note_vel   = int(float(elem_note.attrib['vol'])),
                        note_slide = 0)
                    )
                pattern_length = max(pattern_length, ceil(note_on + note_len))
                print(' --> read', end='')
            print()
        self.return_pattern.length = pattern_length

        self.dismiss()

class ExportPatternDialog(ModalView):
    pass


class SelectSynthDialog(ModalView):
    selectSynthFilterInput = ObjectProperty(None)
    selectSynthList = ObjectProperty(None)

    synths = []
    selected_synth = None
    complete_synthlist = []

    def __init__(self, **kwargs):
        self.synths = kwargs.pop('synths')
        self.selected_synth = kwargs.pop('current_synth')
        super(SelectSynthDialog, self).__init__(**kwargs)
        
        self.complete_synthlist = []
        for index, synth in enumerate(self.synths):
            synth_name = synth[2:]
            self.complete_synthlist.append({'text': synth_name, 'index': index})
        self.selectSynthList.data = self.complete_synthlist

    def applyFilter(self):
        self.selectSynthList.data = [synth for synth in self.complete_synthlist if self.selectSynthFilterInput.text in synth['text']]
        # check whether selected synth is in list or not..?

    def clearFilter(self):
        self.selectSynthList.data = self.complete_synthlist
        self.selectSynthFilterInput.focus = True
        # check whether selected synth is in list or not..?

    def switchToSelected(self):
        self.selected_synth = self.selectSynthList.getSelectedData()['index']
        self.dismiss()

    def switchToRandom(self):
        self.selected_synth = randint(0, len(self.synths) - 2)
        self.dismiss()

    def dontSwitch(self):
        self.selected_synth = None
        self.dismiss()