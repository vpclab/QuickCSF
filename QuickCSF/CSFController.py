import random
import time, math

from qtpy import QtWidgets, QtCore

def chunkList(sequence, numberOfChunks):
	avg = len(sequence) / float(numberOfChunks)
	out = []
	last = 0.0

	while last < len(sequence):
		out.append(sequence[int(last):int(last + avg)])
		last += avg

	return out

class State:
	def __init__(self, nextStateName=None, name=None):
		self.name = name
		self.finished = False
		self.nextStateName = nextStateName
	
	def getNextStateName(self):
		return self.nextStateName

	def start(self):
		self.finished = False

	def isFinished(self):
		return self.finished

	def update(self):
		pass

class InputState(State):
	pass

class TimedState(State):
	def __init__(self, duration, nextStateName=None, name=None):
		super().__init__(nextStateName, name)
		self.startTime = None
		self.duration = duration

	def start(self):
		super().start()
		self.startTime = time.time()

	def update(self):
		if not self.finished:
			self.finished = (time.time() - self.startTime) > self.duration

class Trial_2AFC():
	def __init__(self, stimulusOnFirst):
		self.stimulusOnFirst = stimulusOnFirst
		self.stimulus = {}
		self.correct = None

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return f'Trial(stim={self.stimulus},stimOnFirst={self.stimulusOnFirst},correct={self.correct})'

class Controller_2AFC(QtCore.QObject):
	stateTransition = QtCore.Signal(object, object)

	def __init__(self,
		stimulusGenerator,
		trialsPerBlock=2,
		blockCount=4,
		fixationDuration=.25,
		stimulusDuration=.1,
		maskDuration=.1,
		interStimulusInterval=.1,
		feedbackDuration=.5,
		waitForReady=False,
		parent=None
	):
		super().__init__(parent)

		self.stimulusGenerator = stimulusGenerator

		self.blocks = self.buildTrialBlocks(
			trialsPerBlock,
			blockCount
		)
		self.stateSpace = self.buildStateSpace(fixationDuration, stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration, waitForReady)
		self.state = self.stateSpace['INSTRUCTIONS']

	def start(self):
		self.tick = QtCore.QTimer(self)
		self.tick.timeout.connect(self.update)
		self.tick.start()
		self.stateTransition.emit(self.state.name, self.getCurrentTrial())

	def buildTrialBlocks(self, trialsPerBlock, blockCount):
		trials = []

		totalTrialCount = trialsPerBlock * blockCount

		stimOnFirstPool = [True, False] * math.ceil(totalTrialCount/2)
		random.shuffle(stimOnFirstPool)
		stimOnFirstPool = stimOnFirstPool[:totalTrialCount]

		for b in range(blockCount):
			for i in range(trialsPerBlock):
				trials.append(Trial_2AFC(stimOnFirstPool.pop()))

		random.shuffle(trials)
		blocks = chunkList(trials, blockCount)

		random.shuffle(blocks)
		return blocks

	def buildStateSpace(self, fixationDuration, stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration, waitForReady):
		states = {
			'FINISHED': InputState(),
		}

		if waitForReady:
			preTrialState = InputState('FIXATION_CROSS', name='WAIT_FOR_READY')
		else:
			preTrialState = TimedState(fixationDuration+.5, 'FIXATION_CROSS', name='FIRST_TRIAL_FIXATION')

		states['INSTRUCTIONS'] = InputState(preTrialState.name)
		states['BREAKING'] = InputState(preTrialState.name)
		states[preTrialState.name] = preTrialState

		states['FIXATION_CROSS'] = TimedState(fixationDuration, 'INTERSTIMULUS_BLANK_0')
		states['INTERSTIMULUS_BLANK_0'] = TimedState(interStimulusInterval, 'SHOW_STIMULUS_1')
		states['SHOW_STIMULUS_1'] = TimedState(stimulusDuration, 'SHOW_MASK_1')
		states['SHOW_MASK_1'] = TimedState(maskDuration, 'INTERSTIMULUS_BLANK_1')
		states['INTERSTIMULUS_BLANK_1'] = TimedState(interStimulusInterval, 'SHOW_STIMULUS_2')
		states['SHOW_STIMULUS_2'] = TimedState(stimulusDuration, 'SHOW_MASK_2')
		states['SHOW_MASK_2'] = TimedState(maskDuration, 'INTERSTIMULUS_BLANK_2')
		states['INTERSTIMULUS_BLANK_2'] = TimedState(interStimulusInterval, 'WAIT_FOR_RESPONSE')
		states['WAIT_FOR_RESPONSE'] = InputState('FEEDBACK')
		states['FEEDBACK'] = TimedState(feedbackDuration)

		for name,state in states.items():
			state.name = name

		def getFeedbackNextState():
			if len(self.blocks[0]) == 0:
				if len(self.blocks) == 1:
					return 'FINISHED'
				else:
					return 'BREAKING'
			else:
				if waitForReady:
					return preTrialState.name
				else:
					return preTrialState.name

		states['FEEDBACK'].getNextStateName = getFeedbackNextState

		return states

	def getCurrentTrial(self):
		if len(self.blocks) > 0 and len(self.blocks[0]) > 0:
			return self.blocks[0][0]
		else:
			return None

	def onParticipantReady(self):
		if self.checkState(['INSTRUCTIONS', 'WAIT_FOR_READY', 'BREAKING', 'FINISHED']):
			self.state.finished = True

	def onParticipantResponse(self, selectedFirstOption):
		if self.checkState('WAIT_FOR_RESPONSE'):
			trial = self.getCurrentTrial()
			trial.correct = (selectedFirstOption == trial.stimulusOnFirst)
			self.stimulusGenerator.markResponse(trial.correct)
			self.state.finished = True

	def update(self):
		if self.state == None:
			return

		self.state.update()
		if self.state.isFinished():
			if self.checkState(['INSTRUCTIONS', 'BREAKING']):
				if len(self.blocks[0]) == 0:
					self.blocks.pop(0)

				trial = self.getCurrentTrial()
				if trial is not None:
					trial.stimulus = self.stimulusGenerator.next()

			elif self.checkState('FEEDBACK'):
				self.blocks[0].pop(0)
				trial = self.getCurrentTrial()
				if trial is not None:
					trial.stimulus = self.stimulusGenerator.next()
				

			nextStateName = self.state.getNextStateName()
			if nextStateName is None:
				self.tick.stop()
				QtWidgets.QApplication.quit()
			else:
				self.state = self.stateSpace[nextStateName]
				self.state.start()
				self.stateTransition.emit(self.state.name, self.getCurrentTrial())

	def isFinished(self):
		return self.checkState('FINISHED')

	def checkState(self, okStates):
		if not type(okStates) is list:
			okStates = [okStates]

		return self.state.name in okStates