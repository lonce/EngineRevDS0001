import numpy as np
import math

from scipy import signal   #for making a filter
from random import random

from genericsynth import synthInterface as SI
from PistonSynth import PistonSynth  # This is "event" synthesizer this pattern synth will use

# Repeat an array float(n) times and concatenate them 
def repeatSeg(seg,n) : 
        return  np.concatenate((np.tile(seg,int(n)), seg[:int(round((n%1)*len(seg)))]))

# Exend an event (time) list by concatenating the sequence with seDur added to the events in each successive repeat.
def extendEventSequence(oseq, seqDur, durationSecs) :
        cyclelength=len(oseq)

        newEvList=[]
        newEvNum=0
        revNum=0
        revSeqEvNum=0
        t=oseq[revSeqEvNum]
        while t < durationSecs :
                
                newEvList.append(t)

                # now get the next one
                newEvNum=newEvNum+1
                revNum=newEvNum//cyclelength
                revSeqEvNum=newEvNum%cyclelength
                t=oseq[revSeqEvNum]+revNum*seqDur
        return newEvList


################################################################################################################
class EngineRevSynth(SI.MySoundModel) :

        def __init__(self,  rate_exp=0, irreg_exp=1, evdur=.007,  cylinders=8, evamp=.5) :

                SI.MySoundModel.__init__(self)
                #get the sub synth
                self.evSynth=PistonSynth(amp=evamp)

                self.__addParam__("rate_exp", -10, 10, rate_exp)
                self.__addParam__("irreg_exp", 0, 50, irreg_exp)
                self.__addParam__("evdur", .001, 10, evdur)
                self.__addParam__("cylinders", 2, 16, cylinders)

                #My "hard coded" defaults for the subsynth
                self.evSynth.setParam('amp', .4) #should be smaller for overlapping events...


                self.numResonators=5

                # Parallel Resonators 
                self.__addParam__("f0", 2, 2000, 60., synth_doc="resonator f0")
                self.__addParam__("q0", .1, 40, 3., synth_doc="resonator q0")
                self.__addParam__("a0", 0, 1, 1., synth_doc="resonator a0")
                #-------------------------------------
                self.__addParam__("f1", 2, 2000, 150., synth_doc="resonator f1")
                self.__addParam__("q1", .1, 40, 2., synth_doc="resonator q1")
                self.__addParam__("a1", 0, 1, .5, synth_doc="resonator a1")
                #-------------------------------------
                self.__addParam__("f2", 2, 2000, 390., synth_doc="resonator f2")
                self.__addParam__("q2", .1, 40, 5., synth_doc="resonator q2")
                self.__addParam__("a2", 0, 1, .7, synth_doc="resonator a2")
                #-------------------------------------
                self.__addParam__("f3", 2, 2000, 475., synth_doc="resonator f3")
                self.__addParam__("q3", .1, 40, 3., synth_doc="resonator q3")
                self.__addParam__("a3", 0, 1, 1., synth_doc="resonator a3")
                #-------------------------------------
                self.__addParam__("f4", 2, 2000, 721., synth_doc="resonator f4")
                self.__addParam__("q4", .1, 40, 2., synth_doc="resonator q4")
                self.__addParam__("a4", 0, 1, 5., synth_doc="resonator a4")

        '''
                Just a shorthand for setting all resonance parameters in one call with 3 array args for f, q, a
        '''
        def setResonances(self, f, q, a) :
                assert len(f)==len(q)==len(q)==self.numResonators, f"setResonance: All arrays must be of length {self.numResonators}"
                for i in range(self.numResonators) :
                        self.setParam("f"+str(i), f[i])
                        self.setParam("q"+str(i), q[i])
                        self.setParam("a"+str(i), a[i])
                       

        '''
                Random resonance features for the engine
        '''
        def setRandomResonance(self) :
                for i in range(self.numResonators) :
                        self.setParam("f"+str(i), 120*(i+.5*random()))
                        self.setParam("q"+str(i), 10*random())
                        self.setParam("a"+str(i), 1-i/(self.numResonators+4))
                        print(f"setRandomResonance: For reson {i}, f = {self.getParam('f'+str(i))}. q={self.getParam('q'+str(i))} and a= {self.getParam('a'+str(i))}") 
                        print(f"---")

        '''
                Override of base model method
        '''
        def generate(self,  durationSecs) :

                cylinders=self.getParam("cylinders")
                
                #how much time for n piston pops?
                revdur=cylinders/np.power(2,self.getParam("rate_exp"))
                revSeq=SI.noisySpacingTimeList(self.getParam("rate_exp"), self.getParam("irreg_exp"), revdur)
                #print(f"revdur is {revdur} and durationSecs is {durationSecs}, so will call repeatSeg with {durationSecs/revdur}")
 
                elist=extendEventSequence(revSeq, revdur, durationSecs)
                return self.elist2signal(elist, durationSecs)


        ''' Take a list of event times, and return our (possibly overlapped) events at those times'''
        def elist2signal(self, elist, sigLenSecs) :
                numSamples=self.sr*sigLenSecs
                sig=np.zeros(sigLenSecs*self.sr)

                print(f"Evdur is {self.getParam('evdur')} and ioi is {1./np.power(2,self.getParam('rate_exp'))}")
                dur=np.minimum(self.getParam('evdur'), 1./np.power(2,self.getParam('rate_exp')))

                for nf in elist :
                        startsamp=int(round(nf*self.sr))%numSamples
                        gensig = self.evSynth.generate(dur)
                        sig = SI.addin(gensig, sig, startsamp)

                outsig=np.zeros((len(sig)))


                for i in range(self.numResonators) :
                        # Design peak filter
                        b, a = signal.iirpeak(self.getParam("f"+str(i)), self.getParam("q"+str(i)), self.sr)
                        #use it
                        foo=signal.lfilter(b, a, sig)
                        outsig= outsig+self.getParam("a"+str(i))*signal.lfilter(b, a, foo)


                # envelope with 10ms attack, decay at the beginning and the end of the whole signal. Avoid rude cuts
                length = int(round(sigLenSecs*self.sr)) # in samples
                ltrans = round(.01*self.sr)
                midms=length-2*ltrans-1
                ampenv=SI.bkpoint([0,1,1,0,0],[ltrans,midms,ltrans,1])

                return np.array(ampenv)*outsig