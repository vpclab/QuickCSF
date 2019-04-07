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
	def __init__(self, nextState=None, name=None):
		self.name = name
		self.finished = False
		self.nextState = nextState
	
	def getNextState(self):
		return self.nextState

	def start(self):
		self.finished = False

	def isFinished(self):
		return self.finished

	def update(self):
		pass

class InputState(State):
	pass

class TimedState(State):
	def __init__(self, duration, nextState=None):
		super().__init__(nextState)
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
		trialsPerBlock=25,
		blockCount=4,
		stimulusDuration=.1,
		maskDuration=.1,
		interStimulusInterval=.1,
		feedbackDuration=1.0,
		parent=None
	):
		super().__init__(parent)

		self.stimulusGenerator = stimulusGenerator

		self.blocks = self.buildTrialBlocks(
			trialsPerBlock,
			blockCount
		)
		self.stateSpace = self.buildStateSpace(stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration)
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

	def buildStateSpace(self, stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration):
		states = {
			'FINISHED': InputState(),
		}

		states['FEEDBACK'] = TimedState(feedbackDuration)
		states['WAIT_FOR_RESPONSE'] = InputState(states['FEEDBACK'])
		states['INTERSTIMULUS_BLANK_2'] = TimedState(interStimulusInterval, states['WAIT_FOR_RESPONSE'])
		states['SHOW_MASK_2'] = TimedState(maskDuration, states['INTERSTIMULUS_BLANK_2'])
		states['SHOW_STIMULUS_2'] = TimedState(stimulusDuration, states['SHOW_MASK_2'])
		states['INTERSTIMULUS_BLANK_1'] = TimedState(interStimulusInterval, states['SHOW_STIMULUS_2'])
		states['SHOW_MASK_1'] = TimedState(maskDuration, states['INTERSTIMULUS_BLANK_1'])
		states['SHOW_STIMULUS_1'] = TimedState(stimulusDuration, states['SHOW_MASK_1'])
		states['INTERSTIMULUS_BLANK_0'] = TimedState(interStimulusInterval, states['SHOW_STIMULUS_1'])
		states['WAIT_FOR_READY'] = InputState(states['INTERSTIMULUS_BLANK_0'])
		states['BREAKING'] = InputState(states['WAIT_FOR_READY'])
		states['INSTRUCTIONS'] = InputState(states['WAIT_FOR_READY'])

		for k,v in states.items():
			v.name = k

		def getFeedbackNextState():
			if len(self.blocks[0]) == 0:
				if len(self.blocks) == 1:
					return states['FINISHED']
				else:
					return states['BREAKING']
			else:
				return states['WAIT_FOR_READY']

		states['FEEDBACK'].getNextState = getFeedbackNextState

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
			if self.checkState('FEEDBACK'):
				self.blocks[0].pop(0)
			elif self.checkState('BREAKING'):
				self.blocks.pop(0)
			elif self.checkState('WAIT_FOR_READY'):
				trial = self.getCurrentTrial()
				trial.stimulus = self.stimulusGenerator.next()

			self.state = self.state.getNextState()
			if self.state == None:
				self.tick.stop()
				QtWidgets.QApplication.quit()
			else:
				self.state.start()
				self.stateTransition.emit(self.state.name, self.getCurrentTrial())

	def isFinished(self):
		return self.checkState('FINISHED')

	def checkState(self, okStates):
		if not type(okStates) is list:
			okStates = [okStates]

		return self.state.name in okStates