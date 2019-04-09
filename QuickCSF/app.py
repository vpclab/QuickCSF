import logging

import sys, pathlib, csv
from datetime import datetime

from qtpy import QtWidgets, QtCore

from . import ui
from . import CSFController
from . import QuickCSF
from . import StimulusGenerators

logger = logging.getLogger('QuickCSF.app')

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


def _start():
	global experimentInfo, mainWindow

	logger.debug('Getting experiment info')
	experimentInfo = ui.getExperimentInfo()
	logger.info('Experiment info: ' + str(experimentInfo))
	if experimentInfo is not None:
		logger.debug('Showing main window')
		mainWindow = ui.QuickCSFWindow()

		stimGenerator = StimulusGenerators.RandomOrientationGenerator(256)
		controller = CSFController.Controller_2AFC(stimGenerator)

		mainWindow.participantReady.connect(controller.onParticipantReady)
		mainWindow.participantResponse.connect(controller.onParticipantResponse)

		controller.stateTransition.connect(mainWindow.onNewState)
		controller.stateTransition.connect(onStateTransition)

		QtCore.QTimer.singleShot(0, controller.start)
		mainWindow.showFullScreen()

def run():
	global pid

	logger.info('Starting app')
	app = QtWidgets.QApplication()
	app.setApplicationName('QuickCSF')

	QtCore.QTimer.singleShot(0, _start)

	app.exec_()
	logger.info('App exited')

if __name__ == '__main__':
	from . import log
	log.startLog()

	run()