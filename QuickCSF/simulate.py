import logging
import time
import math

import numpy

import matplotlib
import matplotlib.pyplot as plt
import pathlib

import QuickCSF
from QuickCSF import QuickCSFEstimator


# Plot the current state
def plot(qCSFEstimator, graph, unmappedTrueParams=None, showNumbers=False):
	estimatedParamMeans = qCSFEstimator.getBestParameters(leaveAsIndices=True)
	frequencyDomain = numpy.arange(qCSFEstimator.stimulusRanges[1]).reshape(-1,1)

	if unmappedTrueParams is not None:
		truthData = qCSFEstimator.csf(unmappedTrueParams.reshape(1, -1), frequencyDomain)
	else:
		truthData = None
	estimatedData = qCSFEstimator.csf(estimatedParamMeans.reshape(1, -1), frequencyDomain)
	
	# Convert from log-base to linear
	frequencyDomain = numpy.power(10, frequencyDomain/10 - 0.7)
	estimatedData = numpy.power(10, estimatedData)
	if truthData is not None:
		truthData = numpy.power(10, truthData)

	positives = {'c':[], 'f':[]}
	negatives = {'c':[], 'f':[]}

	# Chart responses
	for record in qCSFEstimator.responseHistory:
		stimIndices = qCSFEstimator.inflateStimulusIndex(record[0])
		stimValues = QuickCSF.mapStimParams(stimIndices, True).T
		
		if record[1]:
			positives['c'].append(stimValues.item(0))
			positives['f'].append(stimValues.item(1))
		else:
			negatives['c'].append(stimValues.item(0))
			negatives['f'].append(stimValues.item(1))

	# plot all of the data
	if truthData is not None:
		truthLine, = graph.plot(frequencyDomain, truthData, linestyle=':', color='gray')
	estimatedLine, = graph.plot(frequencyDomain, estimatedData, linewidth=2.5)
	graph.plot(positives['f'], positives['c'], 'g^')
	graph.plot(negatives['f'], negatives['c'], 'rv')

	graph.set_xlabel('Spatial frequency (CPD)')
	graph.set_xscale('log')
	graph.set_xlim((.5, 40))
	graph.set_xticks([1, 2, 4, 8, 16, 32])
	graph.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

	graph.set_ylabel('Sensitivity (1/contrast)')
	graph.set_yscale('log')
	graph.set_ylim((0.5, 400))
	graph.set_yticks([2, 10, 50, 200])
	graph.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

	graph.grid()

	if showNumbers:
		paramEstimates = qCSFEstimator.getBestParameters().tolist()[0]
		paramEstimates = '%03.2f, %.4f, %.4f, %.4f' % tuple(paramEstimates)
		estimatedLine.set_label(f'Estim: {paramEstimates}')

		if truthData is not None:
			trueParams = QuickCSF.mapCSFParams(unmappedTrueParams, True).T.tolist()[0]
			trueParams = '%03.2f, %.4f, %.4f, %.4f' % tuple(trueParams)
			truthLine.set_label(f'Truth: {trueParams}')

		graph.legend()

	plt.pause(0.001) # necessary for non-blocking graphing

def simulateResponse(qCSFEstimator, parameters, stimulusIndex):
	p = qCSFEstimator._pmeas(parameters, stimulusIndex)
	return numpy.random.rand() < p


def runSimulation(trueParameters=[20, 11, 12, 11], saveImages=False, usePerfectResponses=False):
	numpy.random.seed()

	indexLookupFixed = False

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
			#numpy.arange(0, 31),	# Contrast
			#numpy.arange(0, 24),	# Frequency
			numpy.arange(0, 24),	# Contrast
			numpy.arange(0, 20),	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.arange(0, 28),	# Peak sensitivity
			numpy.arange(0, 21),	# Peak frequency
			numpy.arange(0, 21),	# Log bandwidth
			numpy.arange(0, 21)		# Low frequency truncation (log delta)
		])

	unmappedTrueParams = numpy.array([trueParameters])
	qcsf = QuickCSFEstimator(stimulusSpace, parameterSpace)

	fig = plt.figure()
	graph = fig.add_subplot(1, 1, 1)

	plt.ion()
	plt.show()

	plot(qcsf, graph, unmappedTrueParams)

	# Trial loop
	for i in range(24):
		# Get the next stimulus
		newStimValues = qcsf.next()

		logging.debug('****************** SIMUL RESPON ******************')
		# Simulate a response
		if usePerfectResponses:
			frequencyIndex = newStimValues[:,1]
			vals = QuickCSF.mapStimParams(newStimValues, True).T
			trueSensitivity = numpy.power(10, qcsf.csf(unmappedTrueParams, numpy.array([frequencyIndex])))

			response = trueSensitivity > vals[:,0]
		else:
			response = simulateResponse(qcsf, unmappedTrueParams, qcsf.currentStimulusIndex).item(0)

		qcsf.markResponse(response)
		
		# Update the plot
		graph.clear()
		graph.set_title(f'Estimated Contrast Sensitivity Function ({i+1})')
		plot(qcsf, graph, unmappedTrueParams, True)

		if saveImages:
			plt.savefig('figs/%d.png' % int(time.time()*1000))

	print('DONE')
	print('*******')
	for record in qcsf.responseHistory:
		stimIndex = numpy.array([record[0]]).reshape(1,1)
		stinIndices = qcsf.inflateStimulusIndex(stimIndex)
		stimParamValues = QuickCSF.mapStimParams(stinIndices, True)
		print(stimIndex.item(0), stinIndices[0], stimParamValues.T[0], record[1])

	print('*******')
	paramEstimates = qcsf.getBestParameters()
	trueParams = QuickCSF.mapCSFParams(unmappedTrueParams, True).T
	print(f'Estimates = {paramEstimates}')
	print(f'Actuals = {trueParams}')

	plt.ioff()
	plt.show()
#	plt.close()


if __name__ == '__main__':
	runSimulation(usePerfectResponses=True)
