import logging

import argparse
import sys, pathlib, csv
import functools
from datetime import datetime

from qtpy import QtWidgets, QtCore

from . import ui
from . import CSFController
from . import QuickCSF
from . import StimulusGenerators
from . import screens

logger = logging.getLogger('QuickCSF.app')

app = QtWidgets.QApplication()
app.setApplicationName('QuickCSF')


def onStateTransition(state, data):
	if state == 'FINISHED':
		data = data[0]

		outputFile = pathlib.Path('data/output.csv')

		fields = list(experimentInfo.keys())
		fields += ['Peak sensitivity', 'Peak frequency', 'Bandwidth', 'Truncation', 'Timestamp']

		fileExists = outputFile.exists()
		with outputFile.open('a') as csvFile:
			writer = csv.DictWriter(csvFile, fieldnames=fields)
			if not fileExists:
				writer.writeheader()

			record = {
				'Timestamp': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
				'Peak sensitivity': data[0],
				'Peak frequency': data[1],
				'Bandwidth': data[2],
				'Truncation': data[3],
			}
			record = {**record, **experimentInfo}
			writer.writerow(record)

def _start(settings):
	global experimentInfo, mainWindow

	logger.debug('Showing main window')

	if settings['instructionsFile'] is not None:
		with open(settings['instructionsFile']) as instructionsFile:
			instructions = instructionsFile.read()
	else:
		instructions = None

	mainWindow = ui.QuickCSFWindow(instructions)

	degreesToPixels = None
	if settings['distance_mm'] is not None:
		degreesToPixels = functools.partial(screens.degreesToPixels, distance_mm=settings['distance_mm'])

	stimGenerator = StimulusGenerators.RandomOrientationGenerator(degreesToPixels=degreesToPixels, **settings['stim'])
	controller = CSFController.Controller_2AFC(stimGenerator, **settings['controller'])

	mainWindow.participantReady.connect(controller.onParticipantReady)
	mainWindow.participantResponse.connect(controller.onParticipantResponse)

	controller.stateTransition.connect(mainWindow.onNewState)
	controller.stateTransition.connect(onStateTransition)

	QtCore.QTimer.singleShot(0, controller.start)
	mainWindow.showFullScreen()

def run(settings=None):
	global pid

	QtCore.QTimer.singleShot(0, lambda: _start(settings))
	app.exec_()
	logger.info('App exited')

def getSettings():
	parser = argparse.ArgumentParser()
	parser.add_argument('-sid', '--sessionID', default=None, help='A unique string to identify this observer/session')
	parser.add_argument('-d', '--distance_mm', type=float, default=None, help='Distance (mm) from the display to the observer')
	parser.add_argument('--instructionsFile', default=None, help='A plaintext file containing the instructions')

	parser.add_argument('--controller.trialsPerBlock', type=int, default=25, help='Number of trials in each block')
	parser.add_argument('--controller.blockCount', type=int, default=4, help='Number of blocks')

	parser.add_argument('--controller.fixationDuration', type=float, default=.25, help='How long (seconds) the fixation stimulus is displayed')
	parser.add_argument('--controller.stimulusDuration', type=float, default=.1, help='How long (seconds) the stimulus is displayed')
	parser.add_argument('--controller.maskDuration', type=float, default=.1, help='How long (seconds) the stimulus mask is displayed')
	parser.add_argument('--controller.interStimulusInterval', type=float, default=.1, help='How long (seconds) a blank is displayed between stimuli')
	parser.add_argument('--controller.feedbackDuration', type=float, default=.5, help='How long (seconds) feedback is displayed')

	parser.add_argument('--controller.waitForReady', default=False, action='store_true', help='Wait for the participant to indicate they are ready for the next trial')

	parser.add_argument('-minc', '--stim.minContrast', type=float, default=.01, help='The lowest contrast value to measure (0.0-1.0)')
	parser.add_argument('-maxc', '--stim.maxContrast', type=float, default=1.0, help='The highest contrast value to measure (0.0-1.0)')
	parser.add_argument('-cr', '--stim.contrastResolution', type=int, default=24, help='The number of contrast steps')

	parser.add_argument('-minf', '--stim.minFrequency', type=float, default=0.2, help='The lowest frequency value to measure (cycles per degree)')
	parser.add_argument('-maxf', '--stim.maxFrequency', type=float, default=36.0, help='The highest frequency value to measure (cycles per degree)')
	parser.add_argument('-fr', '--stim.frequencyResolution', type=int, default=20, help='The number of frequency steps')

	parser.add_argument('--stim.size', type=int, default=3, help='Gabor patch size in (degrees)')

	settings = vars(parser.parse_args())
	if settings['sessionID'] is None:
		experimentInfo = ui.getExperimentInfo()
		if experimentInfo is None:
			return None

		settings = {**settings, **experimentInfo}

	groupedSettings = {}
	for k,v in settings.items():
		if '.' in k:
			parts = k.split('.', 1)
			if parts[0] not in groupedSettings:
				groupedSettings[parts[0]] = {}

			groupedSettings[parts[0]][parts[1]] = v
		else:
			groupedSettings[k] = v

	return groupedSettings

if __name__ == '__main__':
	from . import log
	settings = getSettings()

	if not settings is None:
		log.startLog(settings['sessionID'])
		run(settings)
