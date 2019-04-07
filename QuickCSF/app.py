import sys

from qtpy import QtWidgets, QtCore

from . import ui
from . import CSFController
from . import QuickCSF
from . import StimulusGenerators

def run():
	app = QtWidgets.QApplication()
	app.setApplicationName('QuickCSF')

	window = ui.QuickCSFWindow()

	stimGenerator = StimulusGenerators.RandomOrientationGenerator(256)
	controller = CSFController.Controller_2AFC(stimGenerator)

	window.participantReady.connect(controller.onParticipantReady)
	window.participantResponse.connect(controller.onParticipantResponse)

	controller.stateTransition.connect(window.onNewState)

	controller.start()
	window.showFullScreen()
	sys.exit(app.exec_())

if __name__ == '__main__':
	run()