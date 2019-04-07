import math, time

import numpy

from qtpy import QtCore, QtGui, QtWidgets, QtMultimedia

INSTRUCTIONS = '''For this test, you will be presented with two options - one will be blank, and the other will be a striped circle.\n\n
A tone will play when each option is displayed. After both tones, you will need to select which option contained the striped circle.\n\n
If the striped circle appeared during the FIRST tone, press [ ← LEFT ].\n
If the striped circle appeared during the SECOND tone, press [ RIGHT → ].\n\n
Throughout the test, keep your gaze fixated on the circled-dot at the center of the screen.\n\n
If you are uncertain, make a guess.\n\n\nPress [ SPACEBAR ] to start.'''

class QuickCSFWindow(QtWidgets.QMainWindow):
	participantReady = QtCore.Signal()
	participantResponse = QtCore.Signal(object)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.displayWidget = QtWidgets.QLabel(self)
		self.displayWidget.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
		self.displayWidget.setWordWrap(True)
		self.displayWidget.setMargin(100)
		self.displayWidget.setStyleSheet(
			'''
				background: rgb(127, 127, 127);
				color: #bbb;
				font-size: 32pt;
			'''
		)

		self.instructionsText = INSTRUCTIONS
		
		self.breakText = 'Good job - it\'s now time for a break!\n\nWhen you are ready to continue, press the [ SPACEBAR ].'
		self.readyText = 'Ready?'
		self.responseText = '?'
		self.finishedText = 'All done!'

		self.setCentralWidget(self.displayWidget)
		self.sounds = {
			'tone': QtMultimedia.QSound('assets/tone.wav'),
			'good': QtMultimedia.QSound('assets/good.wav'),
			'bad': QtMultimedia.QSound('assets/bad.wav'),
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

	def showFinished(self):
		self.displayWidget.setText(self.finishedText)

	def keyReleaseEvent(self, event):
		if event.key() == QtCore.Qt.Key_Space:
			self.participantReady.emit()
		elif event.key() == QtCore.Qt.Key_4:
			self.participantResponse.emit(True)
		elif event.key() == QtCore.Qt.Key_6:
			self.participantResponse.emit(False)

	def onNewState(self, stateName, trial):
		print(time.time(), 'UI received new state', stateName)

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
			if trial.stimulusOnFirst:
				self.showStimulus(trial.stimulus)
			else:
				self.showNonStimulus()
		elif stateName == 'SHOW_MASK_1':
			self.showMask()
		elif stateName == 'SHOW_STIMULUS_2':
			if not trial.stimulusOnFirst:
				self.showStimulus(trial.stimulus)
			else:
				self.showNonStimulus()
		elif stateName == 'SHOW_MASK_2':
			self.showMask()
		elif stateName == 'WAIT_FOR_RESPONSE':
			self.showResponsePrompt()
		elif stateName == 'FEEDBACK':
			self.giveFeedback(trial.correct)
		elif stateName == 'FINISHED':
			self.showFinished()


if __name__ == '__main__':
	import sys
	app = QtWidgets.QApplication()
	app.setApplicationName('QuickCSF')

	img = ContrastGaborPatchImage(contrast=1.0, size=100, frequency=.1, orientation=0)
	window = QtWidgets.QLabel()
	window.setStyleSheet('background-color: rgb(127, 127, 127)')
	window.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
	window.setText('hi')
	window.setPixmap(QtGui.QPixmap.fromImage(img))
	window.show()
	sys.exit(app.exec_())
