import numpy as np
#import seaborn as sns
from scipy import signal
import math
#import sys

from genericsynth import synthInterface as SI

class PistonSynth(SI.MySoundModel) :

	def __init__(self, sinLevel=1, noiseLevel=.2, amp=1) :
		SI.MySoundModel.__init__(self)
		#create a dictionary of the parameters this synth will use
		self.__addParam__("sinLevel", 0, 1, sinLevel)
		self.__addParam__("noiseLevel", 0, 1, noiseLevel)
		self.__addParam__("amp", 0, 1, amp)


	'''
		Override of base model method
	'''
	def generate(self, sigLenSecs, amp=None) :
		if amp==None : amp=self.getParam("amp")

		ticksamps = int(round(sigLenSecs*self.sr)) # in samples

		noise=tick=2*np.random.rand(ticksamps)-1    #noise samples in [-1,1]
		#tick=np.random.rand(ticksamps)    #noise samples in [0,1]

		# raised sin
		arg=np.linspace(0, np.pi, num=ticksamps)
		tick=self.getParam("sinLevel")*np.sin(arg)+self.getParam("noiseLevel")*noise

		#normalize RMS to get closer to perceptually equal loudness cylander bursts
		#tick = tick/np.sqrt(np.sum(tick*tick))

		#NORMALIZE to max value of tick
		#maxfsignal=max(abs(tick))
		#tick = tick*.9/maxfsignal

		ampenv=SI.bkpoint([0,1,1,0,0],[3,ticksamps-7,3,1])
		tick=ampenv*tick
		#tick = np.pad(tick, (0, length-ticksamps), 'constant')



		return tick

