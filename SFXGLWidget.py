#!/usr/bin/env python
#
# toy210 - the team210 live shader editor
#
# Copyright (C) 2017/2018 Alexander Kraus <nr4@z10.info>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# matze modified and severely disfigured this code.
#

from OpenGL.GL import *
from OpenGL.GLU import *
import datetime
from numpy import *
from struct import *

class SFXGLWidget():
    def __init__(self, parent):
        self.program = 0
        self.iSampleRateLocation = 0
        self.iBlockOffsetLocation = 0
        self.hasShader = False
        self.parent = parent
        self.duration = 60. #1 min of sound
        self.samplerate = 44100 #TODO: add selector to code
        self.nsamples = 2*self.duration*self.samplerate
        self.nblocks = int(ceil(float(self.nsamples)/float(512*512)))
        self.blocksize = 512*512
        self.nsamples_real = 2*self.nblocks*self.blocksize
        self.duration_real = float(self.nsamples_real)/float(self.samplerate)
        self.image = None
        self.music = None
        self.omusic = None
        
        self.parent = parent
        
        self.params = []
        self.values = []
        
        self.initializeGL()
        
    def initializeGL(self):
        print("Init.")
        glEnable(GL_DEPTH_TEST)
        
        self.framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer)
        print("Bound buffer.")
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        print("Bound texture with id ", self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 512, 512, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.image)
        print("Teximage2D returned.")
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.texture, 0)
        
    def newShader(self, source) :
        
        self.shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(self.shader, source)
        glCompileShader(self.shader)
        
        status = glGetShaderiv(self.shader, GL_COMPILE_STATUS)
        if status != GL_TRUE :
            log = glGetShaderInfoLog(self.shader)
            return log.decode('utf-8')
        
        self.program = glCreateProgram()
        glAttachShader(self.program, self.shader)
        glLinkProgram(self.program)
        
        status = glGetProgramiv(self.program, GL_LINK_STATUS)
        if status != GL_TRUE :
            log = glGetProgramInfoLog(self.program)
            return log.decode('utf-8')
                
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer)
        glUseProgram(self.program)
        
        self.iBlockOffsetLocation = glGetUniformLocation(self.program, 'iBlockOffset')
        self.iSampleRateLocation = glGetUniformLocation(self.program, 'iSampleRate')
        
        for i in range(len(self.params)):
            location = glGetUniformLocation(self.program, self.params[i])
            glUniform1f(location, self.values[i])
        
        OpenGL.UNSIGNED_BYTE_IMAGES_AS_STRING = True
        music = bytearray(self.nblocks*self.blocksize*4)
        
        for i in range(self.nblocks) :
            glUseProgram(self.program)
            glUniform1f(self.iBlockOffsetLocation, float32(i*self.blocksize)/float32(self.samplerate))
            glUniform1f(self.iSampleRateLocation, float32(self.samplerate)) 
            
            glViewport(0,0,512,512)
            
            glBegin(GL_QUADS);
            glVertex3f(-1,-1,0);
            glVertex3f(-1,1,0);
            glVertex3f(1,1,0);
            glVertex3f(1,-1,0);
            glEnd();

            glFlush();
            
            music[4*i*self.blocksize:4*(i+1)*self.blocksize] = glReadPixels(0, 0, 512, 512, GL_RGBA, GL_UNSIGNED_BYTE)
                    
        music = unpack('<'+str(self.blocksize*self.nblocks*2)+'H', music)
        
        #music = (float32(music)-32768.)/32768. # scale onto right interval. FIXME render correctly, then this is not needed.
        
        music = float16(music)
        
        self.omusic = music
        
        music = pack('<'+str(self.blocksize*self.nblocks*2)+'f', *music)
        self.music = music

        return 'Success.'
