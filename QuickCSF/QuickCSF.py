import numpy
import logging
import time
import math

def mapStimParams(params, exponify=False):
	sensitivity = 0.1*params[:,0]
	frequency = -0.7 + 0.1*params[:,1]

	if exponify:
		sensitivity = numpy.power(10, sensitivity)
		frequency = numpy.power(10, frequency)

	return numpy.stack((sensitivity, frequency))


def mapCSFParams(params, exponify=False):
	'''
		Maps parameter indices to log values

		Exponify will de-log them, leaving the following units:
			Peak Sensitivity: 1/contrast
			Peak Frequency: cycles per degree
			Bandwidth: octaves
			Delta: 1/contrast (Difference between Peak Sensitivity and the truncation)
	'''
	peakSensitivity = 0.1*params[:,0] + 0.3
	peakFrequency = -0.7 + 0.1*params[:,1]
	bandwidth = 0.05 * params[:,2]
	logDelta = -1.7 + 0.1 * params[:,3]
	delta = numpy.power(10, logDelta)

	if exponify:
		deltaDiff = numpy.power(10, peakSensitivity-delta)

		peakSensitivity = numpy.power(10, peakSensitivity)
		peakFrequency = numpy.power(10, peakFrequency)
		bandwidth = numpy.power(10, bandwidth)
		delta = peakSensitivity - deltaDiff

	return numpy.stack((peakSensitivity, peakFrequency, bandwidth, delta))

def entropy(p):
	return numpy.multiply(-p, numpy.log(p)) - numpy.multiply(1-p, numpy.log(1-p))

class QuickCSFEstimator():
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
		stimIndicies = numpy.arange(self.stimComboCount).reshape(-1,1)
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
		self.currentStimParamIndices = self.inflateStimulusIndex(self.currentStimulusIndex)

		return self.currentStimParamIndices

	def _inflate(self, index, ranges):
		dimensions = len(ranges)
		indices = index.repeat(dimensions, 1)

		for i in range(dimensions-1):
			indices[:, i] = numpy.mod(indices[:, -1], ranges[i])
			indices[:, -1] = numpy.floor(indices[:, -1] / ranges[i])

		return indices

	def inflateParameterIndex(self, parameterIndex):
		'''
			Convert (x,1) to (x,4)
		'''
		return self._inflate(parameterIndex, self.parameterRanges)

	def inflateStimulusIndex(self, stimulusIndex):
		'''
			Convert (1,x) to (2,x)
		'''
		return self._inflate(stimulusIndex, self.stimulusRanges)

	def _pmeas(self, parameterIndex, stimulusIndex):
		# Check if param list is a single-dimension
		if parameterIndex.shape[1] == 1:
			# If it's a single dimension, we need to unroll it into 4 separate ones
			#parameters = unroll(parameters, self.parameterRanges, 1)
			parameters = self.inflateParameterIndex(parameterIndex)
		else:
			parameters = parameterIndex

		# Unroll into separate rows
		stimulusIndices = self.inflateStimulusIndex(stimulusIndex)

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
			csfValues = self.csf(parameters, stimulusIndices[:,1].reshape(1,-1))

		sensitivity = 0.1 * stimulusIndices[:,0]
		sensitivity = numpy.ones((parameters.shape[0], 1)) * sensitivity

		return 1 - numpy.divide(self.d, 1+numpy.exp((csfValues-sensitivity) / self.sig))

	def csf(self, parameters, freqNum):
		'''
			The parametric contrast-sensitivity function
			Param order = peak sensitivity, peak frequency, bandwidth, log delta
			@TODO: move this out of the class
			Expects UNMAPPED parameters and frequencyNum
		'''
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

	def getStimIndex(self, stimValues):
		for i in range(self.stimComboCount):
			stimIndicies = self.inflateStimulusIndex(numpy.array([[i]]))
			searchStimValues = mapStimParams(stimIndicies, True)
			for j,v in enumerate(searchStimValues):
				if not math.isclose(v, stimValues[j], abs_tol=.0001):
					break	# break the j loop, causing the next i to start
			else:
				# the j loop did not break, so all values from i were close enough
				return i
		else:
			print('Could not find stim index for', stimValues)

	def markResponse(self, response, stimIndex=None):
		if stimIndex is None:
			stimIndex = self.currentStimulusIndex
		self.responseHistory.append([stimIndex, response])

		pm = self._pmeas(
			numpy.arange(self.paramComboCount)[:,numpy.newaxis],
			stimIndex
		)

		if response:
			self.probabilities = numpy.multiply(self.probabilities, pm)
		else:
			self.probabilities = numpy.multiply(self.probabilities, (1-pm))

		# Normalize probabilities
		self.probabilities = self.probabilities/numpy.sum(self.probabilities)

	def margin(self, parameterIndex):
		params = numpy.arange(self.paramComboCount).reshape(-1,1)
		params = self.inflateParameterIndex(params)
		
		pMarg = numpy.zeros((self.parameterRanges[parameterIndex], 1))
		for parameterCalcIndex in range(self.parameterRanges[parameterIndex]):
			# Filter out all the other parameters' values
			parameterFilterMask = (params[:, parameterIndex] == parameterCalcIndex).reshape(-1, 1)
			pMarg[parameterCalcIndex] = numpy.sum(numpy.multiply(self.probabilities, parameterFilterMask))

		return pMarg

	def getBestParameters(self, leaveAsIndices=False):
		params = numpy.arange(self.paramComboCount).reshape(-1,1)
		params = self.inflateParameterIndex(params)

		# Calculate a mean value for each of the estimated parameters
		estimatedParamMeans = numpy.zeros(len(self.parameterRanges))
		for n, parameterRange in enumerate(self.parameterRanges):
			pMarg = self.margin(n)
			estimatedParamMeans[n] = numpy.dot(pMarg.T, numpy.arange(parameterRange))

		estimatedParamMeans = estimatedParamMeans.reshape(1,len(self.parameterRanges))

		if leaveAsIndices:
			return estimatedParamMeans
		else:
			return mapCSFParams(estimatedParamMeans, True).T

