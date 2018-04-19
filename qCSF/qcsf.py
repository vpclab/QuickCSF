import matplotlib.pyplot as plt
import numpy
import logging
import time

def mapStimParams(params):
	contrast = params[:,0] / 24 * 3
	frequency = params[:,1]

	return numpy.stack((contrast, frequency))


def mapCSFParams(params):
	senp = 0.3+0.1*params[:,0]
	
	# Peak frequency
	freqp = -0.7+0.1*params[:,1]

	# log bandwidth ???
	logb = 0.05*params[:,2]
	
	# Low frequency truncation (delta)
	logd = -1.7 + 0.1*params[:,3]
	delta = numpy.exp(logd*numpy.log(10))

	return numpy.stack((senp, freqp, logb, delta))

def unroll(data, dims, axis):
	if axis == 0:
		transposed = False
	elif axis == 1:
		data = data.T
		dims = numpy.flip(dims, 0)
		transposed = True
	else:
		raise ValueError('I don\'t know how to unroll this many dimensions.')

	# expand matrix to hold all of our values
	if data.shape[1] == 1:
		data = data.repeat(len(dims), 1)

	for i in range(len(dims) - 1):
		# Modulu each column by the corresponding dimension size 
		data[:, i] = numpy.mod(data[:, -1], dims[i])
		data[:, -1] = numpy.floor(data[:, -1] / dims[i])

	if transposed:
		return data.T
	else:
		return data

def entropy(p):
	return numpy.multiply(-p, numpy.log(p)) - numpy.multiply(1-p, numpy.log(1-p))

class QCSF():
	def __init__(self, stimulusSpace, parameterSpace):
		self.stimulusSpace = stimulusSpace
		self.parameterSpace = parameterSpace

		self.stimulusRanges = [len(sSpace) for sSpace in self.stimulusSpace]
		self.stimComboCount = numpy.prod(self.stimulusRanges)
		
		self.parameterRanges = [len(pSpace) for pSpace in self.parameterSpace]
		self.paramComboCount = numpy.prod(self.parameterRanges)

		self.d = 0.5
		self.sig = 0.25

		# Probabilities (initialize all of them to equal values that sum to 1)
		self.probabilities = numpy.ones((self.paramComboCount,1))/self.paramComboCount

		self.currentStimulusIndex = None
		self.currentStimParamIndices = None
		self.responseHistory = []

	def next(self):
		# collect random samples from input space
		# the randomness is weighted by the stim parameter probability
		# more probable stim params have higher weight of being sampled

		randomSampleCount = 100

		paramIndicies = numpy.random.choice(
			numpy.arange(self.paramComboCount),
			randomSampleCount,
			p=self.probabilities[:,0]
		).reshape(-1, 1)

		# calculate probabilities for all stimuli with all samples of parameters
		# @TODO: parallelize this
		stimIndicies = numpy.arange(self.stimComboCount).reshape(1,-1)
		p = self._pmeas(paramIndicies, stimIndicies)
		
		# Determine amount of information to be gained
		pbar = sum(p)/randomSampleCount
		hbar = sum(entropy(p))/randomSampleCount
		gain = entropy(pbar)-hbar

		# Sort by gain descending (highest gain first)
		sortMap = numpy.argsort(-gain)
		
		# select a random one from the highest 10% info givers
		randIndex = int(numpy.random.rand()*self.stimComboCount/10)
		self.currentStimulusIndex = numpy.array([[sortMap[randIndex]]])
		self.currentStimParamIndices = unroll(
			self.currentStimulusIndex,
			self.stimulusRanges,
			0
		)[0]

		return self.currentStimParamIndices

	# Returns probability of output parameters given stimulusIndex
	# @TODO: give this a better name
	# Expects UNMAPPED parameters
	def _pmeas(self, parameters, stimulusIndex):
		# Check if param list is a single-dimension
		if parameters.shape[1] == 1:
			# If it's a single dimension, we need to unroll it into 4 separate ones
			parameters = unroll(parameters, self.parameterRanges, 0)

		# Unroll into separate rows
		stimulusIndices = unroll(stimulusIndex, self.stimulusRanges, 1)

		# Some kind of special-case optimization... ?
		if stimulusIndices.shape[1] == self.stimComboCount:
			frequencies = numpy.arange(self.stimulusRanges[1])[numpy.newaxis]
			csfValues = self.csf(parameters, frequencies)

			a = numpy.ones(self.stimulusRanges[0])[:,numpy.newaxis]
			b = numpy.arange(self.stimulusRanges[1])[numpy.newaxis,:]

			csfValues = csfValues[:, (a*b).astype(int)]
			csfValues = csfValues.reshape(
				csfValues.shape[0],
				csfValues.shape[1]*csfValues.shape[2]
			)
		else:
			csfValues = self.csf(parameters, stimulusIndices[1,:].reshape(1,-1))

		sensitivity = 0.1 * stimulusIndices[0, :]
		sensitivity = numpy.ones((parameters.shape[0], 1)) * sensitivity

		return 1 - numpy.divide(self.d, 1+numpy.exp((csfValues-sensitivity) / self.sig))

	# The parametric contrast-sensitivity function
	# Param order = peak sensitivity, peak frequency, bandwidth, log delta
	# @TODO: move this out of the class
	# Expects UNMAPPED parameters
	def csf(self, parameters, freqNum):
		[peakSensitivity, peakFrequency, logBandwidth, delta] = mapCSFParams(parameters)
	
		freq = -0.7 + 0.1*freqNum

		n = len(peakSensitivity)
		m = len(freqNum[0])

		freq = freq.repeat(n, 0)
		peakFrequency = peakFrequency[:,numpy.newaxis].repeat(m,1)
		peakSensitivity = peakSensitivity[:,numpy.newaxis].repeat(m,1)
		delta = delta[:,numpy.newaxis].repeat(m,1)
		
		divisor = numpy.log10(2)+logBandwidth
		divisor = divisor[:,numpy.newaxis].repeat(m,1)
		tmpVal = (4 * numpy.log10(2) * numpy.power(numpy.divide(freq-peakFrequency, divisor), 2))
		
		sensitivity = numpy.maximum(0, peakSensitivity - tmpVal)
		Scutoff = numpy.maximum(sensitivity, peakSensitivity-delta)
		
		sensitivity[freq<peakFrequency] = Scutoff[freq<peakFrequency]

		return sensitivity

	def markResponse(self, response):
		self.responseHistory.append([self.currentStimulusIndex, response])
		pm = self._pmeas(
			numpy.arange(self.paramComboCount)[:,numpy.newaxis],
			self.currentStimulusIndex
		)

		if response:
			self.probabilities = numpy.multiply(self.probabilities, pm)
		else:
			self.probabilities = numpy.multiply(self.probabilities, 1-pm)

		# Normalize probabilities
		self.probabilities = self.probabilities/numpy.sum(self.probabilities)

	def margin(self, prob, parameterIndex):
		params = numpy.zeros((self.paramComboCount, len(self.parameterRanges)))
		params[:, -1] = numpy.arange(self.paramComboCount)
		
		params = unroll(params, self.parameterRanges, 0)
		
		pMarg = numpy.zeros((self.parameterRanges[parameterIndex], 1))
		for parameterCalcIndex in range(self.parameterRanges[parameterIndex]):
			# Filter out all the other parameters' values
			parameterFilterMask = (params[:, parameterIndex] == parameterCalcIndex).reshape(-1, 1)
			pMarg[parameterCalcIndex] = numpy.sum(numpy.multiply(prob, parameterFilterMask))

		return pMarg.T

	def getParameterEstimates(self, mapped=True):
		# Calculate a mean value for each of the estimated parameters
		estimatedParamMeans = numpy.zeros((len(self.parameterRanges), 1))
		for n, parameterRange in enumerate(self.parameterRanges):
			pMarg = self.margin(self.probabilities, n)
			estimatedParamMeans[n] = numpy.dot(pMarg, numpy.arange(parameterRange))

		if mapped:
			return mapCSFParams(estimatedParamMeans.T).T[0]
		else:
			return estimatedParamMeans

	# Plot the current state
	def visual(self, qcsf, unmappedTrueParams):
		estimatedParamMeans = qcsf.getParameterEstimates(mapped=False)
		frequencyDomain = numpy.arange(qcsf.stimulusRanges[1]).reshape(-1,1)

		truthData = qcsf.csf(unmappedTrueParams.reshape(1, -1), frequencyDomain)
		estimatedData = qcsf.csf(estimatedParamMeans.reshape(1, -1), frequencyDomain)

		data = numpy.concatenate((truthData, estimatedData), 1)

		graph.clear()
		graph.plot(frequencyDomain, data)

		positives = {'c':[], 'f':[]}
		negatives = {'c':[], 'f':[]}

		for record in qcsf.responseHistory:
			stimParamIndices = unroll(record[0], self.stimulusRanges, 0)
			stimParamValues = mapStimParams(stimParamIndices)
			
			if record[1]:
				whichList = positives
			else:
				whichList = negatives

			whichList['c'].append(stimParamValues[0])
			whichList['f'].append(stimParamValues[1])

		graph.plot(positives['f'], positives['c'], 'g^')
		graph.plot(negatives['f'], negatives['c'], 'rv')

		graph.grid()
		graph.set_ylim((0,3))
		plt.pause(0.001)

	# @TODO: move this out of the class
	def sim(self, parameters, stimulusIndex):
		p = self._pmeas(parameters, stimulusIndex)
		response = numpy.random.rand()<p
		return response

if __name__ == '__main__':
	import pathlib

	numpy.random.seed()

	saveImages = False
	indexLookupFixed = False
	
	pathlib.Path('logs').mkdir(parents=True, exist_ok=True) 
	logging.basicConfig(filename='logs/%d.log' % time.time(), level=logging.DEBUG)

	if saveImages:
		pathlib.Path('figs').mkdir(parents=True, exist_ok=True) 


	fig = plt.figure()
	graph = fig.add_subplot(1, 1, 1)
	plt.ion()
	plt.show()

	if indexLookupFixed:
		stimulusSpace = numpy.array([
			numpy.linspace(.1, 1, 24),	# Contrast
			numpy.linspace(.2, 36, 31)	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.linspace(2, 2000, 28),	# Peak sensitivity
			numpy.linspace(.2, 20, 21),		# Peak frequency
			numpy.linspace(1, 9, 21),		# Log bandwidth
			numpy.linspace(.02, 2, 21)		# Log delta (truncation)
		])
	else:
		stimulusSpace = numpy.array([
			numpy.arange(0, 24),	# Contrast
			numpy.arange(0, 31),	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.arange(0, 28),	# Peak sensitivity
			numpy.arange(0, 21),	# Peak frequency
			numpy.arange(0, 21),	# Log bandwidth
			numpy.arange(0, 21)		# Low frequency truncation (log delta)
		])


	unmappedTrueParams = numpy.array([[20, 11, 8, 11]])
	qcsf = QCSF(stimulusSpace, parameterSpace)

	# Trial loop
	for i in range(100):
		# Get the next stimulus
		logging.info(f'**************** CALCULATING NEXT **************** {i}')
		newStimValues = qcsf.next()

		logging.debug('****************** SIMUL RESPON ******************')
		# Simulate a response
		response = qcsf.sim(unmappedTrueParams, qcsf.currentStimulusIndex).item(0)

		logging.debug('**************** MARKING RESPONSE **************')
		qcsf.markResponse(response)
		
		logging.debug('****************** UPDATE VISUL ******************')
		# Update the plot
		qcsf.visual(qcsf, unmappedTrueParams)
		if saveImages:
			plt.savefig('figs/%d.png' % int(time.time()*1000))

	print('DONE')
	for record in qcsf.responseHistory:
		stimIndex = numpy.array([record[0]]).reshape(1,1)
		stimParamIndices = unroll(stimIndex, qcsf.stimulusRanges, 0)
		stimParamValues = mapStimParams(stimParamIndices)
		print(stimIndex, stimParamIndices[0], stimParamValues, record[1])

	plt.ioff()
	plt.show()


