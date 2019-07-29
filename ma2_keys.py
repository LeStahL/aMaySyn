global_keys  = {
                'escape'            : 'EXIT',
                'f8'                : 'DEBUG TOGGLE',
                'shift tab'         : 'PANEL SWITCH',  # 'tab' alone conflicted with the usage of alt-tab...
                'ctrl tab'          : 'PANEL SWITCH',
                'f1'                : 'COLORS RANDOMIZE',
                'f2'                : 'SONG RENAME',
                'f3'                : 'ENTER SONG COMMAND',
                'f4'                : 'SONG CHANGE LOOPING OPTION',
                'f5'                : 'SYNTH RELOAD',
                'ctrl f5'           : 'SYNTH RELOAD NEW RANDOMS',
                'f7'                : 'TRACK CHANGE PARAMETERS',
                'f11'               : 'CURVE EDIT',
                'f12'               : 'MUTE',
                'enter'             : 'MUTE', 
                'm'                 : 'TRACK MUTE',
                'n'                 : 'TRACK SOLO',
                'ctrl shift b'      : 'SHADER PLAY',
                'ctrl enter'        : 'SHADER PLAY',
		        'ctrl shift enter'  : 'SHADER RENDER',
                'ctrl n'            : 'SONG CLEAR',
                'ctrl l'            : 'SONG LOAD',
                'ctrl s'            : 'SONG SAVE',
                'ctrl b'            : 'SHADER CREATE',
                'ctrl z'            : 'UNDO',
                'ctrl y'            : 'REDO',
                'a'                 : 'SYNTH SELECT NEXT',
                's'                 : 'SYNTH SELECT LAST',
                'pageup'            : 'PATTERN SELECT NEXT',
                'pagedown'          : 'PATTERN SELECT LAST',
                'ctrl i'            : 'DIALOG PATTERN IMPORT',
                'ctrl o'            : 'DIALOG PATTERN EXPORT',
                'shift e'           : 'SYNTH FILE RESET DEFAULT',
                'i'                 : 'SCROLL UP',
                'k'                 : 'SCROLL DOWN',
                'j'                 : 'SCROLL LEFT',
                'l'                 : 'SCROLL RIGHT',
                'shift i'           : 'ZOOM VERT IN',
                'shift k'           : 'ZOOM VERT OUT',
                'shift j'           : 'ZOOM HORZ OUT',
                'shift l'           : 'ZOOM HORZ IN',
                'shift f3'          : 'ENTER COMMAND',
               }

track_keys   = {
                'ctrl shift left'  : 'TRACK SHIFT ALL LEFT',
                'ctrl shift right' : 'TRACK SHIFT ALL RIGHT',
                'ctrl shift up'    : 'MOD TRANSPOSE OCT UP',
                'ctrl shift down'  : 'MOD TRANSPOSE OCT DOWN',
                'ctrl left'        : 'TRACK SHIFT LEFT',
                'ctrl right'       : 'TRACK SHIFT RIGHT',
                'shift up'         : 'MOD TRANSPOSE UP',
                'shift down'       : 'MOD TRANSPOSE DOWN',
                'shift left'       : 'MOD SHIFT LEFT',
                'shift right'      : 'MOD SHIFT RIGHT',
                'shift home'       : 'MOD SHIFT HOME',
                'shift end'        : 'MOD SHIFT END',
                'shift insert'     : 'MOD SHIFT ANYWHERE',
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
                'e'                : 'SYNTH EDIT',
                'ctrl e'           : 'SYNTH CLONE HARD',
               }

pattern_keys = {
                'ctrl shift pageup'   : 'PATTERN LONGER STRETCH', 
                'ctrl shift pagedown' : 'PATTERN SHORTER STRETCH',
                'ctrl shift up'       : 'NOTE TRANSPOSE OCT UP',
                'ctrl shift down'     : 'NOTE TRANSPOSE OCT DOWN',
                'ctrl shift left'     : 'NOTE SHIFT ALL LEFT',
                'ctrl shift right'    : 'NOTE SHIFT ALL RIGHT',
                'shift left'          : 'NOTE SHORTER',
                'shift right'         : 'NOTE LONGER',
                'shift up'            : 'NOTES TRANSPOSE ALL UP',
                'shift down'          : 'NOTES TRANSPOSE ALL DOWN',
                'shift pageup'        : 'PATTERN LONGER',
                'shift pagedown'      : 'PATTERN SHORTER',
                'shift backspace'     : 'NOTE GAP ZERO',
                'ctrl left'           : 'NOTE SHIFT LEFT',
                'ctrl right'          : 'NOTE SHIFT RIGHT',
                'ctrl up'             : 'NOTE TRANSPOSE UP',
                'ctrl down'           : 'NOTE TRANSPOSE DOWN',
                'ctrl +'              : 'PATTERN ADD NEW',
                'ctrl *'              : 'PATTERN ADD CLONE',
                'ctrl delete'         : 'PATTERN DELETE',
                'left'                : 'NOTE SELECT LEFT',
                'right'               : 'NOTE SELECT RIGHT',
                'home'                : 'NOTE SELECT FIRST',
                'end'                 : 'NOTE SELECT LAST',
                '+'                   : 'NOTE ADD NEW',
                'c'                   : 'NOTE ADD CLONE',
                '*'                   : 'NOTE CLONE SELECTION',
                'delete'              : 'NOTE DELETE',
                'spacebar'            : 'GAP LONGER',
                'backspace'           : 'GAP SHORTER',
                'v'                   : 'NOTE SET VELOCITY',
                'g'                   : 'NOTE SET SLIDE',
                'p'                   : 'NOTE SET PAN',
                'x'                   : 'NOTE SET AUX',
                'f6'                  : 'PATTERN RENAME',
                'f9'                  : 'DEBUG PRINT NOTES',
                'e'                   : 'DRUMSYNTH EDIT',
                'ctrl e'              : 'DRUMSYNTH CLONE HARD',
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
