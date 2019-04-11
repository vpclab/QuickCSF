# -*- coding: utf-8 -*
'''Implementation of qCSF

	See Lesmes, L. A., Lu, Z. L., Baek, J., & Albright, T. D. (2010). Bayesian adaptive estimation of the contrast sensitivity function: The quick CSF method. Journal of vision, 10(3), 17-17.

	Assumes a 4-parameter model of CSF:
		Peak sensitivity: highest contrast level across all spatial frequencies
		Peak frequency: the spatial frequency at which peak sensitivity occurs
		Bandwidth: full-width at half-maximum
		Delta: difference between peak sensitivity and truncation at low-frequencies
'''

import logging

import time
import math

import numpy

logger = logging.getLogger(__name__)

class Stimulus:
	def __init__(self, contrast, frequency):
		self.contrast = contrast
		self.frequency = frequency

def makeContrastSpace(min=.01, max=1, count=24):
	'''Creates contrast values at log-linear equal1ly spaced intervals'''

	logger.debug('Making contrast space: ' + str(locals()))

	sensitivityRange = [1/min, 1/max]

	expRange = numpy.log10(sensitivityRange[0])-numpy.log10(sensitivityRange[1])
	expMin = numpy.log10(sensitivityRange[1])

	contrastSpace = numpy.array([0.] * count)
	for i in range(count):
		contrastSpace[count-i-1] = 1.0 / (
			10**((i/(count-1.))*expRange + expMin)
		)

	return contrastSpace

def makeFrequencySpace(min=.2, max=36, count=20):
	'''Creates frequency values at log-linear equally spaced intervals'''

	logger.debug('Making frequency space: ' + str(locals()))

	expRange = numpy.log10(max)-numpy.log10(min)
	expMin = numpy.log10(min)

	frequencySpace = numpy.array([0.] * count)
	for i in range(count):
		frequencySpace[i] = (
			10** ( (i/(count-1)) * expRange + expMin )
		)

	return frequencySpace

def csf(parameters, frequency):
	'''The truncated log-parabola model for human contrast sensitivity
	
		Expects UNMAPPED parameters
		Param order = peak sensitivity, peak frequency, bandwidth, log delta
	'''
	# Get everything into log-units
	[peakSensitivity, peakFrequency, logBandwidth, delta] = mapCSFParams(parameters)
	frequency = numpy.log10(frequency)

	n = len(peakSensitivity)
	m = len(frequency[0])

	frequency = frequency.repeat(n, 0)

	peakFrequency = peakFrequency[:,numpy.newaxis].repeat(m,1)
	peakSensitivity = peakSensitivity[:,numpy.newaxis].repeat(m,1)
	delta = delta[:,numpy.newaxis].repeat(m,1)
	
	divisor = numpy.log10(2)+logBandwidth
	divisor = divisor[:,numpy.newaxis].repeat(m,1)
	truncation = (4 * numpy.log10(2) * numpy.power(numpy.divide(frequency-peakFrequency, divisor), 2))
	
	logSensitivity = numpy.maximum(0, peakSensitivity - truncation)
	Scutoff = numpy.maximum(logSensitivity, peakSensitivity-delta)
	logSensitivity[frequency<peakFrequency] = Scutoff[frequency<peakFrequency]

	return logSensitivity

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
	def __init__(self, stimulusSpace=None):
		'''Create a new QuickCSF estimator with the specified input/output spaces

			Args:
				stimulusSpace: 2,x numpy array of attributes to be used for stimulus generation
					numpy.array([contrasts, frequencies])
		'''
		if stimulusSpace is None:
			stimulusSpace = numpy.array([
				makeContrastSpace(.0001, .05),
				makeFrequencySpace()
			])

		parameterSpace = numpy.array([
			numpy.arange(0, 28),	# Peak sensitivity
			numpy.arange(0, 21),	# Peak frequency
			numpy.arange(0, 21),	# Log bandwidth
			numpy.arange(0, 21)		# Low frequency truncation (log delta)
		])

		logger.info('Initializing QuickCSFEStimator')
		logger.debug('Initializing QuickCSFEstimator stimSpace='+str(stimulusSpace).replace('\n','')+', paramSpace='+str(parameterSpace).replace('\n',''))

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
		'''Determine the next stimulus to be tested'''

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

		return Stimulus(
			self.stimulusSpace[0][self.currentStimParamIndices[0][0]],
			self.stimulusSpace[1][self.currentStimParamIndices[0][1]]
		)

	def _inflate(self, index, ranges):
		'''Inflates a flattened list of indexes into lists of lists of indexes'''

		dimensions = len(ranges)
		indices = index.repeat(dimensions, 1)

		for i in range(dimensions-1):
			indices[:, i] = numpy.mod(indices[:, -1], ranges[i])
			indices[:, -1] = numpy.floor(indices[:, -1] / ranges[i])

		return indices

	def inflateParameterIndex(self, parameterIndex):
		'''Converts a flattened parameter index into its 4 constituent indices'''
		return self._inflate(parameterIndex, self.parameterRanges)

	def inflateStimulusIndex(self, stimulusIndex):
		'''Converts a flattened stimulus index into its 2 constituent indices'''
		return self._inflate(stimulusIndex, self.stimulusRanges)

	def _pmeas(self, parameterIndex, stimulusIndex=None):
		'''Calculates probability for a configuration of parameters'''

		# Check if param list is a single-dimension
		if parameterIndex.shape[1] == 1:
			# If it's a single dimension, we need to unroll it into 4 separate ones
			parameters = self.inflateParameterIndex(parameterIndex)
		else:
			parameters = parameterIndex

		# Unroll into separate rows
		if stimulusIndex is None:
			stimulusIndex = self.currentStimulusIndex

		stimulusIndices = self.inflateStimulusIndex(stimulusIndex)

		frequencies = self.stimulusSpace[1][stimulusIndices[:,1]].reshape(1,-1)
		csfValues = csf(parameters, frequencies)

		# Make vector of sensitivities
		contrast = self.stimulusSpace[0][stimulusIndices[:,0]]

		sensitivity = numpy.log10(
			numpy.ones((parameters.shape[0], 1)) * numpy.divide(1, contrast)
		)

		return 1 - numpy.divide(self.d, 1+numpy.exp((csfValues-sensitivity) / self.sig))

	def markResponse(self, response, stimIndex=None):
		'''Record an observer's response and update parameter probabilities
		
			Args:
				stimIndex: if not specified, will use the last stimulus generated by next()
		'''

		if type(response) == numpy.ndarray:
			response = response.item(0)

		if stimIndex is None:
			stimIndex = self.currentStimulusIndex
			stimIndices = self.inflateStimulusIndex(stimIndex)

		contrast = self.stimulusSpace[0][stimIndices[:,0]][0]
		frequency = self.stimulusSpace[1][stimIndices[:,1]][0]

		logger.info(f'Marking response {stimIndex}[c={contrast},f={frequency}] = {response}')

		self.responseHistory.append([
			[contrast, frequency],
			response
		])

		# get probability for this stimulus
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

	def getResults(self, leaveAsIndices=False):
		'''Calculate an estimate of all 4 parameters based on their probabilities
		
			Args:
				leaveAsIndicies: if False, will output real-world, linear-scale values
					if True, will output indices, which can be converted with `mapCSFParams()`
		'''

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
