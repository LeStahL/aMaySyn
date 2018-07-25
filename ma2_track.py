import kivy
kivy.require('1.10.0') # replace with your current kivy version !
from kivy.app import App

from ma2 import Ma2Widget

class Track():
    
    def __init__(self, name, synth = None):
        self.name = name
        self.modules = []
        self.current_module = 0
        self.setSynth(synth)

    # helpers...
    def getModule(self, offset=0):        return self.modules[(self.current_module + offset) % len(self.modules)] if isinstance(self.current_module, int) and self.modules else None
    def getModulePattern(self, offset=0): return self.getModule(offset).pattern if self.getModule(offset) else None 
    def getModuleOn(self, offset=0):      return self.getModule(offset).mod_on
    def getModuleLen(self, offset=0):     return self.getModule(offset).pattern.length
    def getModuleOff(self, offset=0):     return self.getModuleOn(offset) + self.getModuleLen(offset)
    def getFirstModule(self):             return self.modules[0]  if len(self.modules) > 0 else None
    def getFirstModuleOn(self):           return self.getFirstModule().mod_on if self.getFirstModule() else None
    def getLastModule(self):              return self.modules[-1] if len(self.modules) > 0 else None
    def getLastModuleOff(self):           return (self.getLastModule().mod_on + self.getLastModule().pattern.length) if self.getLastModule() else None

    def addModule(self, mod_on, pattern, transpose = 0, select = False):
        self.modules.append(Module(mod_on, pattern, transpose))
        if select:
            self.current_module = len(self.modules) - 1

    def delModule(self):
        if self.modules:
            del self.modules[-1]
            self.current_module = min(self.current_module, len(self.modules)-1)

    def switchModule(self, inc, to = None):
        if self.modules:
            if to is None:
                self.current_module = (self.current_module + inc) % len(self.modules)
            else:
                self.current_module = (to + len(self.modules)) % len(self.modules)

    def transposeModule(self, inc):
        if self.modules:
            self.getModule().transpose += inc

    def moveModule(self, inc):
        if self.modules:
            if (self.getModule() != self.getFirstModule()) and (self.getModuleOn() + inc < self.getModuleOff(-1)): return
            if (self.getModule() != self.getLastModule()) and (self.getModuleOff() + inc > self.getModuleOn(+1)): return
            if (self.getModuleOn() + inc < 0): return

            self.getModule().mod_on += inc
        #cool TODO: jump into gaps if possible somewhere - rearrange!
        #TODO: in filling, appending: order has to be maintained!

    def moveAllModules(self, inc):
        if self.modules:
            if (self.getFirstModuleOn() + inc < 0): return
        
        for m in self.modules:
            m.mod_on += inc
        
    def switchModulePattern(self, pattern):
        if self.modules:

            # maybe we need to move all the following modules
            if self.current_module < len(self.modules) - 1:
                offset = pattern.length - self.getModuleLen()
                for f in self.modules[self.current_module + 1:]:
                    f.mod_on += offset

            self.getModule().pattern = pattern

        
    def checkModuleCollision(self, module):
        pass
        
    def clearModules(self):
        self.modules=[]

    def setSynth(self, synth):
        self.synth = synth if synth in Ma2Widget.synths else 'I_None'
            
    def isDrum(self):
        return self.synth[0]=='D'


class Module():

    mod_on = 0
    #mod_off = 0
    pattern = None
    transpose = 0
    
    def __init__(self, mod_on, pattern, transpose = 0):
        self.mod_on = mod_on
        #self.mod_off = mod_on + pattern.length
        self.pattern = pattern
        self.transpose = transpose

    def setPattern(self, pattern):
        if App.get_running_app().root.existsPattern(pattern):
            self.pattern = pattern

