#import math
from random import random
from ma2_synatize_defaults import set_remaining_defaults
from re import sub

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f>=1 or f<0 or abs(f)<1e-4 else 1:].replace('-0.','-.')

def GLstr(s):
    try:
        f = float(s)
    except ValueError:
        return s
    else:
        return GLfloat(f)

#reserved keywords you cannot name a form after ~ f,t are essential, and maybe we want to use the other
_f = {'id':'f', 'type':'uniform'}
_t = {'id':'t', 'type':'uniform'}
_t_ = {'id':'_t', 'type':'uniform'}
_B = {'id':'B', 'type':'uniform'}
_vel = {'id':'vel', 'type':'uniform'}
_Bsyn = {'id':'Bsyn', 'type':'uniform'}
_Bproc = {'id':'Bproc', 'type':'uniform'}
_Bprog = {'id':'Bprog', 'type':'uniform'}
_L = {'id':'L', 'type':'uniform'}
_tL = {'id':'tL', 'type':'uniform'}
_SPB = {'id':'SPB', 'type':'uniform'}
_BPS = {'id':'BPS', 'type':'uniform'}
_BPM = {'id':'BPM', 'type':'uniform'}
_note = {'id':'note', 'type':'uniform'}
_Fsample = {'id':'Fsample', 'type':'uniform'}
_Tsample = {'id':'Tsample', 'type':'uniform'}
_rel = {'id':'rel', 'type':'uniform'}

newlineplus = '\n' + 6*' ' + '+'

def synatize(syn_file = 'test.syn'):

    syncode = ""

    form_list = [_f, _t, _t_, _B, _vel, _Bsyn, _Bproc, _Bprog, _L, _tL, _SPB, _BPS, _BPM, _note, _Fsample, _Tsample, _rel]
    main_list = []
   
    print('PARSING', './' + syn_file)
   
    with open(syn_file,"r") as template:
        lines = template.readlines()
        
    # parse lines -- # are comments, ! is a EOF character
    for l in lines:
        if l=='\n' or l[0]=='#': continue
        elif l[0]=='!': break
    
        line = sub(' *, *',',',sub(' +',' ',sub(' *= *','=',l))).split()
        cmd = line[0].lower()
        cid = line[1]
        arg = line[2:]
        
        # some convenience parsing...
        form = {'id':cid, 'type':cmd, 'mode':''}
        for a in arg[:]:
            if a[0] == '!':
                arg.remove(a)
                continue
            
            if "=" in a:
                key = a.split("=")[0].lower()
                val = a.split("=")[1]
                form.update({key : val})
                arg.remove(a)
                
            elif cmd == 'form' and a == arg[:][0]: #minor exception: don't need op= in forms 
                form.update({'op': a})
                arg.remove(a)
                
            elif cmd == 'const' and 'value' not in form:
                form.update({'value': a})

            elif cmd == 'random' and a == 'store':
                form.update({'store': True})
        
        form, defaults, requirements = set_remaining_defaults(cid, cmd, form)

        # some special cases

        form['mode'] = form['mode'].split(',') if form['mode'] != '' else []
        
        if cmd == 'main' or cmd == 'maindrum' or (cmd == 'form' and form['op'] == 'mix'):
            try:
                form['src'] = sub('(?<![*+])-','+-',form['src']).replace('+',',')        
            except KeyError:
                print('PARSING - ERROR IN LINE (src not given)\n', l)
                quit()

        if cmd == 'random':
            form['value'] = round(float(form['min']) + (float(form['max'])-float(form['min']))*random(),int(form['digits']))
        
        for r in requirements:
            try:
                assert r in form
            except AssertionError:
                print('PARSING - ERROR! IN LINE\n', l, '\n... YOU NEED TO DEFINE:', r, 'and generally', requirements)
                quit()
                
        for key in form.keys():
            if key not in defaults.keys() and key not in requirements and key != 'value':
                print('PARSING - WARNING: ', key+'='+str(form[key]), 'IN FORM', form, '- supports', list(defaults.keys()))
        
        if cid in [f['id'] for f in form_list]:
            print('PARSING - WARNING! ID \"' + cid + '\" already taken. Ignoring line.')
            continue

        if cmd == 'main' or cmd == 'maindrum':
            main_list.append(form)
        else:
            form_list.append(form)
        
    drum_list = [d['id'] for d in main_list if d['type']=='maindrum']

    return form_list, main_list, drum_list


def synatize_build(form_list, main_list, actually_used_synths = None, actually_used_drums = None):

    def instance(ID, mod={}, force_int = False):
        
        _return = ''

        form = next((f for f in form_list if f['id']==ID), None)
        
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
                return GLstr(form['value']).replace('"','')
            
            elif form['type']=='form':
                if form['op'] == 'mix':
                    return '(' + '+'.join([instance(f) for f in form['src'].split(',')]) + ')' 
                elif form['op'] == 'detune':
                    detuned_instances = '+'.join(instance(form['src'],{'freq':'(1.-' + instance(amt) + ')*'+param(form['src'],'freq')}) for amt in form['amount'].split(','))
                    return 's_atan(' + instance(form['src']) + '+' + detuned_instances + ')'
                elif form['op'] == 'pitchshift':
                    return instance(form['src'],{'freq':'{:.4f}'.format(pow(2,float(form['steps'])/12)) + '*' + param(form['src'],'freq')})
                elif form['op'] == 'quantize':
                    return instance(form['src']).replace('_TIME','floor('+instance(form['bits']) + '*_TIME+.5)/' + instance(form['bits'])) \
                                                   .replace('_PROG','floor('+instance(form['bits']) + '*_PROG+.5)/' + instance(form['bits']))
                elif form['op'] == 'overdrive':
                    return 'clip(' + instance(form['gain']) + '*' + instance(form['src']) + ')'
                elif form['op'] == 'chorus':
                    return '(' + newlineplus.join([instance(form['src']).replace('_PROG','(_PROG-'+'{:.1e}'.format(i*float(form['step']))+'*(1.+'+instance(form['intensity'])    +'*_sin('+instance(form['rate'])+'*_PROG)))') for i in range(int(form['number']))]) + ')'
                elif form['op'] == 'delay':
                    tvar = '_PROG' if not 'beat' in form['mode'] else '_BPROG'
                    return '(' + newlineplus.join(['{:.1e}'.format(pow(float(form['gain']),i)) + '*' + \
                                                   instance(form['src']).replace(tvar,'('+tvar+'-'+'{:.1e}'.format(i*float(form['delay']))+')') for i in range(int(form['number']))]) + ')'
                elif form['op'] == 'waveshape':
                    return 'supershape(' + instance(form['src']) + ',' + ','.join(instance(form[p]) for p in ['amount','a','b','c','d','e']) + ')'
                elif form['op'] == 'saturate':
                    if 'crazy' in form['mode']:
                        return 's_crzy('+instance(form['gain']) + '*' + instance(form['src']) + ')'
                    else:
                        return 's_atan('+instance(form['gain']) + '*' + instance(form['src']) + ')'
                elif form['op'] == 'lofi':
                    return 'floor('+instance(form['bits'])+'*'+instance(form['src'])+'+.5)*'+'{:.1e}'.format(1/float(form['bits']))
                else:
                    return '1.'

            elif form['type'] == 'osc' or form['type'] == 'lfo':

                    if form['type'] == 'osc':
                        phi = instance(form['freq']) + '*_TIME'

                    elif form['type'] == 'lfo':
                        tvar = '*Bprog' if 'global' not in form['mode'] else '*B'
                        if 'time' in form['mode']: tvar = '*_PROG' if 'global' not in form['mode'] else '*_TIME'
                            
                        phi = instance(form['freq']) + tvar
                        if form['shape'] == 'squ': form['shape'] = 'psq'
                        
                                    
                    if form['shape'] == 'sin':
                        if form['phase'] == '0':
                            _return = '_sin(' + phi + ')'
                        else:
                            _return = '_sin_(' + phi + ',' + instance(form['phase']) + ')'
          
                    elif form['shape'] == 'saw':
                        _return = '(2.*fract(' + phi + '+' + instance(form['phase']) + ')-1.)'

                    elif form['shape'] == 'squ':
                        if form['pw'] == '0':
                            _return = '_sq(' + phi + ')'
                        else:
                            _return = '_sq_(' + phi + ',' + instance(form['pw']) + ')'

                    elif form['shape'] == 'psq':
                        if form['pw'] == '0':
                            _return = '_psq(' + phi + ')'
                        else:
                            _return = '_psq_(' + phi + ',' + instance(form['pw']) + ')'

                    elif form['shape'] == 'tri':
                        _return = '_tri(' + phi + '+' + instance(form['phase']) + ')'

                    elif form['shape'] == 'madd':
                        keyF = '0' if not 'follow' in form['mode'] else '1'
                        inst_nmax = instance(str(int(float(form['nmax']))), force_int=True)
                        inst_ninc = instance(str(int(float(form['ninc']))), force_int=True)
                        _return ='MADD(_PROG,'+instance(form['freq']) + ',' + instance(form['phase']) + ',' + inst_nmax + ',' + inst_ninc + ',' \
                                             + ','.join(instance(form[p]) for p in ['mix', 'cutoff', 'q', 'res', 'resq', 'detune', 'pw'])+ ',' + keyF + ')'
                                         
                    elif form['shape'] == 'fract':
                        _return = 'fract(' + phi + '+' + instance(form['phase']) + ')'
                            
                    elif form['shape'] == 'fm':
                        pars = []    
                        for p in ['lv1', 'lv2', 'lv3', 'lv4', 'fr1', 'fr2', 'fr3', 'fr4', 'fb1', 'fb2', 'fb3', 'fb4', 'algo']:
                            if 'parscale' not in form or form['parscale'] == '1' or p[0:2] not in ['lv', 'fb']:
                                pars.append(instance(form[p]))
                                
                            else:
                                try:
                                    scale = instance('{:.3g}'.format(eval('1./'+form['parscale'])))
                                    pars.append(scale + '*' + instance(form[p]))
                                except:
                                    pars.append(instance(form[p]))
                                    print("QFM error: something stupid happens with parscale =", form['parscale'])
                            
                        _return = 'QFM(_PROG,' + instance(form['freq']) + ',' + instance(form['phase']) + ',' + ','.join(pars) + ')'
                    
                    #elif form['shape'] == 'guitar':
                    #        _return = 'karplusstrong(_PROG,'+instance(form['freq'])+')' # this doesn't work yet... sryboutthat

                    else:
                        print("PARSING - ERROR! THIS OSC/LFO SHAPE DOES NOT EXIST: "+form['shape'], form, sep='\n')
                        quit()
                        
                    if 'overdrive' in form and form['overdrive'] != '0':
                        _return = 'clip((1.+' + instance(form['overdrive']) + ')*' + _return + ')'
                        
                    if 'scale' in form and form['scale'] != '1':
                        _return = instance(form['scale']) + '*' + _return
                    
                    if 'shift' in form and form['shift'] != '0':
                        _return = '(' + instance(form['shift']) + '+(' + _return + '))'
                    
                    return _return

            elif form['type'] == 'drum':
                
                    if form['shape'] == 'kick' or form['shape'] == 'kick2':

                        freq_env = '('+instance(form['freq_start'])+'+('+instance(form['freq_end'])+'-'+instance(form['freq_start'])+')*smoothstep(-'+instance(form['freq_decay'])+', 0.,-_PROG))'
                        amp_env = 'smoothstep(0.,'+instance(form['attack'])+',_PROG)*smoothstep('+instance(form['hold'])+'+'+instance(form['decay'])+','+instance(form['decay'])+',_PROG)'

                        if form['shape'] == 'kick':
                            return 's_atan('+amp_env+'*(clip((1.+'+instance(form['overdrive'])+')*_tri('+freq_env+'*_PROG))+_sin(.5*'+freq_env+'*_PROG)))+'+instance(form['click_amp'])+'*step(_PROG,'+instance(form['click_delay'])+')*_sin(5000.*_PROG*'+instance(form['click_timbre'])+'*_saw(1000.*_PROG*'+instance(form['click_timbre'])+'))'
                        
                        elif form['shape'] == 'kick2':
                            sq_PHASE = instance(form['sq_phase'])
                            sq_NMAX = str(int(float(form['sq_nmax'])))
                            sq_MIX = instance(form['sq_mix'])
                            sq_INR = instance(form['sq_inr'])
                            sq_NDECAY = instance(form['sq_ndecay'])
                            sq_RES = instance(form['sq_res'])
                            sq_RESQ = instance(form['sq_resq'])
                            sq_DET = instance(form['sq_detune'])
                            return 's_atan('+amp_env+'*MADD(_PROG,'+freq_env+','+sq_PHASE+','+sq_NMAX+',1,'+sq_MIX+','+sq_INR+','+sq_NDECAY+','+sq_RES+','+sq_RESQ+','+sq_DET+',0.,1) + '+instance(form['click_amp'])+'*.5*step(_PROG,'+instance(form['click_delay'])+')*_sin(_PROG*1100.*'+instance(form['click_timbre'])+'*_saw(_PROG*800.*'+instance(form['click_timbre'])+')) + '+instance(form['click_amp'])+'*(1.-exp(-1000.*_PROG))*exp(-40.*_PROG)*_sin((400.-200.*_PROG)*_PROG*_sin(1.*'+freq_env+'*_PROG)))'
                    
                    elif form['shape'] == 'snare':
                        freq_0 = instance(form['freq0'])
                        freq_1 = instance(form['freq1'])
                        freq_2 = instance(form['freq2'])
                        fdec01 = instance(form['freqdecay0'])
                        fdec12 = instance(form['freqdecay1'])
                        envdec = instance(form['decay'])
                        envsus = instance(form['sustain'])
                        envrel = instance(form['release'])
                        ns_amt = instance(form['noise_amount'])
                        ns_att = instance(form['noise_attack'])
                        ns_dec = instance(form['noise_decay'])
                        ns_sus = instance(form['noise_sustain'])
                        overdr = instance(form['overdrive'])
                        
                        freq_env = '('+freq_2+'+('+freq_0+'-'+freq_1+')*smoothstep(-'+fdec01+',0.,-_PROG)+('+freq_1+'-'+freq_2+')*smoothstep(-'+fdec01+'-'+fdec12+',-'+fdec01+',-_PROG))'
                        return 'clip((1.+'+overdr+')*(_tri(_PROG*'+freq_env+')*smoothstep(-'+envrel+',-'+fdec01+'-'+fdec12+',-_PROG) + '+ns_amt+'*fract(sin(_PROG*90.)*4.5e4)*doubleslope(_PROG,'+ns_att+','+ns_dec+','+ns_sus+'),-1., 1.)*doubleslope(_PROG,0.,'+envdec+','+envsus+'))'
                        
                    elif form['shape'] == 'fmnoise':
                        env_attack = instance(form['attack'])
                        env_decay = instance(form['decay'])
                        env_sustain = instance(form['sustain'])
                        timbre1 = instance(form['timbre1'])
                        timbre2 = instance(form['timbre2'])
                        return 'fract(sin(_TIME*100.*'+timbre1+')*50000.*'+timbre2+')*doubleslope(_PROG,'+env_attack+','+env_decay+','+env_sustain+')'
                        
                    elif form['shape'] == 'bitexplosion':
                        inst_nvar = instance(form['nvar'], force_int = True) # was: str(int(form['par'][0]))
                        return 'bitexplosion(_TIME, _BPROG, ' + inst_nvar + ',' + ','.join(instance(form[p]) for p in ['freqvar', 'twostepvar', 'var1', 'var2', 'var3', 'decay']) + ')' 


            elif form['type']=='env':
                tvar = '_BPROG' if 'beat' in form['mode'] else '_PROG'
                Lvar = 'L' if 'beat' in form['mode'] else 'tL'
                if form['shape'] == 'ahdsr' or form['shape'] == 'adsr':
                    _return = 'env_AHDSR('+tvar+','+Lvar+','+','.join(instance(form[p]) for p in ['attack', 'hold', 'decay', 'sustain', 'release'])+')'
                elif form['shape'] == 'ahdsrexp' or form['shape'] == 'adsrexp':
                    _return = 'env_AHDSRexp('+tvar+','+Lvar+','+','.join(instance(form[p]) for p in ['attack', 'hold', 'decay', 'sustain', 'release'])+')'
                elif form['shape'] == 'doubleslope':
                    _return = 'doubleslope('+tvar+','+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+')'
                elif form['shape'] == 'ss':
                    _return = 'smoothstep(0.,'+instance(form['attack'])+','+tvar+')'
                elif form['shape'] == 'ssdrop':
                    _return = 'theta('+'_PROG'+')*(1.-smoothstep(0.,'+instance(form['decay'])+','+tvar+'))'
                elif form['shape'] == 'expdecay':
                    _return = 'theta('+'_BPROG'+')*exp(-'+instance(form['exponent'])+'*_BPROG)'
                elif form['shape'] == 'expdecayrepeat':
                    _return = 'theta('+'_BPROG'+')*exp(-'+instance(form['exponent'])+'*mod(_BPROG,'+instance(form['beats'])+'))'
                else:
                    print("PARSING - ERROR! THIS ENVELOPE SHAPE DOES NOT EXIST: "+form['shape'], form, sep='\n')
                    quit()

                if form['scale'] != '1':
                    _return = instance(form['scale']) + '*' + _return
                
                if form['shift'] != '0':
                    _return = '(' + instance(form['shift']) + '+(' + _return + '))'
                
                return _return


            elif form['type']=='gac':
                tvar = '_PROG' if 'global' not in form['mode'] else '_TIME'
                pars = ['offset', 'const', 'lin', 'quad', 'sin', 'sin_coeff', 'exp', 'exp_coeff']
                return 'GAC('+tvar+',' + ','.join([instance(form[p]) for p in pars]) + ')'

            elif form['type']=='filter':
                pars = []
                if form['shape'] in ['resolp', 'resohp']:
                    pars = ['cutoff', 'res']
                elif form['shape'] == 'allpass':
                    pars = ['gain', 'ndelay']
                elif form['shape'] in ['avglp', 'avghp']:
                    pars = ['n']
                elif form['shape'] == 'bandpass':
                    pars = ['center', 'bandwidth', 'n']
                elif form['shape'] == 'comb':
                    pars = ['iir_gain', 'iir_n', 'fir_gain', 'fir_n']
                elif form['shape'] == 'reverb':
                    pars = ['iir_gain', 'iir_delay1', 'iir_delay2', 'iir_delay3', 'iir_delay4', 'ap_gain', 'ap_delay1', 'ap_delay2']
                else:
                    print("PARSING - ERROR! THIS FILTER DOES NOT EXIST: " + form['shape'], form, sep='\n')
                    quit()

                return form['shape']+form['id']+'(_PROG,f,tL,vel,'+','.join([instance(form[p]) for p in pars])+')'

            else:
                print("PARSING - ERROR! THIS FORM TYPE DOES NOT EXIST: "+form['type'], form, sep='\n')
                quit()
        
        except:
            print("PARSING - UNEXPECTED UNEXPECTEDNESS (which was not expected) - IN FORM", form if form else str(ID), '', sep='\n')
            raise

    def param(ID, key):
        form = next((f for f in form_list if f['id']==ID), None)
        try:
            value = form[key]
        except KeyError:
            return ''
        except TypeError:
            return ''
        else:
            return value

    if not main_list:
        print("BUILDING MAIN LIST - WARNING: no main form defined! will return empty sound")
        syncode = "amaysynL = amaysynR = 0.; //some annoying weirdo forgot to define the main form!"

    else:
        #print('BUILDING MAIN LIST:', main_list, actually_used_synths)
        syncount = 1
        syncode = 'if(syn == 0){amaysynL = _sin(f*_t); amaysynR = _sin(f*_t2);}\n' + 20*' '
        for form_main in main_list:
            if form_main['type']!='main': continue
            sources = form_main['src'].split(',')
            if actually_used_synths is None or form_main['id'] in actually_used_synths:
                syncodeL = ''
                for term in sources:
                    syncodeL += instance(term) + (newlineplus if term != sources[-1] else ';')
                
                syncodeR = syncodeL.replace('(_TIME','time2').replace('_PROG','_t2')
                syncodeL = syncodeL.replace('_TIME','time').replace('_PROG','_t')

                syncode += 'else if(syn == ' + str(syncount) + '){\n' + 24*' ' \
                        +  'amaysynL = ' + syncodeL + '\n' + 24*' ' + 'amaysynR = ' + syncodeR 

                if 'relpower' in form_main and form_main['relpower'] != '1':
                    syncode += '\nenv = theta(Bprog)*pow(1.-smoothstep(Boff-rel, Boff, B),'+form_main['relpower']+');'

                syncode += '\n' + 20*' ' + '}\n' + 20*' '
            syncount += 1
        syncode = syncode.replace('_TIME','time').replace('_PROG','_t').replace('_BPROG','Bprog').replace('e+00','')

        drumcount = 1
        drumsyncode = ''
        for form_main in main_list:
            if form_main['type']!='maindrum': continue
            sources = form_main['src'].split(',')
            if actually_used_drums is None or drumcount in actually_used_drums:
                drumsyncodeL = ''
                if 'amp' in form_main and form_main['amp'] != '1': #in case you want e.g. velocity scaling for filtered drums... not pretty, but could work.
                    drumsyncodeL += instance(form['amp']) + '*'
                for term in sources:
                    drumsyncodeL += instance(term) + (newlineplus if term != sources[-1] else ';')
                
                drumsyncodeR = drumsyncodeL.replace('_TIME','time2').replace('_PROG','_t2')
                drumsyncodeL = drumsyncodeL.replace('_TIME','time').replace('_PROG','_t')

                drumsyncode += 'else if(drum == ' + str(drumcount) + '){\n' + 24*' ' \
                            +  'amaydrumL = ' + drumsyncodeL + '\n' + 24*' ' + 'amaydrumR = ' + drumsyncodeR \
                            +  '\n' + 20*' ' + '}\n' + 20*' '
            drumcount += 1
        drumsyncode = drumsyncode.replace('_TIME','time').replace('_PROG','_t').replace('_BPROG','Bprog').replace('e+00','')

    store_randoms = {}
    for r in (f for f in form_list if f['type']=='random'):
        if r['store']:
            store_randoms.update({r['id']: r['value']})
        print('RANDOM CHOICE:', r['id'], 'in', '['+str(r['min'])+'..'+str(r['max'])+']', '-->', str(r['value']))

    filter_list = [f for f in form_list if f['type']=='filter']
    filtercode = '' 
    for form in filter_list:
        ff = open("template."+form['shape'])
        ffcode = ff.read()
        ff.close()
        filtercode += ffcode.replace('TEMPLATE',form['id']).replace('INSTANCE',instance(form['src'])).replace('_PROG','_TIME').replace('_BPROG','Bprog').replace('Bprog','_TIME*SPB')

    return syncode, drumsyncode, filtercode, store_randoms


if __name__ == '__main__':
    synatize()
