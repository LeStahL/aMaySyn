#import math
from random import random

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f>=1 or f<0 or abs(f)<1e-4 else 1:].replace('-0.','-.')

def GLstr(s):
    try:
        f = float(s)
    except ValueError:
        return s
    else:
        return GLfloat(f)

#reserved keywords you cannot name a form after ~ f,t are essential, and maybe we want to use the other
_f = {'ID':'f', 'type':'uniform'}
_t = {'ID':'t', 'type':'uniform'}
_t_ = {'ID':'_t', 'type':'uniform'}
_B = {'ID':'B', 'type':'uniform'}
_vel = {'ID':'vel', 'type':'uniform'}
_Bsyn = {'ID':'Bsyn', 'type':'uniform'}
_Bproc = {'ID':'Bproc', 'type':'uniform'}
_Bprog = {'ID':'Bprog', 'type':'uniform'}
_L = {'ID':'L', 'type':'uniform'}
_tL = {'ID':'tL', 'type':'uniform'}
_SPB = {'ID':'SPB', 'type':'uniform'}
_BPS = {'ID':'BPS', 'type':'uniform'}
_BPM = {'ID':'BPM', 'type':'uniform'}
_note = {'ID':'note', 'type':'uniform'}
_Fsample = {'ID':'Fsample', 'type':'uniform'}

newlineplus = '\n'+6*' '+'+'

def synatize(syn_file = 'test.syn'):

    syncode = ""

    form_list = [_f, _t, _t_, _B, _vel, _Bsyn, _Bproc, _Bprog, _L, _tL, _SPB, _BPS, _BPM, _note, _Fsample]
    main_list = []
   
    print('READING', './' + syn_file + ':')
   
    with open(syn_file,"r") as template:
        lines = template.readlines()
        
    for l in lines:
        if l=='\n' or l[0]=='#': continue
    
        line = l.split()
        cmd = line[0].lower()
        cid = line[1]
        arg = line[2:]
        
        # this will be next level: arg in the form param=value - now separate
        sargs = {'mode':[]}
        for a in arg[:]:
            if "=" in a:
                key = a.split("=")[0].lower()
                val = a.split("=")[1] if key != 'mode' else a.split("=")[1].split(",")
                sargs.update({key : val})
                arg.remove(a)
        
        # small sanity check for number of arguments
        try:
            assert len(line) >= arg_required(cmd, arg)
        except AssertionError as e:
            print('ERROR! THIS LINE DOES NOT MATCH THE NUMBER OF REQUIRED ARGUMENTS:', l, 'REQUIRES: '+str(arg_required(cmd, arg))+' ARGUMENTS. HAS: '+str(len(line)), sep='\n')
            quit()
        
       
        if cid in [f['ID'] for f in form_list]:
            print(' -> ERROR! ID \"' + cid + '\" already taken. Ignoring line.')
            continue

        if cmd == 'main' or cmd == 'maindrum':
            main_list.append({'ID':cid, 'type':cmd, 'amount':len(line)-2, 'terms':arg, **sargs})

        elif cmd == 'const':
            form_list.append({'ID':cid, 'type':cmd, 'value':float(arg[0]), **sargs})
    
        elif cmd == 'random':
            rand_min = float(arg[0])
            rand_max = float(arg[1])
            digits = int(arg[2]) if len(arg)>2 else 3
            form_list.append({'ID':cid, 'type':cmd, 'value':round(rand_min+(rand_max-rand_min)*random(),digits), **sargs})
    
        elif cmd == 'osc' or cmd == 'lfo':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0].lower(), 'freq':arg[1], 'phase':arg[2] if len(arg)>2 else '0', 'par':arg[3:] if len(arg)>3 else [], **sargs})

        elif cmd == 'drum':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0].lower(), 'par':arg[1:], **sargs})

        elif cmd == 'env':
            shape = arg[0].lower()
            form = {'ID':cid, 'type':cmd, 'shape':shape, **sargs}
            
            if shape == 'adsr' or shape == 'adsrexp':
                form.update({'attack':arg[1], 'decay':arg[2], 'sustain':arg[3], 'release':arg[4], 'par':arg[5:] if len(arg)>5 else []})
            elif shape == 'ahd':
                form.update({'attack':arg[1], 'hold':arg[2], 'decay':arg[3]})
            elif shape == 'doubleslope':
                form.update({'attack':arg[1], 'decay':arg[2], 'sustain':arg[3], 'par':arg[4] if len(arg)>4 else ''})
            elif shape == 'ss':
                form.update({'attack':arg[1], 'par':arg[2] if len(arg)>2 else ''})
            elif shape == 'ssdrop':
                form.update({'decay':arg[1], 'par':arg[2] if len(arg)>2 else ''})
            elif shape == 'expdecay' or shape == 'expdecayrepeat':
                form.update({'decay':arg[1], 'par':arg[2] if len(arg)>2 else ''})

            else:
                print('ERROR! THIS ENVELOPE DOES NOT EXIST: '+shape, l, sep='\n')
                quit()
            
            form_list.append(form)

        elif cmd == 'filter':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0].lower(), 'source':arg[1], 'par':arg[2:], **sargs})

        # generic automation curve - implemented just basic for now, let's think of something great some other time
        elif cmd == 'gac':
            form_list.append({'ID':cid, 'type':cmd, 'par':arg, **sargs})

        # advanced forms ("operators"), like detune, chorus, delay, waveshaper/distortion, and more advanced: filter, reverb/*vec2 mainSound( float time )
        elif cmd == 'form':
            op = arg[0].lower()
            form = {'ID':cid, 'type':cmd, 'OP':op, **sargs}

            if op == 'mix':
                form.update({'amount':len(arg), 'terms':arg[1:]})
            elif op == 'detune':
                form.update({'source':arg[1], 'amount':arg[2:]})
            elif op == 'pitchshift':
                form.update({'source':arg[1], 'steps':arg[2]})
            elif op == 'quantize':
                form.update({'source':arg[1], 'quant':arg[2]})
            elif op == 'overdrive':
                form.update({'source':arg[1], 'gain':arg[2]})
            elif op == 'chorus':
                form.update({'source':arg[1], 'number':arg[2], 'step':arg[3], 'intensity':arg[4], 'rate':arg[5]})
            elif op == 'delay':
                form.update({'source':arg[1], 'number':arg[2], 'delay':arg[3], 'decay':arg[4]})
            elif op == 'waveshape':
                form.update({'source':arg[1], 'par':arg[2:8]})
            elif op == 'saturate':
                form.update({'source':arg[1], 'gain':arg[2]})
            elif op == 'lofi':
                form.update({'source':arg[1], 'bits':arg[2]})
            else:
                print('ERROR! THIS FORM DOES NOT EXIST: '+op, l, sep='\n')
                quit()
                
            form_list.append(form)

    drum_list = [d['ID'] for d in main_list if d['type']=='maindrum']

    return form_list, main_list, drum_list


def synatize_build(form_list, main_list, actually_used_synths = None):

    def instance(ID, mod={}, force_int = False):
        
        _return = ''

        form = next((f for f in form_list if f['ID']==ID), None)
        
        try:
            if mod:
                form = form.copy()
                form.update(mod)

            if ID[0]=='"' and ID[-1]=='"':
                return '('+ID[1:-1]+')'
            
            elif '*' in ID:
                IDproduct = ID.split('*')
                product = ''
                for factorID in IDproduct:
                    product += instance(factorID) + '*'
                return product[:-1];

            elif not form:
                if force_int:
                    return str(int(float(ID)))
                else:
                    return GLstr(ID).replace('--','+')
            
            elif form['type']=='uniform':
                return ID
            
            elif form['type']=='const' or form['type']=='random':
                return GLfloat(form['value'])
            
            elif form['type']=='form':
                if form['OP'] == 'mix':
                    return '(' + '+'.join([instance(f) for f in form['terms']]) + ')' 
                elif form['OP'] == 'detune':
                    detuned_instances = '+'.join(instance(form['source'],{'freq':'(1.-' + instance(amt) + ')*'+param(form['source'],'freq')}) for amt in form['amount']) 
                    return 's_atan(' + instance(form['source']) + '+' + detuned_instances + ')'
                elif form['OP'] == 'pitchshift':
                    return instance(form['source'],{'freq':'{:.4f}'.format(pow(2,float(form['steps'])/12)) + '*' + param(form['source'],'freq')})
                elif form['OP'] == 'quantize':
                    return instance(form['source']).replace('_TIME','floor('+instance(form['quant']) + '*_TIME+.5)/' + instance(form['quant'])) \
                                                   .replace('_PROG','floor('+instance(form['quant']) + '*_PROG+.5)/' + instance(form['quant']))
                elif form['OP'] == 'overdrive':
                    return 'clip(' + instance(form['gain']) + '*' + instance(form['source']) + ')'
                elif form['OP'] == 'chorus':
                    return '(' + newlineplus.join([instance(form['source']).replace('_PROG','(_PROG-'+'{:.1e}'.format(i*float(form['step']))+'*(1.+'+instance(form['step'])+'*_sin('+instance(form['rate'])+'*_PROG)))') for i in range(int(form['number']))]) + ')'
                elif form['OP'] == 'delay':
                    tvar = '_PROG' if not 'beat' in form['mode'] else '_BPROG'
                    return '(' + newlineplus.join(['{:.1e}'.format(pow(float(form['decay']),i)) + '*' + \
                                                   instance(form['source']).replace(tvar,'('+tvar+'-'+'{:.1e}'.format(i*float(form['delay']))+')') for i in range(int(form['number']))]) + ')'
                elif form['OP'] == 'waveshape':
                    print(form['par'])
                    return 'supershape(' + instance(form['source']) + ',' + ','.join(instance(form['par'][p]) for p in range(6)) + ')'
                elif form['OP'] == 'saturate':
                    if 'crazy' in form['mode']:
                        return 's_crzy('+instance(form['gain']) + '*' + instance(form['source']) + ')'
                    else:
                        return 's_atan('+instance(form['gain']) + '*' + instance(form['source']) + ')'
                elif form['OP'] == 'lofi':
                    return 'floor('+instance(form['bits'])+'*'+instance(form['source'])+'+.5)*'+'{:.1e}'.format(1/float(form['bits']))
                else:
                    return '1.'

            elif form['type'] == 'osc' or form['type'] == 'lfo':

                    if form['type'] == 'osc':
                        phi = instance(form['freq']) + '*_TIME'
                        pre = 'vel*'

                    elif form['type'] == 'lfo':
                        tvar = '*Bprog' if 'global' not in form['mode'] else '*B'
                        if 'time' in form['mode']: tvar = '*_PROG' if 'global' not in form['mode'] else '*_TIME'
                            
                        phi = instance(form['freq']) + tvar
                        pre = ''
                        if form['shape'] == 'squ': form['shape'] = 'psq'
                        
                        if 'scale' not in form: form['scale'] = '.5'
                        if 'shift' not in form: form['shift'] = '.5'

                                    
                    if form['shape'] == 'sin':
                        if form['phase'] == '0':
                            _return = pre + '_sin(' + phi + ')'
                        else:
                            _return = pre + '_sin(' + phi + ',' + instance(form['phase']) + ')'
          
                    elif form['shape'] == 'saw':
                        _return = pre + '(2.*fract(' + phi + '+' + instance(form['phase']) + ')-1.)'

                    elif form['shape'] == 'squ':
                        if form['par'] == '0':
                            _return = pre + '_sq(' + phi + ')'
                        else:
                            _return = pre + '_sq(' + phi + ',' + instance(form['par'][0]) + ')'

                    elif form['shape'] == 'psq':
                        if form['par'] == '0':
                            _return = pre + '_psq(' + phi + ')'
                        else:
                            _return = pre + '_psq(' + phi + ',' + instance(form['par'][0]) + ')'

                    elif form['shape'] == 'tri':
                            _return = pre + '_tri(' + phi + '+' + instance(form['phase']) + ')'

                    elif form['shape'] == 'macesq':
                            keyF = '0' if not 'follow' in form['mode'] else '1'
                            form['par'][0] = str(int(float(form['par'][0])))
                            form['par'][1] = str(int(float(form['par'][1]))) 
                            print("LOLOL", form['par'])
                            _return ='MACESQ(_PROG,'+instance(form['freq']) + ',' + instance(form['phase']) + ',' + ','.join(instance(form['par'][p], force_int=True) for p in range(0,2)) \
                                                                                                                      + ',' + ','.join(instance(form['par'][p]) for p in range(2,9))+ ',' + keyF + ')'
                    elif form['shape'] == 'fract':
                            _return = pre + '(fract(' + phi + '+' + instance(form['phase']) + ')+' + instance(form['par'][0]) + ')'

                    else:
                        print("ERROR! THIS OSC/LFO SHAPE DOES NOT EXIST: "+form['shape'], form, sep='\n')
                        quit()
                        
                    if 'overdrive' in form:
                        _return = 'clip(' + instance(form['overdrive']) + '*' + _return + ')'
                        
                    if 'scale' in form:
                        _return = instance(form['scale']) + '*' + _return
                    
                    if 'shift' in form:
                        _return = '(' + instance(form['shift']) + '+(' + _return + '))'
                    
                    return _return

            elif form['type'] == 'drum':
                
                    if form['shape'] == 'kick' or form['shape'] == 'kick2': # <start freq> <end freq> <freq decay time> <env attack time> <env decay time> <distortion> ...
                        freq_start = instance(form['par'][0])
                        freq_end = instance(form['par'][1])
                        freq_decay = instance(form['par'][2])
                        env_attack = instance(form['par'][3])
                        env_hold = instance(form['par'][4])
                        env_decay = instance(form['par'][5])
                        click_amp = instance(form['par'][6])
                        click_delay = instance(form['par'][7])
                        click_timbre = instance(form['par'][8])

                        freq_env = '('+freq_start+'+('+freq_end+'-'+freq_start+')*smoothstep(-'+freq_decay+', 0.,-_PROG))'
                        amp_env = 'vel*smoothstep(0.,'+env_attack+',_PROG)*smoothstep('+env_hold+'+'+env_decay+','+env_decay+',_PROG)'

                        if form['shape'] == 'kick':
                            distortion = instance(form['par'][9])
                            return 's_atan('+amp_env+'*(clip('+distortion+'*_tri('+freq_env+'*_PROG))+_sin(.5*'+freq_env+'*_PROG)))+'+click_amp+'*step(_PROG,'+click_delay+')*_sin(5000.*_PROG*'+click_timbre+'*_saw(1000.*_PROG*'+click_timbre+'))'
                        
                        elif form['shape'] == 'kick2':
                            sq_PHASE = instance(form['par'][9])
                            sq_NMAX = str(int(float(form['par'][10])))
                            sq_MIX = instance(form['par'][11])
                            sq_INR = instance(form['par'][12])
                            sq_NDECAY = instance(form['par'][13])
                            sq_RES = instance(form['par'][14])
                            sq_RESQ = instance(form['par'][15])
                            sq_DET = instance(form['par'][16])
                            return 's_atan('+amp_env+'*MACESQ(_PROG,'+freq_env+','+sq_PHASE+','+sq_NMAX+',1,'+sq_MIX+','+sq_INR+','+sq_NDECAY+','+sq_RES+','+sq_RESQ+','+sq_DET+',0.,1) + '+click_amp+'*.5*step(_PROG,'+click_delay+')*_sin(_PROG*1100.*'+click_timbre+'*_saw(_PROG*800.*'+click_timbre+')) + '+click_amp+'*(1.-exp(-1000.*_PROG))*exp(-40.*_PROG)*_sin((400.-200.*_PROG)*_PROG*_sin(1.*'+freq_env+'*_PROG)))'
                    
                    elif form['shape'] == 'snare':
                        freq_0 = instance(form['par'][0])
                        freq_1 = instance(form['par'][1])
                        freq_2 = instance(form['par'][2])
                        fdec01 = instance(form['par'][3])
                        fdec12 = instance(form['par'][4])
                        envdec = instance(form['par'][5])
                        envsus = instance(form['par'][6])
                        envrel = instance(form['par'][7])
                        ns_amt = instance(form['par'][8])
                        ns_att = instance(form['par'][9])
                        ns_dec = instance(form['par'][10])
                        ns_sus = instance(form['par'][11])
                        overdr = instance(form['par'][12])
                        
                        freq_env = '('+freq_2+'+('+freq_0+'-'+freq_1+')*smoothstep(-'+fdec01+',0.,-_PROG)+('+freq_1+'-'+freq_2+')*smoothstep(-'+fdec01+'-'+fdec12+',-'+fdec01+',-_PROG))'
                        return 'vel*clamp('+overdr+'*_tri(_PROG*'+freq_env+')*smoothstep(-'+envrel+',-'+fdec01+'-'+fdec12+',-_PROG) + '+ns_amt+'*fract(sin(_PROG*90.)*4.5e4)*doubleslope(_PROG,'+ns_att+','+ns_dec+','+ns_sus+'),-1., 1.)*doubleslope(_PROG,0.,'+envdec+','+envsus+')'
                        
                    elif form['shape'] == 'fmnoise':
                        env_attack = instance(form['par'][0])
                        env_decay = instance(form['par'][1])
                        env_sustain = instance(form['par'][2])
                        FMtimbre1 = instance(form['par'][3])
                        FMtimbre2 = instance(form['par'][4])
                        return 'vel*fract(sin(_TIME*100.*'+FMtimbre1+')*50000.*'+FMtimbre2+')*doubleslope(_PROG,'+env_attack+','+env_decay+','+env_sustain+')'
                        
                    elif form['shape'] == 'bitexplosion':
                        return 'vel*bitexplosion(_TIME, _BPROG, '+str(int(form['par'][0])) + ',' + ','.join(instance(form['par'][p]) for p in range(1,7)) + ')' 

            elif form['type']=='env':
                tvar = '_BPROG' if 'beat' in form['mode'] else '_PROG'
                Lvar = 'L' if 'beat' in form['mode'] else 'tL'
                if form['shape'] == 'adsr':
                    _return = 'env_ADSR('+tvar+','+Lvar+','+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+','+instance(form['release'])+')'
                elif form['shape'] == 'adsrexp':
                    _return = 'env_ADSRexp('+tvar+','+Lvar+','+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+','+instance(form['release'])+')'
                elif form['shape'] == 'ahd':
                    _return = 'env_AHD('+tvar+','+instance(form['attack'])+','+instance(form['hold'])+','+instance(form['decay'])+')'
                elif form['shape'] == 'doubleslope':
                    _return = 'doubleslope('+tvar+','+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+')'
                elif form['shape'] == 'ss':
                    _return = 'smoothstep(0.,'+instance(form['attack'])+','+tvar+')'
                elif form['shape'] == 'ssdrop':
                    _return = 'theta('+'_PROG'+')*(1.-smoothstep(0.,'+instance(form['decay'])+','+tvar+'))'
                elif form['shape'] == 'expdecay':
                    _return = 'theta('+'_BPROG'+')*exp(-'+instance(form['decay'])+'*_BPROG)'
                elif form['shape'] == 'expdecayrepeat':
                    _return = 'theta('+'_BPROG'+')*exp(-'+instance(form['decay'])+'*mod(_BPROG,'+instance(form['par'])+'))'
                else:
                    print("ERROR! THIS ENVELOPE SHAPE DOES NOT EXIST: "+form['shape'], form, sep='\n')
                    quit()

                if 'scale' in form:
                    _return = instance(form['scale']) + '*' + _return
                
                if 'shift' in form:
                    _return = '(' + instance(form['shift']) + '+(' + _return + '))'
                
                return _return


            elif form['type']=='gac':
                tvar = '_PROG' if 'global' not in form['mode'] else '_TIME'
                return 'GAC('+tvar+',' + ','.join([instance(form['par'][p]) for p in range(8)]) + ')'

            elif form['type']=='filter':
                return form['shape']+form['ID']+'(_PROG,f,tL,'+','.join(instance(form['par'][p]) for p in range(len(form['par'])))+')'

            else:
                print("ERROR! THIS FORM TYPE DOES NOT EXIST: "+form['type'], form, sep='\n')
                quit()
        
        except:
            print("UNEXPECTED UNEXPECTEDNESS IN FORM", form if form else str(ID), '', sep='\n')
            raise

    def param(ID, key):
        form = next((f for f in form_list if f['ID']==ID), None)
        try:
            value = form[key]
        except KeyError:
            return ''
        except TypeError:
            return ''
        else:
            return value

    if not main_list:
        print("WARNING: no main form defined! will return empty sound")
        syncode = "s = 0.; //some annoying weirdo forgot to define the main form!"

    else:
        if len(main_list)==1:
            syncode = "s = "
            for term in main_list[0]['terms']:
                syncode += instance(term) + (newlineplus if term != main_list[0]['terms'][-1] else ';')
           
        else:
            print(main_list, actually_used_synths)
            syncount = 1
            drumcount = 1
            syncode = 'if(Bsyn == 0){}\n' + 4*' '
            for form_main in main_list:
                if form_main['type']!='main': continue
                if actually_used_synths is None or form_main['ID'] in actually_used_synths:
                    syncode += 'else if(Bsyn == ' + str(syncount) + '){\n' + 6*' ' + 's = '
                    for term in form_main['terms']:
                        syncode += instance(term) + (newlineplus if term != form_main['terms'][-1] else ';')
                    syncode += '}\n' + 4*' '
                syncount += 1
            
            syncode = syncode.replace('vel*','') # for now, disable this for the synths above (but not for the drums below)
            syncode += '\n'+4*' '
            
            drumcount = 1
            for form_main in main_list:
                if form_main['type']!='maindrum': continue
                syncode += 'else if(Bsyn == -' + str(drumcount) + '){\n' + 6*' ' + 's = '
                for term in form_main['terms']:
                    syncode += instance(term) + (newlineplus if term != form_main['terms'][-1] else ';')
                syncode += '}\n' + 4*' '
                drumcount += 1

        syncode = syncode.replace('_TIME','t').replace('_PROG','_t').replace('_BPROG','Bprog').replace('e+00','')

    for r in (f for f in form_list if f['type']=='random'):
        print('RANDOM', r['ID'], '=', r['value'])

    print("\nBUILD SYN CODE:\n", 4*' '+syncode, sep="")

    filter_list = [f for f in form_list if f['type']=='filter']
    filtercode = '' 
    for form in filter_list:
        ff = open("framework."+form['shape']+"template")
        ffcode = ff.read()
        ff.close()
        filtercode += ffcode.replace('TEMPLATE',form['ID']).replace('INSTANCE',instance(form['source'])).replace('vel*','').replace('_PROG','_TIME') \
                            .replace('_BPROG','Bprog').replace('Bprog','_TIME*SPB')

    #print("\nBUILD FILTER CODE:\n", filtercode, sep="")

    return syncode, filtercode


def arg_required(cmd, arg):
    arg0 = arg[0].lower()  
    req = 3

    if cmd == 'osc' or cmd == 'lfo':
        req += 1
        if arg0 == 'squ' or arg0 == 'psq' or arg0 == 'fract': req += 2
        elif arg0 == 'macesq': req += 10
        
    elif cmd == 'drum':
        if arg0 == 'kick': req += 10
        elif arg0 == 'kick2': req += 17
        elif arg0 == 'snare': req += 13
        elif arg0 == 'fmnoise': req += 5
        elif arg0 == 'bitexplosion': req += 7

    elif cmd == 'env':
        if arg0 == 'adsr' or arg0 == 'adsrexp': req += 4
        elif arg0 == 'ahd': req += 3
        elif arg0 == 'doubleslope': req += 3
        elif arg0 == 'ss' or arg0 == 'ssdrop': req += 1
        elif arg0 == 'expdecay': req += 1
        elif arg0 == 'expdecayrepeat': req += 2
        
    elif cmd == 'form':
        req += 2
        if arg0 == 'mix': req -= 1
        elif arg0 == 'chorus': req += 3
        elif arg0 == 'delay': req += 2
        elif arg0 == 'waveshape': req += 5
        
    elif cmd == 'filter':
        req += 1
        if arg0 == 'resolp' or arg0 == 'resohp' or arg0 == 'allpass': req += 2
        elif arg0 == 'comb': req += 4
        elif arg0 == 'reverb': req += 8
        
    elif cmd == 'random':
        req += 1

    elif cmd == 'gac':
        req += 7
    
    return req

if __name__ == '__main__':
    synatize()
