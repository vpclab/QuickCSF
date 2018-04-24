import matplotlib
import matplotlib.pyplot as plt
import numpy
import logging
import time

def mapStimParams(params, exponify=False):
	sensitivity = 0.1*params[:,0]
	frequency = -0.7 + 0.1*params[:,1]

	if exponify:
		sensitivity = numpy.power(10, sensitivity)
		frequency = numpy.power(10, frequency)

	return numpy.stack((sensitivity, frequency))


# Returns logs of the things
def mapCSFParams(params, exponify=False):
	peakSensitivity = 0.1*params[:,0] + 0.3
	peakFrequency = -0.7 + 0.1*params[:,1]
	bandwidth = 0.05 * params[:,2]
	logDelta = -1.7 + 0.1 * params[:,3]
	delta = numpy.power(10, logDelta)

	if exponify:
		peakSensitivity = numpy.power(10, peakSensitivity)
		peakFrequency = numpy.power(10, peakFrequency)
		#bandwidth = numpy.power(10, bandwidth)
		#delta = numpy.power(10, delta)

	return numpy.stack((peakSensitivity, peakFrequency, bandwidth, delta))

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

	def markResponse(self, response):
		self.responseHistory.append([self.currentStimulusIndex, response])

		pm = self._pmeas(
			numpy.arange(self.paramComboCount)[:,numpy.newaxis],
			self.currentStimulusIndex
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

	# Plot the current state
	def visual(self, qcsf, unmappedTrueParams):
		estimatedParamMeans = qcsf.getBestParameters(leaveAsIndices=True)
		frequencyDomain = numpy.arange(qcsf.stimulusRanges[1]).reshape(-1,1)

		truthData = qcsf.csf(unmappedTrueParams.reshape(1, -1), frequencyDomain)
		estimatedData = qcsf.csf(estimatedParamMeans.reshape(1, -1), frequencyDomain)
		
		# Convert from log-base to linear
		frequencyDomain = numpy.power(10, frequencyDomain/10 - 0.7)
		truthData = numpy.power(10, truthData)
		estimatedData = numpy.power(10, estimatedData)

		data = numpy.concatenate((truthData, estimatedData), 1)

		positives = {'c':[], 'f':[]}
		negatives = {'c':[], 'f':[]}

		# Chart responses
		for record in qcsf.responseHistory:
			stimIndices = self.inflateStimulusIndex(record[0])
			stimValues = mapStimParams(stimIndices, True).T
			
			if record[1]:
				positives['c'].append(stimValues.item(0))
				positives['f'].append(stimValues.item(1))
			else:
				negatives['c'].append(stimValues.item(0))
				negatives['f'].append(stimValues.item(1))

		# plot all of the data
		graph.plot(frequencyDomain, data, marker='o')
		graph.plot(positives['f'], positives['c'], 'g^')
		graph.plot(negatives['f'], negatives['c'], 'rv')

		graph.set_xlabel('Spatial frequency (CPD)')
		graph.set_xscale('log')
		graph.set_xlim((.5, 40))
		graph.set_xticks([1, 2, 4, 8, 16, 32])
		graph.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

		graph.set_ylabel('Contrast sensitivity')
		graph.set_yscale('log')
		graph.set_ylim((0.5, 400))
		graph.set_yticks([2, 10, 50, 200])
		graph.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

		graph.grid()

		trueParams = mapCSFParams(unmappedTrueParams, True).T.tolist()[0]
		trueParams = '%03.2f, %.4f, %.4f, %.4f' % tuple(trueParams)
		graph.text(0.6, 1, f'Actual    : {trueParams}', fontweight='bold')

		paramEstimates = qcsf.getBestParameters().tolist()[0]
		paramEstimates = '%03.2f, %.4f, %.4f, %.4f' % tuple(paramEstimates)
		graph.text(0.6, .6, f'Estimate: {paramEstimates}', fontweight='bold')

		plt.pause(0.001) # necessary for non-blocking graphing

	# @TODO: move this out of the class
	def sim(self, parameters, stimulusIndex):
		p = self._pmeas(parameters, stimulusIndex)
		return numpy.random.rand()<p


if __name__ == '__main__':
	import pathlib

	numpy.random.seed()

	saveImages = False
	indexLookupFixed = False

	pathlib.Path('logs').mkdir(parents=True, exist_ok=True) 

	if saveImages:
		pathlib.Path('figs').mkdir(parents=True, exist_ok=True) 

	if indexLookupFixed:
		stimulusSpace = numpy.array([
			numpy.linspace(.1, 1, 31),	# Contrast
			numpy.linspace(.2, 36, 24)	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.linspace(2, 2000, 28),	# Peak sensitivity
			numpy.linspace(.2, 20, 21),		# Peak frequency
			numpy.linspace(1, 9, 21),		# Log bandwidth
			numpy.linspace(.02, 2, 21)		# Log delta (truncation)
		])
	else:
		stimulusSpace = numpy.array([
			numpy.arange(0, 31),	# Contrast
			numpy.arange(0, 24),	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.arange(0, 28),	# Peak sensitivity
			numpy.arange(0, 21),	# Peak frequency
			numpy.arange(0, 21),	# Log bandwidth
			numpy.arange(0, 21)		# Low frequency truncation (log delta)
		])

	unmappedTrueParams = numpy.array([[20, 11, 8, 11]])
	qcsf = QCSF(stimulusSpace, parameterSpace)

	fig = plt.figure()
	graph = fig.add_subplot(1, 1, 1)

	plt.ion()
	plt.show()

	qcsf.visual(qcsf, unmappedTrueParams)

	perfectResponsesOnly = False
	# Trial loop
	for i in range(10):
		# Get the next stimulus
		newStimValues = qcsf.next()

		logging.debug('****************** SIMUL RESPON ******************')
		# Simulate a response
		if perfectResponsesOnly:
			frequencyIndex = newStimValues[:,1]
			vals = mapStimParams(newStimValues, True).T
			trueSensitivity = numpy.power(10, qcsf.csf(unmappedTrueParams, numpy.array([frequencyIndex])))

			response = trueSensitivity > vals[:,0]
		else:
			response = qcsf.sim(unmappedTrueParams, qcsf.currentStimulusIndex).item(0)

		qcsf.markResponse(response)
		
		# Update the plot
		graph.clear()
		graph.set_title(f'Estimated Contrast Sensitivity Function ({i+1})')
		qcsf.visual(qcsf, unmappedTrueParams)

		if saveImages:
			plt.savefig('figs/%d.png' % int(time.time()*1000))

	print('DONE')
	print('*******')
	for record in qcsf.responseHistory:
		stimIndex = numpy.array([record[0]]).reshape(1,1)
		stinIndices = qcsf.inflateStimulusIndex(stimIndex)
		stimParamValues = mapStimParams(stinIndices, True)
		print(stimIndex.item(0), stinIndices[0], stimParamValues.T[0], record[1])

	print('*******')
	paramEstimates = qcsf.getBestParameters()
	trueParams = mapCSFParams(unmappedTrueParams, True).T
	print(f'Estimates = {paramEstimates}')
	print(f'Actuals = {trueParams}')

	plt.ioff()
	plt.show()
#	plt.close()


