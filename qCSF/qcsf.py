import matplotlib.pyplot as plt
import numpy
import logging
import time

def entropy(p):
	return numpy.multiply(-p, numpy.log(p)) - numpy.multiply(1-p, numpy.log(1-p))

class QCSF():
	def __init__(self, stimulusSpace, parameterSpace):
		self.stimulusSpace = stimulusSpace
		self.parameterSpace = parameterSpace

		# Nms = stimulusRanges
		self.stimulusRanges = [len(sSpace) for sSpace in self.stimulusSpace]
		# Nm = stimComboCount
		self.stimComboCount = numpy.prod(self.stimulusRanges)
		
		# Nps = parameterRanges
		self.parameterRanges = [len(pSpace) for pSpace in self.parameterSpace]
		# Np = paramComboCount
		self.paramComboCount = numpy.prod(self.parameterRanges)

		self.d = 0.5
		self.sig = 0.25

		# Probabilities (initialize all of them to equal values that sum to 1)
		self.probabilities = numpy.ones((self.paramComboCount,1))/self.paramComboCount

	def next(self):
		# Np = prod(Nps); 			self.parameterRanges
		# Nm = prod(Nms);			self.stimComboCount
		# np = length(Nps);			self.parameterComboCount
		pbar = numpy.zeros(self.stimulusRanges)
		hbar = numpy.zeros(self.stimulusRanges)

		Nr = 100
		
		# collect samples from input space
		binEdges = numpy.cumsum(self.probabilities)
		# make sure the first edge is 0
		numpy.insert(binEdges, 0, 0)

		# plop and bin a bunch of random numbers
		binMap = numpy.digitize(numpy.random.rand(Nr,1), binEdges)
		# bin = pointers to bin numbers
		# if there are N elements in X grouped into Y bins,
		#   then there will be N elements in bin with values 0-(Y-1)
		
		# calculate probabilities for those samples
		tmp = numpy.arange(self.stimComboCount)[numpy.newaxis]
		p = self._pmeas(binMap, tmp)
		
		# Determine amount of information to be gained?
		pbar = sum(p)/Nr
		hbar = sum(entropy(p))/Nr
		gain = entropy(pbar)-hbar

		# Sort by gain - grab the indexes of the sort
		sortMap = numpy.argsort(-gain)
		
		# select the one with the most gain
		randIndex = int(numpy.random.rand()*self.stimComboCount/10)
		randIndex = 0
		indices = sortMap[randIndex]
		return indices

	# Given stimulus parameters, returns probability
	# param becomes 4 dimensions
	# meas comes in as an index or list of indicies?
	def _pmeas(self, param, meas):
		# params are from the binMap?
		logging.debug(f'Param input shape {param.shape}')
		logging.debug(f'Meas input shape {meas.shape}')
		# Converts param from 100x1 to 100x4
		# Each column represents a target parameter, mod'd by the resolution of that parameter
		if param.shape[1] == 1:
			param = param - 1
			d = len(self.parameterRanges)
			param = param.repeat(d, 1) # make 4 identical columns

			# for each column (except the last)
			for i in range(d-1):
				# modulu each column by the corresponding parameter resolution
				param[:, i] = numpy.mod(param[:, -1], self.parameterRanges[i])
				# except for the last column...
				# last column is divided by the resolution of each of the other corresponding parameters?
				param[:, -1] = numpy.floor(param[:, -1] / self.parameterRanges[i])
		
		# Converts meas from a 1x744 to a 2x744
		# Each row represents a stimulus dimension, mod'd by the resolution of that dimension

		# Why subtract by one here?
		meas = meas - 1
		d = len(self.stimulusRanges)
		# repeat the row
		meas = meas.repeat(d, 0)
		# for each row (except the last)
		for i in range(d-1):
			# modulu each row by the corresponding dimension resolution
			meas[i, :] = numpy.mod(meas[-1, :], self.stimulusRanges[i])
			# except for the last row...
			# last rowis divided by the resolution of each of the other corresponding dimensions?
			meas[-1, :] = numpy.floor(meas[-1, :] / self.stimulusRanges[i])
		
		if meas.shape[1] == self.stimComboCount:
			tmp = numpy.arange(self.stimulusRanges[1])[numpy.newaxis]
			S = self.csf(param, tmp)
			a = numpy.ones(self.stimulusRanges[0])[:,numpy.newaxis]
			b = numpy.arange(self.stimulusRanges[1])[numpy.newaxis,:]
			S = S[:, (a*b).astype(int)]
			S = S.reshape(S.shape[0], S.shape[1]*S.shape[2])
		else:
			S = self.csf(param, meas[1,:].reshape(1,-1))

		sen = 0.1 * meas[1, :]

		return 1 - numpy.divide(self.d, 1+numpy.exp((S-sen) / self.sig))

	# The parametric contrast-sensitivity function
	# Param order = peak sensitivity, peak frequency, bandwidth, log delta
	def csf(self, param, freqNum):
		# Peak sensitivity
		senp = 0.3+0.1*param[:,0]
		
		# Peak frequency
		freqp = -0.7+0.1*param[:,1]

		# log bandwidth ???
		logb = 0.05*param[:,2]
		
		# Low frequency truncation (delta)
		logd = -1.7 + 0.1*param[:,3]
		delta = numpy.exp(logd*numpy.log(10))
		
		freq = -0.7 + 0.1*freqNum


		n = len(senp)
		m = len(freqNum[0])

		freq = freq.repeat(n, 0)
		freqp = freqp[:,numpy.newaxis].repeat(m,1)
		senp = senp[:,numpy.newaxis].repeat(m,1)
		delta = delta[:,numpy.newaxis].repeat(m,1)
		
		divisor = numpy.log10(2)+logb
		divisor = divisor[:,numpy.newaxis].repeat(m,1)
		tmpVal = (4 * numpy.log10(2) * numpy.power(numpy.divide(freq-freqp, divisor), 2))
		S = numpy.maximum(0, senp - tmpVal)
		Scutoff = numpy.maximum(S, senp-delta)
		
		S[freq<freqp] = Scutoff[freq<freqp]

		return S

	def markResponse(self, response, pm):
		if response:
			self.probabilities = numpy.multiply(self.probabilities, pm)
		else:
			self.probabilities = numpy.multiply(self.probabilities, 1-pm)

		# Normalize probabilities
		self.probabilities = self.probabilities/numpy.sum(self.probabilities)

	def margin(self, prob, n):
		d = len(self.parameterRanges)
		params = numpy.zeros((self.paramComboCount, d))
		z = numpy.arange(self.paramComboCount).transpose()
		params[:, -1] = z
		
		for i in range(d-1):
			params[:, i] = numpy.mod(params[:, -1], self.parameterRanges[i])
			params[:, -1] = numpy.floor(params[:, -1] / self.parameterRanges[i])
		
		pMarg = numpy.zeros((self.parameterRanges[n], 1))
		for k in range(self.parameterRanges[n]):
			tmp = (params[:, n] == k).reshape(-1, 1)
			pMarg[k] = numpy.sum(numpy.multiply(prob, tmp))

		return pMarg

	# Plot the current state
	def visual(self, prob, pobs):
		mean = numpy.zeros(len(self.parameterRanges))
		for n, parameterRange in enumerate(self.parameterRanges):
			pMarg = self.margin(prob, n).reshape(1,-1)
			mean[n] = numpy.dot(pMarg, numpy.arange(parameterRange).reshape(-1,1))
		
		meas = numpy.arange(self.stimulusRanges[1]).reshape(-1,1)
		Sobs = self.csf(pobs.reshape(1, -1), meas)
		S = self.csf(mean.reshape(1, -1), meas)
		x = numpy.arange(self.stimulusRanges[1]).reshape(-1,1)
		y = numpy.concatenate((Sobs, S), 1)

		graph.clear()
		graph.plot(x, y)
		graph.grid()
		plt.pause(0.001)

	def sim(self, p, m):
		p = self._pmeas(p, m)
		return numpy.random.rand()<p

if __name__ == '__main__':
	import pathlib

	saveImages = False
	
	pathlib.Path('logs').mkdir(parents=True, exist_ok=True) 
	logging.basicConfig(filename='logs/%d.log' % time.time(), level=logging.DEBUG)

	if saveImages:
		pathlib.Path('figs').mkdir(parents=True, exist_ok=True) 


	fig = plt.figure()
	graph = fig.add_subplot(1, 1, 1)
	graph.set_ylim((0,3))
	plt.ion()
	plt.show()

	stimulusSpace = numpy.array([
		numpy.arange(0, 31),	# Frequency
		numpy.arange(0, 24)		# Contrast
	])
	parameterSpace = numpy.array([
		numpy.arange(0, 28),	# Peak sensitivity
		numpy.arange(0, 21),	# Peak frequency
		numpy.arange(0, 21),	# Log bandwidth
		numpy.arange(0, 21)		# Low frequency truncation (log delta)
	])

	trueParams = numpy.array([[20, 11, 8, 11]])
	qcsf = QCSF(stimulusSpace, parameterSpace)
	#qcsf.visual(qcsf.probabilities, trueParams)

	# Trial loop
	for i in range(25):
		# Get the next stimulus
		logging.info(f'**************** CALCULATING NEXT **************** {i}')
		m = qcsf.next()
		m = numpy.array([m]).reshape((1,1))
		# m is just the index
		# @TODO: convert that to stim parameters
		
		logging.debug('****************** DOING SAMPLE ******************')
		pm = qcsf._pmeas(
			numpy.arange(qcsf.paramComboCount)[:,numpy.newaxis],
			m
		)
		
		logging.debug('****************** SIMUL RESPON ******************')
		# Simulate a response
		response = qcsf.sim(trueParams, m)
		logging.debug('**************** MARKING RESPONSE **************')
		qcsf.markResponse(response, pm)
		
		logging.debug('****************** UPDATE VISUL ******************')
		# Update the plot
		qcsf.visual(qcsf.probabilities, trueParams)
		if saveImages:
			plt.savefig('figs/%d.png' % int(time.time()*1000))

	plt.ioff()
	plt.show()


