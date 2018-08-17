import kivy
kivy.require('1.10.0') # replace with your current kivy version !
from kivy.app import App

from ma2 import Ma2Widget
from ma2_globals import synths

class Track():
    
    def __init__(self, name, synth = ''):
        self.name = name
        self.modules = []
        self.current_module = 0
        self.current_synth = synths.index(synth) if synth in synths else -1

    # helpers...
    def getModule(self, offset=0):        return self.modules[(self.current_module + offset) % len(self.modules)] if isinstance(self.current_module, int) and self.modules else None
    def getModulePattern(self, offset=0): return self.getModule(offset).pattern if self.getModule(offset) else None 
    def getModuleOn(self, offset=0):      return self.getModule(offset).mod_on
    def getModuleLen(self, offset=0):     return self.getModule(offset).pattern.length
    def getModuleOff(self, offset=0):     return self.getModule(offset).getModuleOff()
    def getFirstModule(self):             return self.modules[0]  if len(self.modules) > 0 else None
    def getFirstModuleOn(self):           return self.getFirstModule().mod_on if self.getFirstModule() else None
    def getLastModule(self):              return self.modules[-1] if len(self.modules) > 0 else None
    def getLastModuleOff(self):           return (self.getLastModule().mod_on + self.getLastModule().pattern.length) if self.getLastModule() else 0

    def getSynthName(self):               return synths[self.current_synth] if synths else ''
    def getSynthIndex(self):              return (self.current_synth - len(synths)) if synths[self.current_synth][0] == '_' and self.current_synth != -1 else self.current_synth

    def addModule(self, mod_on, pattern, transpose = 0, select = True):
        self.modules.append(Module(mod_on, pattern, transpose))
        if select:
            self.current_module = len(self.modules) - 1

    def delModule(self):
        if self.modules:
            del self.modules[self.current_module if self.current_module is not None else -1]
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

    #def wouldModuleCollide(self, test_on, test_len):
        #for m in self.modules:
            #print(m.mod_on, m.mod_on + m.pattern.length, test_on, test_on + test_len)
            #if m.mod_on < test_on and m.mod_on + m.pattern.length > test_on + test_len: return True
        #return False

    def moveModule(self, inc, move_home = None, move_end = None):
        if self.modules:
            move_to = self.getModuleOn() + inc
            if move_to < 0: return
            try_leap = 0
            
            if inc < 0:
                if self.getModule() != self.getFirstModule():
                    while move_to < self.getModuleOff(try_leap-1): 
                        try_leap -=1
                        move_to = self.getModuleOn(try_leap) - self.getModuleLen()
                        if move_to < 0: return
                        if move_to + self.getModuleLen() <= self.getFirstModuleOn(): break
                
            else:
                if self.getModule() != self.getLastModule():
                    while move_to + self.getModuleLen() > self.getModuleOn(try_leap+1):
                        try_leap += 1
                        move_to = self.getModuleOff(try_leap)
                        if move_to >= self.getLastModuleOff(): break
                    
            self.getModule().mod_on = move_to
            self.current_module += try_leap

            self.modules.sort(key = lambda m: m.mod_on)

        if move_home:
            if self.getModule() == self.getFirstModule() or self.getFirstModuleOn() >= self.getModuleLen():
                self.getModule().mod_on = 0
                self.modules.sort(key = lambda m: m.mod_on)            
                self.current_module = 0
        if move_end:
            if self.getModule() != self.getLastModule():
                self.getModule().mod_on = self.getLastModuleOff()
                self.modules.sort(key = lambda m: m.mod_on)            
                self.current_module = len(self.modules) - 1

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

    def switchSynth(self, inc):
        if synths:
            self.current_synth = (self.current_synth + inc) % len(synths)
            
        # TODO: option to set specific synth (find out which number that one should be)
        #self.synth = synth if synth in synths else 'I_None'


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

    def getModuleOff(self):
        return self.mod_on + (self.pattern.length if self.pattern else 0)

    def setPattern(self, pattern):
        if App.get_running_app().root.existsPattern(pattern):
            self.pattern = pattern
