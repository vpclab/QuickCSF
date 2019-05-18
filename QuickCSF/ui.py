# -*- coding: utf-8 -*
'''User interaction (display and input)'''

import sys, traceback
import logging
import math, time

import numpy

from qtpy import QtCore, QtGui, QtWidgets, QtMultimedia
import argparseqt.gui

from . import assets

logger = logging.getLogger(__name__)

DEFAULT_INSTRUCTIONS = '''For this test, you will be presented with two options - one will be blank, and the other will be a striped circle.\n\n
A tone will play when each option is displayed. After both tones, you will need to select which option contained the striped circle.\n\n
If the striped circle appeared during the FIRST tone, press [ ← LEFT ].\n
If the striped circle appeared during the SECOND tone, press [ RIGHT → ].\n\n
Throughout the test, keep your gaze fixated on the circled-dot at the center of the screen.\n\n
If you are uncertain, make a guess.\n\n\nPress [ SPACEBAR ] to start.'''

class QuickCSFWindow(QtWidgets.QMainWindow):
	'''The main window for QuickCSF.app'''

	participantReady = QtCore.Signal()
	participantResponse = QtCore.Signal(object)

	def __init__(self, instructions=None, parent=None):
		super().__init__(parent)
		self.displayWidget = QtWidgets.QLabel(self)
		self.displayWidget.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
		self.displayWidget.setWordWrap(True)
		self.displayWidget.setMargin(100)
		self.displayWidget.setStyleSheet(
			'''
				background: rgb(127, 127, 127);
				color: #bbb;
				font-size: 28pt;
			'''
		)

		self.instructionsText = instructions if instructions is not None else DEFAULT_INSTRUCTIONS
		
		self.breakText = 'Good job - it\'s now time for a break!\n\nWhen you are ready to continue, press the [ SPACEBAR ].'
		self.readyText = 'Ready?'
		self.responseText = '?'
		self.finishedText = 'All done!'

		self.setCentralWidget(self.displayWidget)
		self.sounds = {
			'tone': QtMultimedia.QSound(assets.locate('tone.wav')),
			'good': QtMultimedia.QSound(assets.locate('good.wav')),
			'bad': QtMultimedia.QSound(assets.locate('bad.wav')),
		}

	def showInstructions(self):
		self.displayWidget.setText(self.instructionsText)

	def showReadyPrompt(self):
		self.displayWidget.setText(self.readyText)

	def showFixationCross(self):
		self.displayWidget.setText('+')

	def showStimulus(self, stimulus):
		self.displayWidget.setPixmap(QtGui.QPixmap.fromImage(stimulus))
		self.sounds['tone'].play()

	def showNonStimulus(self):
		self.showBlank()
		self.sounds['tone'].play()

	def showMask(self):
		self.displayWidget.setText('')

	def showBlank(self):
		self.displayWidget.setText('')
		self.displayWidget.setPixmap(None)

	def giveFeedback(self, good):
		if good:
			self.displayWidget.setText('Good!')
			self.sounds['good'].play()
		else:
			self.displayWidget.setText('Wrong')
			self.sounds['bad'].play()

	def showResponsePrompt(self):
		self.displayWidget.setText(self.responseText)

	def showBreak(self):
		self.displayWidget.setText(self.breakText)

	def showFinished(self, results):
		outputDisplay = self.finishedText + '\n'
		for key,value in results.items():
			outputDisplay += f'\n{key} = {value:.4f}'
				
		self.displayWidget.setText(outputDisplay)

	def keyReleaseEvent(self, event):
		logger.debug(f'Key released {event.key()}')
		if event.key() == QtCore.Qt.Key_Space:
			self.participantReady.emit()
		elif event.key() in (QtCore.Qt.Key_4, QtCore.Qt.Key_Left):
			self.participantResponse.emit(True)
		elif event.key() in (QtCore.Qt.Key_6, QtCore.Qt.Key_Right):
			self.participantResponse.emit(False)

	def onNewState(self, stateName, data):
		logger.debug(f'New state: {stateName} [{data}]')

		if stateName == 'INSTRUCTIONS':
			self.showInstructions()
		elif stateName == 'BREAKING':
			self.showBreak()
		elif stateName == 'WAIT_FOR_READY':
			self.showReadyPrompt()
		elif 'FIXATION' in stateName:
			self.showFixationCross()
		elif '_BLANK' in stateName:
			self.showBlank()
		elif stateName == 'SHOW_STIMULUS_1':
			if data.stimulusOnFirst:
				self.showStimulus(data.stimulus)
			else:
				self.showNonStimulus()
		elif stateName == 'SHOW_MASK_1':
			self.showMask()
		elif stateName == 'SHOW_STIMULUS_2':
			if not data.stimulusOnFirst:
				self.showStimulus(data.stimulus)
			else:
				self.showNonStimulus()
		elif stateName == 'SHOW_MASK_2':
			self.showMask()
		elif stateName == 'WAIT_FOR_RESPONSE':
			self.showResponsePrompt()
		elif stateName == 'FEEDBACK':
			self.giveFeedback(data.correct)
		elif stateName == 'FINISHED':
			self.showFinished(data)

def getSettings(parser, settings, requiredFields=[]):
	'''Display a GUI to collect experiment settings'''
	dialog = argparseqt.gui.ArgDialog(parser)
	dialog.setValues(settings)
	dialog.exec_()
	if dialog.result() == QtWidgets.QDialog.Accepted:
		settings = dialog.getValues()
		
		for field in requiredFields:
			if settings[field] == None:
				QtWidgets.QMessageBox.critical(
					None,
					'Missing information',
					'You must specify the following fields: ' + ','.join(requiredFields)
				)
				return None
	else:
		return None

	return settings

def exception_handler(excType, exc, tb, extraDetails=None, parentWindow=None):
	if issubclass(excType, KeyboardInterrupt):
		sys.__excepthook__(excType, exc, tb)
		return

	stack = traceback.format_tb(tb)

	details = '%s: %s\n%s' % (excType.__name__, exc, ''.join(stack))
	print('UNHANDLED EXCEPTION! ' + details, file=sys.stderr)

	dialog = QtWidgets.QMessageBox(parentWindow)
	dialog.setWindowTitle('QuickCSF - Application Error')
	dialog.setText('Something went wrong and we were not prepared for it :(\n\nThe application will now exit, but some details may be available below.')

	if extraDetails is not None:
		details = extraDetails + '\n\n' + details

	dialog.setDetailedText(details)
	dialog.setModal(True)
	dialog.exec_()
	QtWidgets.QApplication.exit()

def popupUncaughtExceptions(extraDetails=None, parent=None):
	sys.excepthook = lambda excType, exc, tb: exception_handler(excType, exc, tb, extraDetails, parent)
