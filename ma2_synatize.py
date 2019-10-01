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

inquotes = lambda f: len(f) > 2 and f[0] == '"' and f[-1] == '"'
split_if_not_quoted = lambda string, delimiter: string.split(delimiter) if not inquotes(string) else [string]

newlineindent = '\n' + 4*' '
newlineplus = '\n' + 6*' ' + '+'

def synatize(syn_file = 'default.syn', stored_randoms = [], reshuffle_randoms = False):

    # reserved names you cannot name a form after ~ f,t are essential, and maybe we want to use the other
    # time              time elapsed globally
    # _t                time elapsed since beginning of note
    # B                 beats elapsed since beginning of module
    # BT                beats elapsed globally
    # Bprog             beats elapsed since beginning of note
    # Bproc             elapsed percent of note
    var_list = ['f', 'time', 'time2', '_t', '_t2', 'B', 'BT', 'vel', 'Bsyn', 'Bproc', 'Bprog', 'L', 'tL', 'SPB', 'BPS', 'BPM', 'iSampleRate', 'Tsample', 'rel', 'aux', 'note', 'slide']

    form_list = [{'id': var, 'type': 'uniform'} for var in var_list]
    main_list = []
    param_list = []

    stored_random_values = {r['id']: r['value'] for r in stored_randoms}

    print('PARSING', './' + syn_file)

    with open(syn_file, 'r') as template:
        lines = template.readlines()

    # parse lines -- # are comments, ! is a EOF character
    for l in lines:
        if l=='\n' or l[0]=='#': continue
        elif l[0]=='!': break

        line = sub(' *, *',',',sub(' +',' ',sub(' *= *','=',l))).split()
        cmd = line[0].lower()
        cid = line[1]
        arg = []
        i = 2
        while i < len(line):
            a = line[i]
            while a.count('"') % 2 > 0:
                i += 1
                a += ' ' + line[i]
            arg.append(a)
            i += 1

        # some convenience parsing...
        form = {'id': cid, 'type': cmd, 'mode': ''}
        for a in arg[:]:
            if a[0] == '!':
                arg.remove(a)
                continue

            if "=" in a:
                key = a.split("=")[0].lower()
                val = "=".join(a.split("=")[1:])
                form.update({key : val})
                arg.remove(a)

            elif cmd == 'form' and a == arg[:][0]: #minor convenience: don't need op= in forms
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
                if not inquotes(form['src']):
                    form['src'] = sub('(?<![*+])-','+-',form['src']).replace('+',',')
            except KeyError:
                print('PARSING - ERROR IN LINE (src not given)\n', l)
                quit()

        if cmd == 'random': # TODO: 'tag' functionality not accessible yet - idea is: if tag is set, then only reshuffle if the tag is in the taglist
            if form['id'] in stored_random_values and not reshuffle_randoms:
                form['value'] = stored_random_values[form['id']]
            else:
                form['value'] = round(float(form['min']) + (float(form['max'])-float(form['min'])) * random(),int(form['digits']))
                print('RANDOM CHOICE:', form['id'], 'in', '['+str(form['min'])+'..'+str(form['max'])+']', '-->', str(form['value']))
                stored_randoms.append(form)

            stored_random_values.update({form['id']: form['value']})

        if cmd == 'seg':
            if form['shape'] == 'linear' and form['to'] is not None:
                from_x = float(form['from'].split(',')[0])
                from_y = float(form['from'].split(',')[1])
                to_x = float(form['to'].split(',')[0])
                to_y = float(form['to'].split(',')[1])
                form['scale'] = GLfloat(round((to_y-from_y)/(to_x-from_x), 5))
                form['offset'] = GLfloat(from_x)
                form['shift'] = GLfloat(from_y)

        for r in requirements:
            try:
                assert r in form
            except AssertionError:
                print('PARSING - ERROR! IN LINE\n', l, '\n... YOU NEED TO DEFINE:', r, 'and generally', requirements)
                quit()

        for key in form.keys():
            if key not in defaults.keys() and key not in requirements and key != 'value':
                print('PARSING - ERROR: ', key+'='+str(form[key]), 'IN FORM', form, '- supports', list(defaults.keys()))
                quit()

        if cid in [f['id'] for f in form_list if f['id'] != 'include']:
            print('PARSING - ERROR! ID \"' + cid + '\" already taken.')
            quit()

        if cmd == 'main' or cmd == 'maindrum':
            main_list.append(form)
        else:
            form_list.append(form)

        if cmd == 'param':
            if form['id'] == 'include':
                pass
            else:
                segments = form['segments'].split(',')
                if len(segments) % 3 != 0:
                    print('PARSING - ERROR! SEGMENTS OF PARAM HAVE TO BE IN STRUCTURE <Segment>,<Start>,<End>,... AND THUS A MULTIPLE OF THREE: ', form)
                    quit()
                form.update({'segments': segments, 'n_segments': int(len(segments) / 3)})

            param_list.append(form)


    drum_list = [d['id'] for d in main_list if d['type']=='maindrum']

    for stored_random in stored_randoms:
        stored_random['value'] = stored_random_values[stored_random['id']]

    return form_list, main_list, drum_list, stored_randoms, param_list


def synatize_build(form_list, main_list, param_list, actually_used_synths = None, actually_used_drums = None):

    def instance(ID, mod={}, force_int = False):
        _return = ''
        form = next((f for f in form_list if f['id']==ID), None)

        try:
            if mod:
                form = form.copy()
                form.update(mod)

            if inquotes(ID):
                return '('+ID[1:-1]+')'

            elif '+' in ID:
                IDsum = ID.split('+')
                sum = ''
                for sumID in IDsum:
                    sum += instance(sumID) + '+'
                return sum[:-1]

            elif '*' in ID:
                IDproduct = ID.split('*')
                product = ''
                for factorID in IDproduct:
                    product += instance(factorID) + '*'
                return product[:-1]

            elif not form:
                if force_int:
                    return str(int(float(ID)))
                else:
                    return GLstr(ID).replace('--','+')

            elif form['type']=='uniform':
                if form['id']=='note':
                    return 'note_pitch(_note)'
                else:
                    return ID

            elif form['type']=='const' or form['type']=='random':
                return GLstr(form['value']).replace('"','')

            elif form['type']=='form':
                if form['op'] == 'mix':
                    return '(' + '+'.join([instance(f) for f in form['src'].split(',')]) + ')'
                elif form['op'] == 'define': # actually pretty similar to mix, but I keep it.
                    return instance(form['src'])
                elif form['op'] == 'detune':
                    detuned_instances = '+'.join(instance(form['src'],{'freq':instance(amt)+'*'+param(form['src'],'freq')}) for amt in form['factor'].split(','))
                    return 's_atan(' + instance(form['src']) + '+' + detuned_instances + ')'
                elif form['op'] == 'pitchshift':
                    return instance(form['src'],{'freq':'{:.4f}'.format(pow(2,float(form['steps'])/12)) + '*' + param(form['src'],'freq')})
                elif form['op'] == 'quantize':
                    return instance(form['src']).replace('_TIME','floor('+instance(form['bits']) + '*_TIME+.5)/' + instance(form['bits'])) \
                                                   .replace('_PROG','floor('+instance(form['bits']) + '*_PROG+.5)/' + instance(form['bits']))
                                                   # TODO: replace these with calls to lofi(_TIME) / lofi(_PROG). don't wanna test these right now, though.
                elif form['op'] == 'overdrive':
                    return 'clip(' + instance(form['gain']) + '*' + instance(form['src']) + ')'
                elif form['op'] == 'chorus':
                    return '(' + newlineplus.join([instance(form['src']).replace('_PROG','(_PROG-'+'{:.1e}'.format(i*float(form['step']))+'*(1.+'+instance(form['intensity'])
                        +'*_sin('+instance(form['rate'])+'*_PROG)))') for i in range(int(form['number']))]) + ')'
                elif form['op'] == 'delay':
                    if 'time' in form['mode']:
                        return '(' + newlineplus.join(['{:.1e}'.format(pow(float(form['gain']),i)) + '*' + \
                                    instance(form['src']).replace('_BPROG','(_BPROG-BPS*'+'{:.3e}'.format(i*float(form['delay']))+')') \
                                                         .replace('_PROG','(_PROG-'+'{:.3e}'.format(i*float(form['delay']))+')') \
                                                            for i in range(1+int(form['number']))]) + ')'
                    else:
                        return '(' + newlineplus.join(['{:.1e}'.format(pow(float(form['gain']),i)) + '*' + \
                                    instance(form['src']).replace('_BPROG','(_BPROG-'+'{:.3e}'.format(i*float(form['delay']))+')') \
                                                         .replace('_PROG','(_PROG-SPB*'+'{:.3e}'.format(i*float(form['delay']))+')') \
                                                            for i in range(1+int(form['number']))]) + ')'
                elif form['op'] == 'timeshift':
                    pass # TODO: implement this (just a static shift in time)
                elif form['op'] == 'waveshape':
                    return 'waveshape(' + instance(form['src']) + ',' + ','.join(instance(form[p]) for p in ['amount','a','b','c','d','e']) + ')'
                elif form['op'] == 'sinshape':
                    return 'sinshape(' + instance(form['src']) + ',' + ','.join(instance(form[p]) for p in ['amount','parts']) + ')'
                elif form['op'] == 'saturate':
                    if 'crazy' in form['mode']:
                        return 's_crzy('+instance(form['gain']) + '*' + instance(form['src']) + ')'
                    else:
                        return 's_atan('+instance(form['gain']) + '*' + instance(form['src']) + ')'
                elif form['op'] == 'lofi':
                    return 'floor('+instance(form['bits'])+'*'+instance(form['src'])+'+.5)*'+'{:.1e}'.format(1/float(form['bits']))
                elif form['op'] == 'modsync':
                    return instance(form['src']).replace('_TIME','mod(_TIME, 1./(' + instance(form['freq']) + '))') \
                                                   .replace('_PROG','mod(_PROG, 1./(' + instance(form['freq']) + '))')
                elif form['op'] == 'timescale':
                    # TODO: have to think about it, but for now, only shift the
                    map_string = '{}'
                    if form['scale'] != '1':
                        map_string = instance(form['scale']) + '*' + map_string
                    if form['shift'] != '0':
                        map_string = '(' + map_string + '+' + instance(form['shift']) + ')'
                    return instance(form['src']).replace('_TIME', map_string.format('_TIME')).replace('_PROG', map_string.format('_PROG'))
                else:
                    return '0.'

            elif form['type'] == 'osc' or form['type'] == 'lfo':

                    if form['type'] == 'osc':
                        phi = instance(form['freq']) + '*_PROG'

                    elif form['type'] == 'lfo':
                        tvar = '*_BPROG' if 'global' not in form['mode'] else '*_BEAT'
                        if 'module' in form['mode']:
                            tvar = '*_BMODPROG'
                        elif 'time' in form['mode']:
                            tvar = '*_PROG' if 'global' not in form['mode'] else '*_TIME'

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
                                             + ','.join(instance(form[p]) for p in ['mix', 'cutoff', 'q', 'res', 'resq', 'detune', 'pw', 'lowcut'])+ ',' + keyF + ')'

                    elif form['shape'] == 'badd':
                        _return ='BADD(_PROG,' + ','.join(instance(form[p]) for p in ['freq', 'phase', 'mix', 'amp', 'peak', 'sigma', 'q', 'ncut', 'detune', 'pw']) + ')'

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

                    elif form['shape'] == 'lpnoise':
                        _return = 'lpnoise(_PROG + ' + instance(form['phase']) + ',' + instance(form['freq']) + ')'

                    elif form['shape'] == 'noise':
                        _return = 'pseudorandom(' + instance(form['freq']) + '*_PROG + ' + instance(form['phase']) + ')'

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

                        freq_env = '('+instance(form['freq_start'])+'+('+instance(form['freq_end'])+'-'+instance(form['freq_start'])+')*smstep(-'+instance(form['freq_decay'])+', 0.,-_PROG))'
                        amp_env = 'smstep(0.,'+instance(form['attack'])+',_PROG)*smstep('+instance(form['hold'])+'+'+instance(form['decay'])+','+instance(form['decay'])+',_PROG)'

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

                        freq_env = '('+freq_2+'+('+freq_0+'-'+freq_1+')*(1.-smstep(0.,'+fdec01+',_PROG))+('+freq_1+'-'+freq_2+')*(1.-smstep('+fdec01+','+fdec01+'+'+fdec12+',_PROG)))'
                        return '(clip((1.+'+overdr+')*(_tri(_PROG*'+freq_env+')*(1.-smstep('+fdec01+'+'+fdec12+','+envrel+'+'+fdec01+'+'+fdec12+',_PROG))) + '+ns_amt+'*pseudorandom(_PROG)*doubleslope(_PROG,'+ns_att+','+ns_dec+','+ns_sus+'))*doubleslope(_PROG,0.,'+envdec+','+envsus+'))'

                    elif form['shape'] == 'fmnoise':
                        env_attack = instance(form['attack'])
                        env_decay = instance(form['decay'])
                        env_sustain = instance(form['sustain'])
                        timbre1 = instance(form['timbre1'])
                        timbre2 = instance(form['timbre2'])
                        return 'fract(sin(_PROG*100.*'+timbre1+')*50000.*'+timbre2+')*doubleslope(_PROG,'+env_attack+','+env_decay+','+env_sustain+')'

                    elif form['shape'] == 'bitexplosion':
                        inst_nvar = instance(form['nvar'], force_int = True)
                        return 'bitexplosion(_PROG, _BPROG, ' + inst_nvar + ',' + ','.join(instance(form[p]) for p in ['freqvar', 'twostepvar', 'var1', 'var2', 'var3', 'decay']) + ')'

                    elif form['shape'] == 'protokick':
                        freq_0 = instance(form['freq0'])
                        freq_1 = instance(form['freq1'])
                        fdec = instance(form['freqdecay'])
                        return 'protokick(_PROG,' + ','.join(instance(form[p]) for p in ['freq0', 'freq1', 'freqdecay', 'hold', 'decay', 'drive', 'detune',\
                                                                                         'rev_amount', 'rev_hold', 'rev_decay', 'rev_drive']) + ')'

                    elif form['shape'] == 'protokickass':
                        phase = 'drop_phase(_PROG,' + ','.join(instance(form[p]) for p in ['freqdecay', 'freq0', 'freq1']) + ')'
                        return '(clamp(' + instance(form['drive']) + '*_tri(' + phase + '),-1.,1.)*(1.-smstep(-1e-3,0.,_PROG-'+instance(form['decay'])+'))'\
                         + '+' + instance(form['rev1_amt']) +'*clamp(' + instance(form['rev1_drive']) + '*_tri('+phase+'+'+ instance(form['rev1_amt'])\
                         + '*lpnoise(_PROG,' + instance(form['rev1_tone']) + ')),-1.,1.)*exp(-' + instance(form['rev1_exp']) + '*_PROG)'\
                         + '+' + instance(form['noise_amt']) + '*lpnoise(_PROG,' + instance(form['noise_tone']) + ')*(1.-smstep(0.,'\
                         + instance(form['noise_decay']) + ',_PROG-' + instance(form['noise_hold']) + '))'\
                         + '+' + instance(form['rev2_amt']) + '*lpnoise(_PROG,' + instance(form['rev2_tone']) + ')*exp(-_PROG*' + instance(form['rev2_exp']) + ')'\
                         + '+' + instance(form['rev3_amt']) + '*lpnoise(_PROG,' + instance(form['rev3_tone']) + ')*exp(-_PROG*' + instance(form['rev3_exp']) + '))'\
                         + '*smstep(0.,' + instance(form['attack']) + ',_PROG)'

                    elif form['shape'] == 'protosnare':
                        return instance(form['noise_amp']) + '*(' + instance(form['noise1_amount']) + '*lpnoise(_PROG,' + instance(form['noise1_freq']) + ')'\
                            + '+' + instance(form['noise2_amount']) + '*lpnoise(_PROG,' + instance(form['noise2_freq']) + ')'\
                            + '+' + instance(form['noise3_amount']) + '*lpnoise(_PROG,' + instance(form['noise3_freq']) + '))'\
                            + '*(smstep(0.,'+instance(form['attack'])+',_PROG)-smstep(0.,'+instance(form['release'])+',_PROG-'+instance(form['decay'])+'))'\
                            + ' + _sin(drop_phase(_PROG,'+','.join(instance(form[p]) for p in ['freqdecay','freq0','freq1'])+'))'\
                            + '*exp(-_PROG*' + instance(form['tone_decayexp'])+')*' + instance(form['tone_amp'])\
                            + '+ _sin(drop_phase(_PROG*' + instance(form['fmtone_freq'])+','+','.join(instance(form[p]) for p in ['freqdecay','freq0','freq1'])+'))'\
                            + '*exp(-_PROG*' + instance(form['fmtone_decayexp'])+')*' + instance(form['fmtone_amp'])

                    elif form['shape'] == 'protoshake':
                        return instance(form['amp']) + '*lpnoise(_PROG, 1.+' + instance(form['timbre']) + '*_PROG)'\
                            + '*(smstep(0.,1e-3,_PROG)-smstep(0.,' + instance(form['release']) + ',_PROG-' + instance(form['decay']) + '))'

                    elif form['shape'] == 'protoride':
                        base_freq = instance(form['base_freq'])
                        base_pw = instance(form['base_pw']) + '+' + instance(form['vibe_pw']) + '*cos(' + instance(form['vibe_freq']) + ')'
                        mod_freq = instance(form['mod_freq'])
                        mod_pw = instance(form['mod_pw'])
                        noise = instance(form['noise_amt']) + '*lpnoise(_PROG,' + instance(form['noise_freq']) + ')'
                        env_att = instance(form['env_attack'])
                        env_dec = instance(form['env_decay'])
                        base_template = '_sq_('+base_freq+'*_PROG*_sq_('+mod_freq+'*_PROG+'+noise +','+mod_pw+'),'+base_pw+')'
                        return base_template + '*(_PROG <= ' + env_att + ' ? _PROG/' + env_att + ' : exp(-(_PROG-' + env_att + ')/' + env_dec + '))'

                    elif form['shape'] == 'protocrash':
                        base_freq = instance(form['base_freq'])
                        base_pw = instance(form['base_pw']) + '+' + instance(form['vibe_pw']) + '*cos(' + instance(form['vibe_freq']) + ')'
                        mod_freq = instance(form['mod_freq'])
                        mod_pw = instance(form['mod_pw'])
                        noise = instance(form['noise_amt']) + '*lpnoise(_PROG,' + instance(form['noise_freq']) + ')'
                        env_att = instance(form['env_attack'])
                        env_dec = instance(form['env_decay'])
                        comb_delay = instance(form['comb_delay'])
                        base_template = '_sq_('+base_freq+'*_PROG*_sq_('+mod_freq+'*_PROG+'+noise +','+mod_pw+'),'+base_pw+')'
                        return '.33*(' + base_template + '+' \
                                        + base_template.replace('_PROG','(_PROG+'+comb_delay+')') + '+' \
                                        + base_template.replace('_PROG','(_PROG-'+comb_delay+')') + ')' \
                                        + '*(_PROG <= ' + env_att + ' ? _PROG/' + env_att + ' : exp(-(_PROG-' + env_att + ')/' + env_dec + '))'

                    elif form['shape'] == 'metalnoise':
                        tvar = '_PROG'
                        if form['modfreq'] != '0':
                            tvar = f"mod({tvar},1./({instace(form['modfreq'])})"
                        if form['timescale'] != '1':
                            tvar = instance(form['timescale']) + '*' + tvar
                        return f"metalnoise({tvar}, {instance(form['factor1'])}, {instance(form['factor2'])})"


            elif form['type'] == 'env' or form['type'] == 'seg':
                tvar = '_BPROG'
                Lvar = 'L'

                if 'module' in form['mode']:
                    tvar = '_BMODPROG'
                elif 'time' in form['mode']:
                    tvar = '_PROG'
                    Lvar = 'tL'
                elif 'relative' in form['mode']:
                    tvar = 'Bproc'
                    Lvar = '1.'

                if form['type'] == 'seg':
                    tvar = '_BEAT'
                    Lvar = 'L'

                if form['offset'] != '0':
                    tvar = tvar + '-' + instance(form['offset'])

                if form['shape'] == 'ahdsr' or form['shape'] == 'adsr':
                    _return = 'env_AHDSR('+tvar+','+Lvar+','+','.join(instance(form[p]) for p in ['attack', 'hold', 'decay', 'sustain', 'release'])+')'
                elif form['shape'] == 'ahdsrexp' or form['shape'] == 'adsrexp':
                    _return = 'env_AHDSRexp('+tvar+','+Lvar+','+','.join(instance(form[p]) for p in ['attack', 'hold', 'decay', 'sustain', 'release'])+')'
                elif form['shape'] == 'limitlength':
                    _return = 'env_limit_length('+tvar+','+instance(form['factor']) + '*(' + instance(form['length'])+'),'+instance(form['release'])+')'
                elif form['shape'] == 'doubleslope':
                    _return = 'doubleslope('+tvar+','+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+')'
                elif form['shape'] == 'ss':
                    _return = 'smstep(0.,'+instance(form['attack'])+','+tvar+')'
                elif form['shape'] == 'ssdrop':
                    _return = '(1.-smstep(0.,'+instance(form['decay'])+','+tvar+'))'
                elif form['shape'] == 'expdecay':
                    thold = tvar if form['hold'] == '0' else 'max(_PROG-'+form['hold']+',0.)'
                    _return = f"exp(-{instance(form['exponent'])}*{thold})"
                elif form['shape'] == 'expdecayrepeat':
                    _return = 'exp(-'+instance(form['exponent'])+'*mod(_BPROG,'+instance(form['beats'])+'))'
                elif form['shape'] == 'stepexpdecay':
                    _return = f"clamp(1.+({instance(form['hold'])}-{tvar})/({instance(form['decay'])}),exp(-{instance(form['exponent'])}*{tvar}),1.)"
                elif form['shape'] == 'antivelattack':
                    try:
                        attack = str(round(float(form['attack'])/(float(form['velmax'])-float(form['velmin'])+1e-3), 5)) + '*('+ GLstr(form['velmax']) + '-' + instance(form['vel']) + '+1e-3)'
                        _return = 'smstep(0.,'+instance(attack)+','+tvar+')'
                    except:
                        attack = instance(form['attack']) + '*('+instance(form['velmax']) + '-' + instance(form['vel']) + '+1e-3)/(' + instance(form['velmax']) + '-' + instance(form['velmin']) + '+1e-3)'
                        _return = 'smstep(0.,'+attack+','+tvar+')'

                elif form['shape'] == 'generic':
                    _return = instance(form['src']).replace('_BPROG', '(_BEAT-' + instance(form['offset']) + ')') # hm. might I do this better?
                elif form['shape'] == 'linear':
                    _return = tvar
                elif form['shape'] == 'param':
                    _return = form['id'] + '(' + tvar + ')'

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

            elif form['type'] == 'param':
                return form['id'] + '(_BEAT)'

            else:
                print("PARSING - ERROR! THIS FORM TYPE DOES NOT EXIST: "+form['type'], form, sep='\n')
                quit()

        except:
            print("PARSING - UNEXPECTED UNEXPECTEDNESS (which was not expected) - IN FORM", form if form else str(ID), '', sep='\n')
            quit()

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

    synatized_forms = []

    if not main_list:
        print("BUILDING MAIN LIST - WARNING: no main form defined! will return empty sound")
        syncode = "amaysynL = amaysynR = 0.; // some annoying weirdo forgot to define the main form!"

    else:
        #print('BUILDING MAIN LIST:', main_list, actually_used_synths)
        syncount = 1
        syncode = 'if(syn == 0){amaysynL = _sin(f*_t); amaysynR = _sin(f*_t2);}\n' + 20*' '
        for form_main in main_list:
            if form_main['type']!='main': continue
            sources = split_if_not_quoted(form_main['src'], ',')
            if actually_used_synths is None or form_main['id'] in actually_used_synths:
                synatized_src = ''
                syncodeL = ''
                for term in sources:
                    instance_src = instance(term)
                    synatized_src += instance_src + ('+' if term != sources[-1] else '')
                    syncodeL += instance_src + (newlineplus if term != sources[-1] else ';')
                synatized_forms.append({**form_main, 'src': '"' + sub(' *\n*','',synatized_src) + '"'})

                extracode = ''
                if form_main['stereodelay'] != 'default':
                    extracode = f"time2 = time-{form_main['stereodelay']}; _t2 = _t-{form_main['stereodelay']};"
                syncodeR = syncodeL.replace('_TIME','time2').replace('_PROG','_t2')
                syncodeL = syncodeL.replace('_TIME','time').replace('_PROG','_t')
                syncode += 'else if(syn == ' + str(syncount) + '){\n' + 24*' ' + extracode + '\n' + 24*' ' \
                        +  'amaysynL = ' + syncodeL + '\n' + 24*' ' + 'amaysynR = ' + syncodeR
                if 'relpower' in form_main and form_main['relpower'] != '1':
                    syncode += '\nenv = theta(Bprog)*pow(1.-smstep(Boff-rel, Boff, B),'+form_main['relpower']+');'
                syncode += '\n' + 20*' ' + '}\n' + 20*' '
            syncount += 1
        syncode = syncode.replace('_TIME','time').replace('_PROG','_t').replace('_BPROG','Bprog').replace('_BEAT','BT').replace('_BMODPROG','B')

        drumcount = 1
        drumsyncode = ''
        for form_main in main_list:
            if form_main['type']!='maindrum': continue
            sourcesL = split_if_not_quoted(form_main['src'], ',')
            sourcesR = sourcesL if form_main['srcr'] == '' else split_if_not_quoted(form_main['srcr'], ',')
            if actually_used_drums is None or drumcount in actually_used_drums:
                synatized_srcL = ''
                synatized_srcR =  ''
                drumsyncodeL = 'vel*'
                drumsyncodeR = 'vel*'
                for term in sourcesL:
                    instance_src = instance(term)
                    synatized_srcL += instance_src + ('+' if term != sourcesL[-1] else '')
                    drumsyncodeL += instance_src + (newlineplus if term != sourcesL[-1] else ';')
                for term in sourcesR:
                    instance_src = instance(term)
                    synatized_srcR += instance_src + ('+' if term != sourcesR[-1] else '')
                    drumsyncodeR += instance_src + (newlineplus if term != sourcesR[-1] else ';')

                synatized_forms.append({**form_main, 'src': '"' + sub(' *\n*','',synatized_srcL) + '"', 'srcr': '"' + sub(' *\n*','',synatized_srcR) + '"'})

                drumsyncodeR = drumsyncodeR.replace('_TIME','time2').replace('_PROG','_t2' if form_main['srcr'] == '' else '_t')
                drumsyncodeL = drumsyncodeL.replace('_TIME','time').replace('_PROG','_t')
                drumsyncode += 'else if(drum == ' + str(drumcount) + '){\n' + 24*' ' \
                            +  'amaydrumL = ' + drumsyncodeL + '\n' + 24*' ' + 'amaydrumR = ' + drumsyncodeR \
                            +  '\n' + 20*' ' + '}\n' + 20*' '
            drumcount += 1
        drumsyncode = drumsyncode.replace('_TIME','time').replace('_PROG','_t').replace('_BPROG','Bprog').replace('_BEAT','BT').replace('_BMODPROG','B')

    paramcode = ''
    param_normal, param_includes = [], []
    for par in param_list:
        param_includes.append(par) if par['id'] == 'include' else param_normal.append(par)

    for par in param_normal:
        paramcode += 'float ' + par['id'] + '(float _BEAT)\n{' + newlineindent + 'return _BEAT<0 ? 0. : '
        for seg in range(par['n_segments']):
            seg_code = instance(par['segments'][3*seg]).replace('_BPROG', '_BEAT').replace('_BMODPROG', '_BEAT')
            seg_start = par['segments'][3*seg+1]
            seg_end = par['segments'][3*seg+2]
            paramcode += '(_BEAT>=' + seg_start + ' && _BEAT<' + seg_end + ') ? ' + seg_code.replace('_BEAT','(_BEAT-' + GLstr(seg_start) + ')') + ' : '
        paramcode += instance(par['default']) + ';' + '\n}\n'

    for par in param_includes:
        paramcode += par['src'].replace('"', '').replace('} ', '}\n')


    filter_list = [f for f in form_list if f['type']=='filter']
    filtercode = ''
    for form in filter_list:
        ff = open("template."+form['shape'])
        ffcode = ff.read()
        ff.close()
        filtercode += ffcode.replace('TEMPLATE',form['id']).replace('INSTANCE',instance(form['src']))\
                            .replace('_PROG','_TIME').replace('_BPROG','Bprog').replace('Bprog','_TIME*SPB')
        # think again... do we really prefer _TIME over _PROG?? (what is with slides?)

    return syncode, drumsyncode, paramcode, filtercode, synatized_forms


if __name__ == '__main__':
    print(synatize())
