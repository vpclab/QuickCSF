# -*- coding: utf-8 -*
'''An simple QuickCSF app to measure full contrast sensitivity function

	Executes a series of trials using 2AFC to measure CSF. Results are saved to a .CSF file.

	Example:
		$ python3 -m QuickCSF.app --help
		$ python3 -m QuickCSF.app -d 750 -s participant001
		$ python3 -m QuickCSF.app -d 750 --controller.trialsPerBlock 50 --controller.blockCount 2
'''

import logging

import argparse
import sys, pathlib, csv
import functools
from datetime import datetime

from qtpy import QtWidgets, QtCore
import argparseqt.groupingTools

from . import ui
from . import CSFController
from . import QuickCSF
from . import StimulusGenerators
from . import screens

logger = logging.getLogger('QuickCSF.app')

app = QtWidgets.QApplication()
app.setApplicationName('QuickCSF')
mainWindow = None
settings = None

def _onFinished(results):
	outputFile = pathlib.Path(settings['outputFile'])
	logger.debug('Writing output file: ' + str(outputFile.resolve()))

	fileExists = outputFile.exists()
	with outputFile.open('a') as csvFile:
		record = {
			'SessionID': settings['sessionID'],
			'Timestamp': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
			**results
		}

		writer = csv.DictWriter(csvFile, fieldnames=record.keys())
		if not fileExists:
			writer.writeheader()

		writer.writerow(record)

def _start():
	global mainWindow, settings

	def onStateTransition(state, data):
		if state == 'FINISHED':
			_onFinished(data)

	logger.debug('Showing main window')

	if settings['instructionsFile'] is not None and settings['instructionsFile'] != '':
		with open(settings['instructionsFile']) as instructionsFile:
			instructions = instructionsFile.read()
	else:
		instructions = None

	mainWindow = ui.QuickCSFWindow(instructions)

	degreesToPixels = functools.partial(screens.degreesToPixels, distance_mm=settings['distance_mm'])

	stimGenerator = StimulusGenerators.QuickCSFGenerator(degreesToPixels=degreesToPixels, **settings['Stimuli'], **settings['Parameters'])
	controller = CSFController.Controller_2AFC(stimGenerator, **settings['Controller'])

	mainWindow.participantReady.connect(controller.onParticipantReady)
	mainWindow.participantResponse.connect(controller.onParticipantResponse)

	controller.stateTransition.connect(mainWindow.onNewState)
	controller.stateTransition.connect(onStateTransition)

	QtCore.QTimer.singleShot(0, controller.start)
	mainWindow.showFullScreen()

def run(configuredSettings=None):
	'''Start the QuickCSF app'''
	global settings
	
	settings = configuredSettings

	ui.popupUncaughtExceptions()
	QtCore.QTimer.singleShot(0, lambda: _start())
	app.exec_()
	logger.info('App exited')

def getSettings():
	'''Parse command line arguments for the QuickCSF app. Will show a UI promptif necessary information is missing'''

	parser = argparse.ArgumentParser()
	parser.add_argument('-sid', '--sessionID', default=None, help='A unique string to identify this observer/session')
	parser.add_argument('-d', '--distance_mm', type=float, default=None, help='Distance (mm) from the display to the observer')
	parser.add_argument('--outputFile', default='data/QuickCSF-results.csv', help='The path/file to save results into')
	parser.add_argument('--instructionsFile', default=None, help='A plaintext file containing the instructions. If unspecified, default instructions will be displayed')

	controllerSettings = parser.add_argument_group('Controller')
	controllerSettings.add_argument('--trialsPerBlock', type=int, default=25, help='Number of trials in each block')
	controllerSettings.add_argument('--blockCount', type=int, default=4, help='Number of blocks')

	controllerSettings.add_argument('--fixationDuration', type=float, default=.25, help='How long (seconds) the fixation stimulus is displayed')
	controllerSettings.add_argument('--stimulusDuration', type=float, default=.1, help='How long (seconds) the stimulus is displayed')
	controllerSettings.add_argument('--maskDuration', type=float, default=.1, help='How long (seconds) the stimulus mask is displayed')
	controllerSettings.add_argument('--interStimulusInterval', type=float, default=.1, help='How long (seconds) a blank is displayed between stimuli')
	controllerSettings.add_argument('--feedbackDuration', type=float, default=.5, help='How long (seconds) feedback is displayed')

	controllerSettings.add_argument('--waitForReady', default=False, action='store_true', help='Wait for the participant to indicate they are ready for the next trial')

	stimulusSettings = parser.add_argument_group('Stimuli')
	stimulusSettings.add_argument('-minc', '--minContrast', type=float, default=.001, help='The lowest contrast value to measure (0.0-1.0)')
	stimulusSettings.add_argument('-maxc', '--maxContrast', type=float, default=1.0, help='The highest contrast value to measure (0.0-1.0)')
	stimulusSettings.add_argument('-cr', '--contrastResolution', type=int, default=24, help='The number of contrast steps')

	stimulusSettings.add_argument('-minf', '--minFrequency', type=float, default=0.2, help='The lowest frequency value to measure (cycles per degree)')
	stimulusSettings.add_argument('-maxf', '--maxFrequency', type=float, default=36.0, help='The highest frequency value to measure (cycles per degree)')
	stimulusSettings.add_argument('-fr', '--frequencyResolution', type=int, default=20, help='The number of frequency steps')

	stimulusSettings.add_argument('--size', type=int, default=3, help='Gabor patch size in (degrees)')
	stimulusSettings.add_argument('--orientation', type=float, help='Orientation of gabor patch (degrees). If unspecified, each trial will be random')

	parameterSettings = parser.add_argument_group('Parameters')
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
	if None in [settings['sessionID'], settings['distance_mm']]:
		settings = ui.getSettings(parser, settings, ['sessionID', 'distance_mm'])

	return settings

def main():
	from . import log
	settings = getSettings()

	if not settings is None:
		# parameter validation: peak sensitivty space and peak frequency space should be subspaces of stimulus spaces (1/contrast, frequency)
		if not (settings['Parameters']['minPeakSensitivity'] >= 1/settings['Stimuli']['maxContrast'] and settings['Parameters']['maxPeakSensitivity'] <= 1/settings['Stimuli']['minContrast']):
			raise ValueError("Please increase the range of contrast space or decrease the range of peak sensitivity space.")
		if not (settings['Parameters']['minPeakFrequency'] >= settings['Stimuli']['minFrequency'] and settings['Parameters']['maxPeakFrequency'] <= settings['Stimuli']['maxFrequency']):
			raise ValueError("Please increase the range of frequency space or decrease the range of peak frequency space.")

		logPath = pathlib.Path(settings['outputFile']).parent
		log.startLog(settings['sessionID'], logPath)
		run(settings)

if __name__ == '__main__':
	main()