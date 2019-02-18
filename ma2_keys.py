global_keys  = {
                'escape'        : 'EXIT',
                'f8'            : 'DEBUG TOGGLE',
                'tab'           : 'PANEL SWITCH',
                'f1'            : 'COLORS RANDOMIZE',
                'f2'            : 'SONG RENAME',
                'f3'            : 'SONG CHANGE PARAMETERS',
                'f5'            : 'SYNTH RELOAD',
                'f11'           : 'CURVE EDIT',
                'f12'           : 'MUTE',
                'ctrl shift b'  : 'SHADER PLAY',
                'ctrl n'        : 'SONG CLEAR',
                'ctrl l'        : 'SONG LOAD',
                'ctrl s'        : 'SONG SAVE',
                'ctrl b'        : 'SHADER CREATE',
                'ctrl z'        : 'UNDO',
                'ctrl y'        : 'REDO',
                'a'             : 'SYNTH SELECT NEXT',
                's'             : 'SYNTH SELECT LAST',
                'pagedown'      : 'PATTERN SELECT NEXT',
                'pageup'        : 'PATTERN SELECT LAST'
               }

track_keys   = {
                'ctrl shift left'  : 'TRACK SHIFT LEFT',
                'ctrl shift right' : 'TRACK SHIFT RIGHT',
                'shift up'         : 'MOD TRANSPOSE UP',
                'shift down'       : 'MOD TRANSPOSE DOWN',
                'shift left'       : 'MOD SHIFT LEFT',
                'shift right'      : 'MOD SHIFT RIGHT',
                'shift home'       : 'MOD SHIFT HOME',
                'shift end'        : 'MOD SHIFT END',
                'ctrl +'           : 'TRACK ADD NEW',
                'ctrl delete'      : 'TRACK DELETE',
                'left'             : 'MOD SELECT LEFT',
                'right'            : 'MOD SELECT RIGHT',
                'end'              : 'MOD SELECT LAST',
                'home'             : 'MOD SELECT FIRST',
                'up'               : 'TRACK SELECT LAST',
                'down'             : 'TRACK SELECT NEXT',
                '+'                : 'MOD ADD NEW',
                'c'                : 'MOD ADD CLONE',
                'delete'           : 'MOD DELETE',
                'f6'               : 'TRACK RENAME',
                'f7'               : 'TRACK CHANGE PARAMETERS',
                'f9'               : 'DEBUG PRINT PATTERNS'
               }

pattern_keys = {
                'ctrl shift pageup'   : 'PATTERN LONGER STRETCH', 
                'ctrl shift pagedown' : 'PATTERN SHORTER STRETCH',
                'shift left'          : 'NOTE SHORTER',
                'shift right'         : 'NOTE LONGER',
                'shift up'            : 'NOTES TRANSPOSE ALL UP',
                'shift down'          : 'NOTES TRANSPOSE ALL DOWN',
                'shift pageup'        : 'PATTERN LONGER',
                'shift pagedown'      : 'PATTERN SHORTER',
                'backspace'           : 'NOTE GAP ZERO',
                'ctrl left'           : 'NOTE SHIFT LEFT',
                'ctrl right'          : 'NOTE SHIFT RIGHT',
                'ctrl up'             : 'NOTE TRANSPOSE OCT UP',
                'ctrl down'           : 'NOTE TRANSPOSE OCT DOWN',
                'ctrl +'              : 'PATTERN ADD NEW',
                'ctrl *'              : 'PATTERN ADD CLONE',
                'ctrl delete'         : 'PATTERN DELETE',
                'left'                : 'NOTE SELECT LEFT',
                'right'               : 'NOTE SELECT RIGHT',
                'home'                : 'NOTE SELECT FIRST',
                'end'                 : 'NOTE SELECT LAST',
                'up'                  : 'NOTE TRANSPOSE UP',
                'down'                : 'NOTE TRANSPOSE DOWN',
                '+'                   : 'NOTE ADD NEW',
                'c'                   : 'NOTE ADD CLONE',
                '*'                   : 'NOTE CLONE SELECTION',
                'delete'              : 'NOTE DELETE',
                'spacebar'            : 'GAP LONGER',
                'backspace'           : 'GAP SHORTER',
                'v'                   : 'NOTE SET VELOCITY',
                'g'                   : 'NOTE SET SLIDE',
                'f6'                  : 'PATTERN RENAME',
                'f9'                  : 'DEBUG PRINT NOTES'
               }

# https://kivy.org/doc/stable/_modules/kivy/core/window.html

def interpretKeypress(key, modifiers, trkActive = False, ptnActive = False):

    key = correctForNumpad(key, key)
    if 'shift' in modifiers: key = 'shift ' + key
    if 'ctrl' in modifiers: key = 'ctrl ' + key
    
    action = None

    if key in global_keys:
        action = global_keys[key]
        
    elif trkActive and key in track_keys:
        action = track_keys[key]
        
    elif ptnActive and key in pattern_keys:
        action = pattern_keys[key]

    return action


def doesActionChangeState(action):
    
    if action in ['SONG RENAME',
                  'SONG CHANGE PARAMETERS',
                  'CURVE EDIT',
                  'SONG CLEAR'
                  'SONG LOAD',
                  'SYNTH SELECT NEXT',
                  'SYNTH SELECT LAST',
                  'PATTERN SELECT NEXT',
                  'PATTERN SELECT LAST',
                ]:
        return True
    
    if action in track_keys.values() and action not in ['DEBUG PRINT PATTERNS']:
        return True
    
    if action in pattern_keys.values() and action not in ['DEBUG PRINT NOTES']:
        return True
    
    return False

def correctForNumpad(keytext, k):
    if 'numpad' not in k: return keytext
    
    return k.replace('numpadadd','+') \
            .replace('numpadsubstract','-') \
            .replace('numpadmul','*') \
            .replace('numpaddivide','/') \
            .replace('numpaddecimal', '.') \
            .replace('numpad','')
