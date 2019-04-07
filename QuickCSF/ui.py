from qtpy import QtCore, QtGui, QtWidgets

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
				color: #ccc;
				font-size: 32pt;
			'''
		)

		self.instructionsText = INSTRUCTIONS
		
		self.breakText = 'Good job - it\'s now time for a break!\n\nWhen you are ready to continue, press the [ SPACEBAR ].'
		self.readyText = 'Ready?'
		self.responseText = '?'
		self.finishedText = 'All done!'

		self.setCentralWidget(self.displayWidget)

	def showInstructions(self):
		self.displayWidget.setText(self.instructionsText)

	def showReadyPrompt(self):
		self.displayWidget.setText(self.readyText)

	def showStimulus(self, stimulus):
		self.displayWidget.orientation = stimulus.orientation
		self.displayWidget.setText('-')

	def showMask(self):
		self.displayWidget.setText('+')

	def showBlank(self):
		self.displayWidget.setText('')

	def giveFeedback(self, good):
		if good:
			self.displayWidget.setText('Good!')
		else:
			self.displayWidget.setText('Wrong')

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
		print('UI received new state', stateName)

		if stateName == 'INSTRUCTIONS':
			self.showInstructions()
		elif stateName == 'BREAKING':
			self.showBreak()
		elif stateName == 'WAIT_FOR_READY':
			self.showReadyPrompt()
		elif 'INTERSTIMULUS_BLANK' in stateName:
			self.showBlank()
		elif stateName == 'SHOW_STIMULUS_1':
			if trial.stimulusOnFirst:
				self.showStimulus(trial.stimulus)
		elif stateName == 'SHOW_MASK_1':
			self.showMask()
		elif stateName == 'SHOW_STIMULUS_2':
			if not trial.stimulusOnFirst:
				self.showStimulus(trial.stimulus)
		elif stateName == 'SHOW_MASK_2':
			self.showMask()
		elif stateName == 'WAIT_FOR_RESPONSE':
			self.showResponsePrompt()
		elif stateName == 'FEEDBACK':
			self.giveFeedback(trial.correct)
		elif stateName == 'FINISHED':
			self.showFinished()
