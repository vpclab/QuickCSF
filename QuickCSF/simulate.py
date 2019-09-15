# -*- coding: utf-8 -*
'''Simulate a QuickCSF experiment'''

import logging
import argparse
import time
import math

import numpy

import matplotlib
import matplotlib.pyplot as plt
import pathlib
import argparseqt.gui
import argparseqt.groupingTools

from . import QuickCSF

logger = logging.getLogger('QuickCSF.simulate')

def plot(qCSFEstimator, graph=None, unmappedTrueParams=None, showNumbers=True):
	'''Generate a plot of estimates from QuickCSF, along with history of responses and true parameter values'''

	if graph is None:
		fig = plt.figure()
		graph = fig.add_subplot(1, 1, 1)

		plt.ion()
		plt.show()

	frequencyDomain = QuickCSF.makeFrequencySpace(.005, 80, 50).reshape(-1,1)

	if unmappedTrueParams is not None:
		truthData = QuickCSF.csf_unmapped(unmappedTrueParams.reshape(1, -1), qCSFEstimator.parameterSpace, frequencyDomain)
		truthData = numpy.power(10, truthData)
		truthLine = graph.fill_between(
			frequencyDomain.reshape(-1),
			truthData.reshape(-1),
			color=(1, 0, 0, .5)
		)
	else:
		truthData = None

	estimatedParamMeans = qCSFEstimator.getResults(leaveAsIndices=True)
	estimatedData = QuickCSF.csf_unmapped(estimatedParamMeans.reshape(1, -1), qCSFEstimator.parameterSpace, frequencyDomain, True)
	estimatedData = numpy.power(10, estimatedData)

	estimatedLine = graph.fill_between(
		frequencyDomain.reshape(-1),
		estimatedData.reshape(-1),
		color=(0, 0, 1, .4)
	)

	## Chart responses
	positives = {'f':[], 's':[]}
	negatives = {'f':[], 's':[]}
	for record in qCSFEstimator.responseHistory:
		stimValues = record[0]
		targetArray = positives if record[1] else negatives
		targetArray['f'].append(stimValues[1])
		targetArray['s'].append(1/stimValues[0])

	graph.plot(positives['f'], positives['s'], 'o', markersize=4, color=(.2, 1, .2))
	graph.plot(negatives['f'], negatives['s'], 'x', markersize=5, color=(1,0,0), markeredgewidth=2)

	graph.set_xlabel('Spatial frequency (CPD)')
	graph.set_xscale('log')
	graph.set_xlim((.25, 64))
	graph.set_xticks([1, 2, 4, 8, 16, 32])
	graph.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

	graph.set_ylabel('Sensitivity (1/contrast)')
	graph.set_yscale('log')
	graph.set_ylim((1, 400))
	graph.set_yticks([2, 10, 50, 200])
	graph.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

	graph.grid()

	if showNumbers:
		estimatedParamMeans = QuickCSF.mapCSFParams(estimatedParamMeans, qCSFEstimator.parameterSpace, exponify=True, continuous=True)
		estimatedParamMeans = estimatedParamMeans.reshape(1,-1).tolist()[0]
		paramEstimates = '%03.2f, %.4f, %.4f, %.4f' % tuple(estimatedParamMeans)
		estimatedLine.set_label(f'Estim: {paramEstimates}')

		if truthData is not None:
			trueParams = QuickCSF.mapCSFParams(unmappedTrueParams, qCSFEstimator.parameterSpace, True).T.tolist()[0]
			trueParams = '%03.2f, %.4f, %.4f, %.4f' % tuple(trueParams)
			truthLine.set_label(f'Truth: {trueParams}')

		graph.legend()

	plt.pause(0.001) # necessary for non-blocking graphing

	return graph

def runSimulation(
	trials=30,
	imagePath=None,
	usePerfectResponses=False,
	stimuli={
		'minContrast':0.001, 'maxContrast':1, 'contrastResolution':24,
		'minFrequency':.2, 'maxFrequency':36, 'frequencyResolution':20,
	},
	parameters={
		'truePeakSensitivity':18, 'truePeakFrequency':11,
		'trueBandwidth':12, 'trueDelta':11,
		'minPeakSensitivity':2, 'maxPeakSensitivity':1000, 'peakSensitivityResolution':28,
		'minPeakFrequency':0.2, 'maxPeakFrequency':20, 'peakFrequencyResolution': 21,
		'minBandwidth':1, 'maxBandwidth':10, 'bandwidthResolution': 21,
		'minLogDelta':0.02, 'maxLogDelta':2, 'logDeltaResolution': 21,
	},
):
	logger.info('Starting simulation')

	numpy.random.seed()

	if imagePath is not None:
		pathlib.Path(imagePath).mkdir(parents=True, exist_ok=True)

	stimulusSpace = numpy.array([
		QuickCSF.makeContrastSpace(stimuli['minContrast'], stimuli['maxContrast'], stimuli['contrastResolution']),
		QuickCSF.makeFrequencySpace(stimuli['minFrequency'], stimuli['maxFrequency'], stimuli['frequencyResolution'])
	])
	parameterSpace = numpy.array([
		QuickCSF.makePeakSensitivitySpace(parameters['minPeakSensitivity'], parameters['maxPeakSensitivity'], parameters['peakSensitivityResolution']), # Peak sensitivity
		QuickCSF.makePeakFrequencySpace(parameters['minPeakFrequency'], parameters['maxPeakFrequency'], parameters['peakFrequencyResolution']),          # Peak frequency
		QuickCSF.makeBandwidthSpace(parameters['minBandwidth'], parameters['maxBandwidth'], parameters['bandwidthResolution']),                         # Log bandwidth
		QuickCSF.makeLogDeltaSpace(parameters['minLogDelta'], parameters['maxLogDelta'], parameters['logDeltaResolution'])                              # Low frequency truncation (log delta)
	])

	unmappedTrueParams = numpy.array([[
		parameters['truePeakSensitivity'],
		parameters['truePeakFrequency'],
		parameters['trueBandwidth'],
		parameters['trueDelta'],
	]])
	qcsf = QuickCSF.QuickCSFEstimator(parameterSpace, stimulusSpace)

	graph = plot(qcsf, unmappedTrueParams=unmappedTrueParams)

	# Trial loop
	for i in range(trials):
		# Get the next stimulus
		stimulus = qcsf.next()
		newStimValues = numpy.array([[stimulus.contrast, stimulus.frequency]])

		# Simulate a response
		if usePerfectResponses:
			logger.debug('Simulating perfect response')
			frequency = newStimValues[:,1]
			trueSens = numpy.power(10, QuickCSF.csf_unmapped(unmappedTrueParams, qcsf.parameterSpace, numpy.array([frequency])))
			testContrast = newStimValues[:,0]
			testSens = 1 / testContrast

			response = trueSens > testSens
		else:
			logger.debug('Simulating human response response')
			p = qcsf._pmeas(unmappedTrueParams)
			response = numpy.random.rand() < p

		qcsf.markResponse(response)

		# Update the plot
		graph.clear()
		graph.set_title(f'Estimated Contrast Sensitivity Function ({i+1})')
		plot(qcsf, graph, unmappedTrueParams)

		if imagePath is not None:
			plt.savefig(pathlib.Path(imagePath+'/%f.png' % time.time()).resolve())

	logger.info('Simulation complete')
	print('******* History *******')
	for record in qcsf.responseHistory:
		print(f'\tf={record[0][1]},c={record[0][0]},r={record[1]}')

	print('***********************')

	paramEstimates = qcsf.getResults()
	logger.info('Results: ' + str(paramEstimates))

	trueParams = QuickCSF.mapCSFParams(unmappedTrueParams, qcsf.parameterSpace, True).T
	print('******* Results *******')
	print(f'\tEstimates = {paramEstimates}')
	print(f'\tActuals = {trueParams}')
	print('***********************')
	plt.ioff()
	plt.show()

def entropyPlot(qcsf):
	params = numpy.arange(qcsf.paramComboCount).reshape(-1, 1)
	stims = numpy.arange(qcsf.stimComboCount).reshape(-1,1)

	p = qcsf._pmeas(params, stims)

	pbar = sum(p)/len(params)
	hbar = sum(QuickCSF.entropy(p))/len(params)
	gain = QuickCSF.entropy(pbar)-hbar


	gain = -gain.reshape(qcsf.stimulusRanges[::-1]).T

	fig = plt.figure()
	graph = fig.add_subplot(1, 1, 1)
	plt.imshow(gain, cmap='hot')

	plt.ioff()
	plt.show()


if __name__ == '__main__':
	from . import log
	log.startLog()

	parser = argparse.ArgumentParser()

	parser.add_argument('-n', '--trials', type=int, help='Number of trials to simulate')
	parser.add_argument('--imagePath', default=None, help='If specified, path to save images')
	parser.add_argument('-perfect', '--usePerfectResponses', default=False, action='store_true', help='Whether to simulate perfect responses, rather than probablistic ones')

	stimuliSettings = parser.add_argument_group('stimuli')
	stimuliSettings.add_argument('-minc', '--minContrast', type=float, default=.001, help='The lowest contrast value to measure (0.0-1.0)')
	stimuliSettings.add_argument('-maxc', '--maxContrast', type=float, default=1.0, help='The highest contrast value to measure (0.0-1.0)')
	stimuliSettings.add_argument('-cr', '--contrastResolution', type=int, default=24, help='The number of contrast steps')

	stimuliSettings.add_argument('-minf', '--minFrequency', type=float, default=0.2, help='The lowest frequency value to measure (cycles per degree)')
	stimuliSettings.add_argument('-maxf', '--maxFrequency', type=float, default=36.0, help='The highest frequency value to measure (cycles per degree)')
	stimuliSettings.add_argument('-fr', '--frequencyResolution', type=int, default=20, help='The number of frequency steps')

	parameterSettings = parser.add_argument_group('parameters')
	parameterSettings.add_argument('-s', '--truePeakSensitivity', type=int, default=18, help='True peak sensitivity (index)')
	parameterSettings.add_argument('-f', '--truePeakFrequency', type=int, default=11, help='True peak frequency (index)')
	parameterSettings.add_argument('-b', '--trueBandwidth', type=int, default=12, help='True bandwidth (index)')
	parameterSettings.add_argument('-d', '--trueDelta', type=int, default=11, help='True delta truncation (index)')

	parameterSettings.add_argument('-minps', '--minPeakSensitivity', type=float, default=2.0, help='The lower bound of peak sensitivity value (>1.0)')
	parameterSettings.add_argument('-maxps', '--maxPeakSensitivity', type=float, default=1000.0, help='The upper bound of peak sensitivity value')
	parameterSettings.add_argument('-psr', '--peakSensitivityResolution', type=int, default=28, help='The number of peak sensitivity steps')
	
	parameterSettings.add_argument('-minpf', '--minPeakFrequency', type=float, default=.2, help='The lower bound of peak frequency value (>0)')
	parameterSettings.add_argument('-maxpf', '--maxPeakFrequency', type=float, default=20.0, help='The upper bound of peak frequency value')
	parameterSettings.add_argument('-pfr', '--peakFrequencyResolution', type=int, default=21, help='The number of peak frequency steps')
	
	parameterSettings.add_argument('-minb', '--minBandwidth', type=float, default=1.0, help='The lower bound of bandwidth value')
	parameterSettings.add_argument('-maxb', '--maxBandwidth', type=float, default=10.0, help='The upper bound of bandwidth value')
	parameterSettings.add_argument('-br', '--bandwidthResolution', type=int, default=21, help='The number of bandwidth steps')
	
	parameterSettings.add_argument('-mind', '--minLogDelta', type=float, default=.02, help='The lower bound of logdelta value')
	parameterSettings.add_argument('-maxd', '--maxLogDelta', type=float, default=2.0, help='The upper bound of logdelta value')
	parameterSettings.add_argument('-dr', '--logDeltaResolution', type=int, default=21, help='The number of logdelta steps')

	settings = argparseqt.groupingTools.parseIntoGroups(parser)
	if settings['trials'] is None:
		from qtpy import QtWidgets
		from . import ui
		app = QtWidgets.QApplication()
		settings = ui.getSettings(parser, settings, ['trials'])

	if settings is not None:
		# parameter validation: peak sensitivty space and peak frequency space should be subspaces of stimulus spaces (1/contrast, frequency)
		if not (settings['parameters']['minPeakSensitivity'] >= 1/settings['stimuli']['maxContrast'] and settings['parameters']['maxPeakSensitivity'] <= 1/settings['stimuli']['minContrast']):
			raise ValueError("Please increase the range of contrast space or decrease the range of peak sensitivity space.")
		if not (settings['parameters']['minPeakFrequency'] >= settings['stimuli']['minFrequency'] and settings['parameters']['maxPeakFrequency'] <= settings['stimuli']['maxFrequency']):
			raise ValueError("Please increase the range of frequency space or decrease the range of peak frequency space.")

		runSimulation(**settings)
