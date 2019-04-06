import logging
import time
import math

import numpy

import matplotlib
import matplotlib.pyplot as plt
import pathlib

import QuickCSF
from QuickCSF import QuickCSFEstimator

def mapStimParams(params, exponify=False):
	sensitivity = 0.1*params[:,0]
	frequency = -0.7 + 0.1*params[:,1]

	if exponify:
		sensitivity = numpy.power(10, sensitivity)
		frequency = numpy.power(10, frequency)

	return numpy.stack((sensitivity, frequency))

# Plot the current state
def plot(qCSFEstimator, graph, unmappedTrueParams=None, showNumbers=False):
	#frequencyDomain = qCSFEstimator.stimulusSpace[1].reshape(-1,1)
	frequencyDomain = QuickCSF.makeFrequencySpace(.005, 64, 50).reshape(-1,1)

	if unmappedTrueParams is not None:
		truthData = qCSFEstimator.csf(unmappedTrueParams.reshape(1, -1), frequencyDomain)
		truthData = numpy.power(10, truthData)
		truthLine, = graph.plot(frequencyDomain, truthData, linestyle=':', color='gray')

	estimatedParamMeans = qCSFEstimator.getBestParameters(leaveAsIndices=True)
	estimatedData = qCSFEstimator.csf(estimatedParamMeans.reshape(1, -1), frequencyDomain)
	estimatedData = numpy.power(10, estimatedData)
	estimatedLine, = graph.plot(frequencyDomain, estimatedData, linewidth=2.5)
	
	## Chart responses
	positives = {'f':[], 's':[]}
	negatives = {'f':[], 's':[]}
	for record in qCSFEstimator.responseHistory:
		#stimIndices = qCSFEstimator.inflateStimulusIndex(record[0])
		#stimValues = mapStimParams(stimIndices, True).T
		stimValues = record[0]
		targetArray = positives if record[1] else negatives
		targetArray['f'].append(stimValues[1])
		targetArray['s'].append(1/stimValues[0])

	graph.plot(positives['f'], positives['s'], 'g^')
	graph.plot(negatives['f'], negatives['s'], 'rv')

	graph.set_xlabel('Spatial frequency (CPD)')
	graph.set_xscale('log')
	graph.set_xlim((.125, 64))
	graph.set_xticks([1, 2, 4, 8, 16, 32])
	graph.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

	graph.set_ylabel('Sensitivity (1/contrast)')
	graph.set_yscale('log')
	graph.set_ylim((1, 400))
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


def runSimulation(trueParameters=[20, 11, 12, 11], iterations=30, saveImages=False, usePerfectResponses=False):
	numpy.random.seed()

	indexLookupFixed = False

	if saveImages:
		pathlib.Path('figs').mkdir(parents=True, exist_ok=True) 

#		parameterSpace = numpy.array([
#			numpy.linspace(2, 2000, 28),	# Peak sensitivity
#			numpy.linspace(.2, 20, 21),		# Peak frequency
#			numpy.linspace(1, 9, 21),		# Log bandwidth
#			numpy.linspace(.02, 2, 21)		# Log delta (truncation)
#		])
	stimulusSpace = numpy.array([
		QuickCSF.makeContrastSpace(),
		QuickCSF.makeFrequencySpace()
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
	for i in range(iterations):
		# Get the next stimulus
		newStimValues = qcsf.next()
		
		logging.debug('****************** SIMUL RESPON ******************')
		# Simulate a response
		if usePerfectResponses:
			
			frequency = newStimValues[:,1]
			trueSens = numpy.power(10, qcsf.csf(unmappedTrueParams, numpy.array([frequency])))
			testContrast = newStimValues[:,0]
			testSens = 1 / testContrast

			response = trueSens > testSens
		else:
			response = simulateResponse(qcsf, unmappedTrueParams, qcsf.currentStimulusIndex).item(0)

		qcsf.markResponse(response)
		
		# Update the plot
		graph.clear()
		graph.set_title(f'Estimated Contrast Sensitivity Function ({i+1})')
		plot(qcsf, graph, unmappedTrueParams, False)

		if saveImages:
			plt.savefig('figs/%d.png' % int(time.time()*1000))

	print('DONE')
	print('*******')
	for record in qcsf.responseHistory:
		print(f'f={record[0][1]},c={record[0][0]},r={record[1]}')

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
