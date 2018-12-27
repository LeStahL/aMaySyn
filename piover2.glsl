#define PI radians(180.)
float clip(float a) { return clamp(a,-1.,1.); }
float theta(float x) { return smoothstep(0., 0.01, x); }
float _sin(float a) { return sin(2. * PI * mod(a,1.)); }
float _sin(float a, float p) { return sin(2. * PI * mod(a,1.) + p); }
float _unisin(float a,float b) { return (.5*_sin(a) + .5*_sin((1.+b)*a)); }
float _sq(float a) { return sign(2.*fract(a) - 1.); }
float _sq(float a,float pwm) { return sign(2.*fract(a) - 1. + pwm); }
float _psq(float a) { return clip(50.*_sin(a)); }
float _psq(float a, float pwm) { return clip(50.*(_sin(a) - pwm)); } 
float _tri(float a) { return (4.*abs(fract(a)-.5) - 1.); }
float _saw(float a) { return (2.*fract(a) - 1.); }
float quant(float a,float div,float invdiv) { return floor(div*a+.5)*invdiv; }
float quanti(float a,float div) { return floor(div*a+.5)/div; }
float freqC1(float note){ return 32.7 * pow(2.,note/12.); }
float minus1hochN(int n) { return (1. - 2.*float(n % 2)); }

#define pat4(a,b,c,d,x) mod(x,1.)<.25 ? a : mod(x,1.)<.5 ? b : mod(x,1.) < .75 ? c : d

const float BPM = 80.;
const float BPS = BPM/60.;
const float SPB = 60./BPM;

const float Fsample = 44100.; // I think?
const float Tsample = 2.267573696e-5;

float doubleslope(float t, float a, float d, float s)
{
    return smoothstep(-.00001,a,t) - (1.-s) * smoothstep(0.,d,t-a);
}

float s_atan(float a) { return 2./PI * atan(a); }
float s_crzy(float amp) { return clamp( s_atan(amp) - 0.1*cos(0.9*amp*exp(amp)), -1., 1.); }
float squarey(float a, float edge) { return abs(a) < edge ? a : floor(4.*a+.5)*.25; } 

float supershape(float s, float amt, float A, float B, float C, float D, float E)
{
    float w;
    float m = sign(s);
    s = abs(s);

    if(s<A) w = B * smoothstep(0.,A,s);
    else if(s<C) w = C + (B-C) * smoothstep(C,A,s);
    else if(s<=D) w = s;
    else if(s<=1.)
    {
        float _s = (s-D)/(1.-D);
        w = D + (E-D) * (1.5*_s*(1.-.33*_s*_s));
    }
    else return 1.;
    
    return m*mix(s,w,amt);
}

float GAC(float t, float offset, float a, float b, float c, float d, float e, float f, float g)
{
    t = t - offset;
    return t<0. ? 0. : a + b*t + c*t*t + d*sin(e*t) + f*exp(-g*t);
}

float MACESQ(float t, float f, float phase, int NMAX, int NINC, float MIX, float INR, float NDECAY, float RES, float RES_Q, float DET, float PW)
{
    float ret = 0.;
    
    float p = f*t + phase;
    for(int N=0; N<=NMAX; N+=NINC)
    {
        float mode     = 2.*float(N) + 1.;
        float inv_mode = 1./mode; 		// avoid division? save table of Nmax <= 20 in some array or whatever
        float comp_TRI = (N % 2 == 1 ? -1. : 1.) * inv_mode*inv_mode;
        float comp_SQU = inv_mode * (1. + (2.*float(N%2)-1.)*_sin(PW)); 
        float comp_mix = (MIX * comp_TRI + (1.-MIX) * comp_SQU);
        
        //one special mode from legacy code 'matzeskuh' - I computed some shitty-but-fun Fourier coefficients for PWM
        if(MIX < -.01) comp_mix = 1./(2.*PI*float(N)) * (minus1hochN(N)*_sin(PW*float(N)+.25) - 1.);

        float filter_N = pow(1. + pow(float(N) * INR,2.*NDECAY),-.5) + RES * exp(-pow(float(N)*INR*RES_Q,2.));

        if(abs(filter_N*comp_mix) < 1e-6) break;
        
        ret += comp_mix * filter_N * (_sin(mode * p) + _sin(mode * p * (1.+DET)));
    }
    return s_atan(ret);
}

float QMACESQ(float t, float f, float phase, float QUANT, int NMAX, int NINC, float MIX, float INR, float NDECAY, float RES, float RES_Q, float DET, float PW)
{
    return MACESQ(quant(t,QUANT,1./QUANT), f, phase, NMAX, NINC, MIX, INR, NDECAY, RES, RES_Q, DET, PW);
}

float env_ADSR(float x, float L, float A, float D, float S, float R)
{
    float att = x/A;
    float dec = 1. - (1.-S)*(x-A)/D;
    float rel = (x <= L-R) ? 1. : (L-x)/R;
    return (x < A ? att : (x < A+D ? dec : S)) * rel;    
}

// CHEERS TO metabog https://www.shadertoy.com/view/XljSD3 - thanks for letting me steal
float resolpsomesaw1(float time, float f, float tL, float fa, float reso)
{
    int maxTaps = 128;
    fa = sqrt(fa*Tsample);
    float c = pow(0.5, (128.0-fa*128.0)  / 16.0);
    float r = pow(0.5, (reso*128.0+24.0) / 16.0);
    
    float v0 = 0.;
    float v1 = 0.;
    
    for(int i = 0; i < maxTaps; i++)
    {
          float _TIME = time - float(maxTaps-i)*Tsample;
          float Bprog = _TIME * BPS; //might need that
          float inp = (2.*fract(f*_TIME+0.)-1.);
          v0 =  (1.0-r*c)*v0  -  (c)*v1  + (c)*inp;
          v1 =  (1.0-r*c)*v1  +  (c)*v0;
    }
    return v1;
}
// CHEERS TO metabog https://www.shadertoy.com/view/XljSD3 - thanks for letting me steal
float resolpsaw2D(float time, float f, float tL, float fa, float reso)
{
    int maxTaps = 128;
    fa = sqrt(fa*Tsample);
    float c = pow(0.5, (128.0-fa*128.0)  / 16.0);
    float r = pow(0.5, (reso*128.0+24.0) / 16.0);
    
    float v0 = 0.;
    float v1 = 0.;
    
    for(int i = 0; i < maxTaps; i++)
    {
          float _TIME = time - float(maxTaps-i)*Tsample;
          float Bprog = _TIME * BPS; //might need that
          float inp = s_atan((2.*fract((f+.3*_sin(5.*Bprog)*env_ADSR(_TIME,tL,.2,.3,.8,.2))*_TIME+0.)-1.)+(2.*fract((1.-.01)*(f+.3*_sin(5.*Bprog)*env_ADSR(_TIME,tL,.2,.3,.8,.2))*_TIME+0.)-1.)+(2.*fract((1.-.011)*(f+.3*_sin(5.*Bprog)*env_ADSR(_TIME,tL,.2,.3,.8,.2))*_TIME+0.)-1.)+(2.*fract((1.+.02)*(f+.3*_sin(5.*Bprog)*env_ADSR(_TIME,tL,.2,.3,.8,.2))*_TIME+0.)-1.));
          v0 =  (1.0-r*c)*v0  -  (c)*v1  + (c)*inp;
          v1 =  (1.0-r*c)*v1  +  (c)*v0;
    }
    return v1;
}


float env_ADSRexp(float x, float L, float A, float D, float S, float R)
{
    float att = pow(x/A,8.);
    float dec = S + (1.-S) * exp(-(x-A)/D);
    float rel = (x <= L-R) ? 1. : pow((L-x)/R,4.);
    return (x < A ? att : dec) * rel;    
}

//matze: not happy that I include this as is, but we'll just live with it, it is ancient knowledge
float bitexplosion(float time, float B, int dmaxN, float fvar, float B2amt, float var1, float var2, float var3, float decvar)
{
    float snd = 0.;
    float B2 = mod(B,2.);
    float f = 60.*fvar;
	float dt = var1 * 2.*PI/15. * B/sqrt(10.*var2-.5*var3*B);
    int maxN = 10 + dmaxN;
    for(int i=0; i<2*maxN+1; i++)
    {
        float t = time + float(i - maxN)*dt;
        snd += _sin(f*t + .5*(1.+B2amt*B2)*_sin(.5*f*t));
    }
    float env = exp(-2.*decvar*B);
    return atan(snd * env);
}

float AMAYSYN(float t, float B, float Bon, float Boff, float note, int Bsyn)
{
    float Bprog = B-Bon;
    float Bproc = Bprog/(Boff-Bon);
    float L = Boff-Bon;
    float tL = SPB*L;
    float _t = SPB*(B-Bon);
    float f = freqC1(note);
	float vel = 1.;

    float env = theta(B-Bon) * theta(Boff-B);
	float s = _sin(t*f);

	if(Bsyn == 0){}
    else if(Bsyn == 1){
      s = _sin(.5*f*t)*env_ADSR(_t,tL,.5,2.,.5,.1);}
    else if(Bsyn == 2){
      s = theta(Bprog)*exp(-16.*mod(Bprog,.125))*theta(Bprog)*exp(-1.5*Bprog)*(s_atan((2.*fract(f*t+0.)-1.)+(2.*fract((1.-.01)*f*t+0.)-1.)+(2.*fract((1.-.033)*f*t+0.)-1.)+(2.*fract((1.-.04)*f*t+0.)-1.))+.6*s_atan((2.*fract(.5*f*t+.01)-1.)+(2.*fract((1.-.05)*.5*f*t+.01)-1.)+(2.*fract((1.+.03)*.5*f*t+.01)-1.)+(2.*fract((1.+.02)*.5*f*t+.01)-1.)));}
    else if(Bsyn == 3){
      s = _sin(f*t)
      +-.1*GAC(t,0.,1.,2.,-.5,3.,2.,2.,-.25)*_sin(f*t)
      +.1*GAC(t,0.,1.,2.,-.5,3.,2.,2.,-.25)*supershape(_sin(f*t),1.,.01,.7,.1,.6,.8);}
    else if(Bsyn == 4){
      s = resolpsomesaw1(_t,f,tL,.1,.4);}
    else if(Bsyn == 5){
      s = env_ADSR(_t,tL,.2,.3,.8,.2)*resolpsaw2D(_t,f,tL,300.*env_ADSR(Bprog,L,.5,.5,.4,0.),0.);}
    else if(Bsyn == -1){
      s = s_atan(vel*smoothstep(0.,.1,_t)*smoothstep(.1+.3,.3,_t)*(clip(10.*_tri((61.5+(115.5-61.5)*smoothstep(-.1, 0.,-_t))*_t))+_sin(.5*(61.5+(115.5-61.5)*smoothstep(-.1, 0.,-_t))*_t)))+1.2*step(_t,.05)*_sin(5000.*_t*.8*_saw(1000.*_t*.8));}
    else if(Bsyn == -2){
      s = s_atan(vel*smoothstep(0.,.015,_t)*smoothstep(.1+.15,.15,_t)*MACESQ(_t,(50.+(200.-50.)*smoothstep(-.12, 0.,-_t)),5.,10,1,.8,1.,1.,1.,.1,.1,0.) + .4*.5*step(_t,.03)*_sin(_t*1100.*1.*_saw(_t*800.*1.)) + .4*(1.-exp(-1000.*_t))*exp(-40.*_t)*_sin((400.-200.*_t)*_t*_sin(1.*(50.+(200.-50.)*smoothstep(-.12, 0.,-_t))*_t)));}
    else if(Bsyn == -3){
      s = vel*fract(sin(t*100.*.9)*50000.*.9)*doubleslope(_t,.03,.15,.15);}
    else if(Bsyn == -4){
      s = vel*bitexplosion(t, Bprog, 1,1.,1.,1.,1.,1.,1.);}
    else if(Bsyn == -5){
      s = (.6+.25*_psq(4.*B,0.))*vel*fract(sin(t*100.*.3)*50000.*2.)*doubleslope(_t,0.,.05,0.);}
    else if(Bsyn == -6){
      s = vel*clamp(1.6*_tri(_t*(350.+(6000.-800.)*smoothstep(-.01,0.,-_t)+(800.-350.)*smoothstep(-.01-.01,-.01,-_t)))*smoothstep(-.1,-.01-.01,-_t) + .7*fract(sin(t*90.)*4.5e4)*doubleslope(_t,.05,.3,.3),-1., 1.)*doubleslope(_t,0.,.25,.3);}
    
	return clamp(env,0.,1.) * s_atan(s);
}

float BA8(float x, int pattern)
{
    x = mod(x,1.);
    float ret = 0.;
	for(int b = 0; b < 8; b++)
    	if ((pattern & (1<<b)) > 0) ret += step(x,float(7-b)/8.);
    return ret * .125;
}

float mainSynth(float time)
{
    int NO_trks = 2;
    int trk_sep[3] = int[3](0,1,5);
    int trk_syn[2] = int[2](5,6);
    float trk_norm[2] = float[2](.9,1.);
    float trk_rel[2] = float[2](.7,.5);
    float mod_on[5] = float[5](0.,0.,2.,4.,6.);
    float mod_off[5] = float[5](8.,2.,4.,6.,8.);
    int mod_ptn[5] = int[5](0,1,1,1,1);
    float mod_transp[5] = float[5](-12.,0.,0.,0.,0.);
    float max_mod_off = 8.;
    int drum_index = 6;
    float drum_synths = 7.;
    int NO_ptns = 2;
    int ptn_sep[3] = int[3](0,24,36);
    float note_on[36] = float[36](0.,0.,0.,1.,1.,1.,2.,2.,2.,3.,3.,3.,4.,4.,4.,5.,5.,5.,6.,6.,6.,7.,7.,7.,0.,.125,.375,.5,.625,.875,1.125,1.25,1.375,1.5,1.625,1.875);
    float note_off[36] = float[36](1.,1.,1.,2.,2.,2.,3.,3.,3.,4.,4.,4.,5.,5.,5.,6.,6.,6.,7.,7.,7.,8.,8.,8.,.375,.25,.5,.625,.75,1.,1.25,1.625,1.5,1.625,1.75,2.);
    float note_pitch[36] = float[36](36.,72.,63.,34.,70.,65.,39.,70.,67.,37.,72.,65.,36.,72.,63.,34.,70.,65.,27.,70.,58.,29.,69.,60.,16.,19.,19.,20.,19.,19.,19.,2.,19.,76.,19.,19.);
    float note_vel[36] = float[36](1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.,1.);
    
    float r = 0.;
    float d = 0.;

    // mod for looping
    float BT = mod(BPS * time, max_mod_off);
    if(BT > max_mod_off) return r;
    time = SPB * BT;

    float r_sidechain = 1.;

    float Bon = 0.;
    float Boff = 0.;

    for(int trk = 0; trk < NO_trks; trk++)
    {
        int TLEN = trk_sep[trk+1] - trk_sep[trk];
       
        int _mod = TLEN;
        for(int i=0; i<TLEN; i++) if(BT < mod_off[(trk_sep[trk]+i)]) {_mod = i; break;}
        if(_mod == TLEN) continue;
       
        float B = BT - mod_on[trk_sep[trk]+_mod];

        int ptn = mod_ptn[trk_sep[trk]+_mod];
        int PLEN = ptn_sep[ptn+1] - ptn_sep[ptn];
       
        int _noteU = PLEN-1;
        for(int i=0; i<PLEN-1; i++) if(B < note_on[(ptn_sep[ptn]+i+1)]) {_noteU = i; break;}

        int _noteL = PLEN-1;
        for(int i=0; i<PLEN-1; i++) if(B <= note_off[(ptn_sep[ptn]+i)] + trk_rel[trk]) {_noteL = i; break;}
       
        for(int _note = _noteL; _note <= _noteU; _note++)
        {
            Bon    = note_on[(ptn_sep[ptn]+_note)];
            Boff   = note_off[(ptn_sep[ptn]+_note)];

            float anticlick = 1.-exp(-1000.*(B-Bon)); //multiply this elsewhere?

            if(trk_syn[trk] == drum_index)
            {
                int Bdrum = int(mod(note_pitch[ptn_sep[ptn]+_note], drum_synths));
                float Bvel = note_vel[(ptn_sep[ptn]+_note)] * pow(2.,mod_transp[_mod]/6.);

                //0 is for sidechaining - am I doing this right?
                if(Bdrum == 0)
                    r_sidechain = anticlick - .999 * theta(B-Bon) * smoothstep(Boff,Bon,B);
                else
                    d += trk_norm[trk] * AMAYSYN(time, B, Bon, Boff, Bvel, -Bdrum);
            }
            else
            {
                r += trk_norm[trk] * AMAYSYN(time, B, Bon, Boff,
                                               note_pitch[(ptn_sep[ptn]+_note)] + mod_transp[_mod], trk_syn[trk]);
            }
        }
    }

    return s_atan(s_atan(r_sidechain * r + d));
//    return sign(snd) * sqrt(abs(snd)); // eine von Matzes "besseren" Ideen
}

vec2 mainSound(float t)
{
    //maybe this works in enhancing the stereo feel
    float stereo_width = 0.1;
    float stereo_delay = 0.00001;
   
    //float comp_l = mainSynth(t) + stereo_width * mainSynth(t - stereo_delay);
    //float comp_r = mainSynth(t) + stereo_width * mainSynth(t + stereo_delay);
   
    //return vec2(comp_l * .99999, comp_r * .99999);
   
    return vec2(mainSynth(t));
}
