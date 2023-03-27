# -*- coding: utf-8 -*
'''Simulate a QuickCSF experiment'''

import logging
import argparse
import time
import math

import numpy

import matplotlib.pyplot as plt
import pathlib
import argparseqt.gui
import argparseqt.groupingTools

from . import QuickCSF
from .plot import plot

logger = logging.getLogger('QuickCSF.simulate')

def runSimulation(
	trials=30,
	imagePath=None,
	usePerfectResponses=False,
	stimuli={
		'minContrast':0.01, 'maxContrast':1, 'contrastResolution':24,
		'minFrequency':.2, 'maxFrequency':36, 'frequencyResolution':20,
	},
	parameters={
		'truePeakSensitivity':18, 'truePeakFrequency':11,
		'trueBandwidth':12, 'trueDelta':11,
	},
):
	logger.info('Starting simulation')

	numpy.random.seed()

	if imagePath is not None:
		pathlib.Path(imagePath).mkdir(parents=True, exist_ok=True)

	stimulusSpace = [
		QuickCSF.makeContrastSpace(stimuli['minContrast'], stimuli['maxContrast'], stimuli['contrastResolution']),
		QuickCSF.makeFrequencySpace(stimuli['minFrequency'], stimuli['maxFrequency'], stimuli['frequencyResolution'])
	]

	unmappedTrueParams = numpy.array([[
		parameters['truePeakSensitivity'],
		parameters['truePeakFrequency'],
		parameters['trueBandwidth'],
		parameters['trueDelta'],
	]])
	qcsf = QuickCSF.QuickCSFEstimator(stimulusSpace)

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
			trueSens = numpy.power(10, QuickCSF.csf_unmapped(unmappedTrueParams, numpy.array([frequency])))
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

	trueParams = QuickCSF.mapCSFParams(unmappedTrueParams, True).T
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
	stimuliSettings.add_argument('-minc', '--minContrast', type=float, default=.01, help='The lowest contrast value to measure (0.0-1.0)')
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

	settings = argparseqt.groupingTools.parseIntoGroups(parser)
	if settings['trials'] is None:
		from qtpy import QtWidgets
		from . import ui
		app = QtWidgets.QApplication()
		settings = ui.getSettings(parser, settings, ['trials'])

	if settings is not None:
		runSimulation(**settings)
