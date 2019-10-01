# special cases: main, maindrum, const, mix

def set_remaining_defaults(cid, cmd, form):

    requirements = ['id', 'type', 'mode']
    defaults = {}

    if cmd in ['main', 'maindrum']:
        requirements.append('src')
        defaults.update({'release':'0', 'relpower':'1', 'slidetime':'.125', 'predraw': '0', 'stereodelay': 'default'})

        if cmd == 'maindrum':
            defaults.update({'srcr': ''})

    elif cmd == 'random':
        defaults.update({'min':'0', 'max':'1', 'digits':'3', 'store':False, 'tag':''})

    elif cmd == 'osc' or cmd == 'lfo':
        defaults.update({'shape':'sin', 'freq':'f', 'phase':'0', 'pw':'0', 'overdrive':'0', 'shift':'0', 'scale':'1'})

        if cmd == 'lfo':
            defaults.update({'freq':'1', 'shift':'0.5', 'scale':'0.5'})

        try:
            if form['shape'] == 'madd':
                defaults.update({'nmax':'128', 'ninc':'1', 'mix':'.5', 'cutoff':'1000', 'q':'10', 'res':'0', 'resq': '3', 'detune':'1e-3', 'lowcut': '0'})
                # TODO: calibrate q (and rename)
                # TODO: calibrate (resQ)
            elif form['shape'] == 'badd':
                defaults.update({'mix':'.5', 'amp':'1', 'peak':'500.', 'sigma':'200.', 'q': '2', 'ncut': '3', 'detune':'1e-3'})
            elif form['shape'] == 'fm':
                defaults.update({'lv1':'1', 'lv2':'0', 'lv3':'0', 'lv4':'0', 'fr1':'1', 'fr2':'1', 'fr3':'1', 'fr4':'1', 'fb1':'0', 'fb2':'0', 'fb3':'0', 'fb4':'0', 'algo':'0', 'parscale':'1'})
            elif form['shape'] == 'noise':
                defaults.update({'freq':'1.'})
            elif form['shape'] == 'fract' and cmd == 'lfo':
                defaults.update({'shift':'0', 'scale':'1'})

        except:
            pass

    elif cmd == 'drum':
        defaults.update({'shape':'fmnoise'})

        try:
            if form['shape'] in ['kick', 'kick2']: # TODO CALIBRATE
                defaults.update({'freq_start':'150', 'freq_end':'60', 'freq_decay':'.2', 'attack':'.01', 'hold':'.3', 'decay':'.1', 'click_amp':'1.5', 'click_delay':'.05', 'click_timbre':'5.'})

            if form['shape'] == 'fmnoise':
                defaults.update({'attack':'1e-3', 'decay':'.1', 'sustain':'.1', 'timbre1':'1', 'timbre2':'1'})
            elif form['shape'] == 'kick':
                defaults.update({'overdrive':'.2'})
            elif form['shape'] == 'kick2': # TODO: CALIBRATE (might need resonance? idk)
                defaults.update({'sq_phase':'5', 'sq_nmax':'10', 'sq_mix':'.8', 'sq_inr':'1', 'sq_ndecay':'1', 'sq_res':'1', 'sq_resq':'1', 'sq_detune':'0'})
            elif form['shape'] == 'snare': # TODO: CALIBRATE
                defaults.update({'freq0':'6000', 'freq1':'800', 'freq2':'350', 'freqdecay0':'.01', 'freqdecay1':'.01', 'decay':'.25', 'sustain':'.3', 'release':'.1', \
                                 'noise_amount':'.7', 'noise_attack':'.05', 'noise_decay':'.3', 'noise_sustain':'.3', 'overdrive':'0.6'})
            elif form['shape'] == 'bitexplosion':
                defaults.update({'nvar':'0', 'freqvar':'1', 'twostepvar':'1', 'var1':'1', 'var2':'1', 'var3':'1', 'decay':'1'})
            elif form['shape'] == 'protokick':
                defaults.update({'freq0':'180', 'freq1':'50', 'freqdecay':'.15', 'attack':'.01', 'hold':'.2', 'decay':'.5', 'drive':'1.2', 'detune':'5e-3',\
                                 'rev_amount':'.7', 'rev_hold':'.2', 'rev_decay':'.3', 'rev_drive':'1'})
            elif form['shape'] == 'protokickass':
                defaults.update({'freq0':'180', 'freq1':'50', 'freqdecay':'.15', 'attack':'5e-3', 'decay':'.5', 'drive':'2.4',\
                                 'rev1_amt':'.8', 'rev1_tone':'2000', 'rev1_exp':'13.5', 'rev1_drive':'.4',\
                                 'noise_amt':'.6', 'noise_hold':'9e-3', 'noise_decay':'9e-2', 'noise_tone':'16000',\
                                 'rev2_amt':'.04', 'rev2_tone':'8000', 'rev2_exp':'3', 'rev3_amt':'.03', 'rev3_tone':'5000', 'rev3_exp':'1'})
            elif form['shape'] == 'protosnare':
                defaults.update({'noise_amp':'.25', 'tone_amp': '.8', 'freq0':'500', 'freq1':'300', 'freqdecay':'.5', 'fmtone_amp':'.2', 'fmtone_freq':'500',\
                                 'noise1_amount':'.7', 'noise1_freq':'3196', 'noise2_amount':'.3', 'noise2_freq':'2965', 'noise3_amount':'.6', 'noise3_freq':'3643',\
                                 'attack':'1e-3', 'decay':'.1', 'release':'.2', 'tone_decayexp':'30', 'fmtone_decayexp':'20'})
            elif form['shape'] == 'protoshake':
                defaults.update({'timbre':'1', 'amp':'2', 'decay':'.05', 'release':'.01'})
            elif form['shape'] == 'protoride':
                defaults.update({'base_freq':'1240', 'base_pw':'.4', 'mod_freq':'525', 'mod_pw':'.2', 'noise_amt':'.9', 'noise_freq':'20',\
                                 'vibe_pw':'.2', 'vibe_freq':'20', 'comb_delay':'.445e-4', 'env_attack':'0', 'env_decay':'.8'})
            elif form['shape'] == 'protocrash':
                defaults.update({'base_freq':'310', 'base_pw':'.2', 'mod_freq':'1050', 'mod_pw':'.2', 'noise_amt':'1.5', 'noise_freq':'15',\
                                 'vibe_pw':'.2', 'vibe_freq':'20', 'comb_delay':'.445e-4', 'env_attack':'0', 'env_decay':'.6'})
            elif form['shape'] == 'metalnoise':
                defaults.update({'timescale':'1', 'factor1':'1', 'factor2':'2', 'modfreq':'0'})
        except:
            raise

    elif cmd == 'env':
        defaults.update({'shape':'ahdsr', 'attack':'1e-3', 'hold':'0', 'decay':'.1', 'sustain':'1', 'release':'0', 'scale':'1', 'shift':'0', 'offset':'0'})
        #TODO: calibrate attack and decay

        try:
            if form['shape'] == 'expdecay' or form['shape'] == 'expdecayrepeat' or form['shape'] == 'stepexpdecay':
                defaults.update({'exponent':'1', 'beats':'1'})
            elif form['shape'] == 'antivelattack':
                defaults.update({'vel':'vel', 'velmin':'0', 'velmax':'1'})
            elif form['shape'] == 'limitlength':
                defaults.update({'length':'L-rel', 'factor':'1'})

        except:
            pass

    elif cmd == 'seg':
        defaults.update({'shape':'generic', 'src':'0', 'scale':'1', 'shift':'0', 'offset': '0'})

        if form['shape'] == 'linear':
            defaults.update({'from': '0,0', 'to': None})

    elif cmd == 'filter':
        requirements.extend(['shape', 'src'])

        try:
            if form['shape'] in ['resolp', 'resohp']:
                defaults.update({'cutoff':'200', 'res':'0'})
                #TODO: calibrate "cutoff"! - and this isn't really cutoff! - find that thing out.
            elif form['shape'] == 'allpass':
                defaults.update({'gain':'.9', 'ndelay':'1'})
            elif form['shape'] in ['avghp', 'avglp']:
                defaults.update({'n':'2'})
            elif form['shape'] == 'bandpass':
                defaults.update({'center':'500', 'bandwidth':'100', 'n':'32'}) # TODO: this is still not working right. fix, if possible.
            elif form['shape'] == 'comb':
                defaults.update({'iir_gain':'.95', 'iir_n':'1', 'fir_gain':'.95', 'fir_n':'1'})
            elif form['shape'] == 'reverb': # TODO: calibrate!
                defaults.update({'iir_gain':'.8', 'iir_delay1':'1e-1', 'iir_delay2':'1e-2', 'iir_delay3':'1e-3', 'iir_delay4':'1e-4', 'ap_gain':'.9', 'ap_delay1':'5e-3', 'ap_delay2':'5e-4'})

        except:
            pass

    elif cmd == 'gac':
        defaults.update({'offset':'0', 'const':'0', 'lin':'0', 'quad':'0', 'sin':'0', 'sin_coeff':'0', 'exp':'0', 'exp_coeff':'0'})

    elif cmd == 'form':
        requirements.extend(['op','src'])

        try:
            if form['op'] == 'detune':
                defaults.update({'factor':'1.01,.995'})

            elif form['op'] =='pitchshift':
                defaults.update({'steps':'12'})

            elif form['op'] == 'quantize':
                defaults.update({'bits':'32'})

            elif form['op'] == 'overdrive':
                defaults.update({'gain':'1.33'})

            elif form['op'] == 'chorus':
                defaults.update({'number':'1', 'step':'.01', 'intensity':'.5', 'rate':'.5'})
                # TODO: calibrate

            elif form['op'] == 'delay':
                defaults.update({'number':'1', 'delay':'.2', 'gain':'.01'})

            elif form['op'] == 'waveshape':
                defaults.update({'amount':'1', 'a':'0', 'b':'0', 'c':'0', 'd':'1', 'e':'1'})

            elif form['op'] == 'sinshape':
                defaults.update({'amount':'1', 'parts':'3'})

            elif form['op'] == 'saturate':
                defaults.update({'gain':'3'})

            elif form['op'] == 'lofi':
                defaults.update({'bits':'128'})

            elif form['op'] == 'modsync':
                defaults.update({'freq':'1'})

            elif form['op'] == 'timescale':
                defaults.update({'scale':'1', 'shift':'0'})

            elif form['op'] == 'define':
                pass

        except:
            pass

    elif cmd == 'param':
        requirements.append('segments')
        defaults.update({'default':'0'})

    for key in defaults:
        if key not in form:
            form[key] = defaults[key]

    # special keyword 'include' as name: only for hardcoded strings
    if cid == 'include':
        requirements = ['id', 'type', 'mode', 'src']

    return form, defaults, requirements
