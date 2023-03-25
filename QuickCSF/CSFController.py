# -*- coding: utf-8 -*
'''A 2AFC controller for the simple QuickCSF.app'''

import logging
import random
import time, math

from qtpy import QtWidgets, QtCore

logger = logging.getLogger(__name__)

class State:
	'''Base class for state objects that describe the state of the controller and transition map'''

	def __init__(self, nextStateName=None, name=None):
		'''Create a new state
			Args:
				nextStateName (str): the state we should transition to when finished
				name (str): the name of this state
		'''
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
	'''States that require a user response'''
	pass

class TimedState(State):
	'''States that automatically finish after a fixed duration'''

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
	'''Represents a single trial'''

	def __init__(self, stimulusOnFirst):
		self.stimulusOnFirst = stimulusOnFirst
		self.stimulus = {}
		self.correct = None
		self.id = ''

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return f'{self.__class__.__name__}(' + str(vars(self)) + ')'

class Controller_2AFC(QtCore.QObject):
	'''A 2AFC experiment controller

		Follows a basic pattern:
			Execute `blockCount` blocks:
				Execute `trialsPerBlock` trials:
					Determine the visual stimulus to be displayed
					(optional) Wait for participant to indicate they are ready
					Play two audible tones, displaying a visual stimulus during one of them
					Wait for participant response indicating if the the visual stimulus was present for the first or second audible tone
					Record the response
				Take a break between blocks
	'''

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

		self.blocks = self._buildTrialBlocks(
			trialsPerBlock,
			blockCount
		)
		self.stateSpace = self._buildStateSpace(fixationDuration, stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration, waitForReady)
		self.state = self.stateSpace['INSTRUCTIONS']

	def _buildTrialBlocks(self, trialsPerBlock, blockCount):
		'''Build blocks of trials

			Creates the specified number of trials, shuffles them, then chunks them into blocks and shuffles the blocks
		'''

		trials = []

		totalTrialCount = trialsPerBlock * blockCount

		stimOnFirstPool = [True, False] * math.ceil(totalTrialCount/2)
		random.shuffle(stimOnFirstPool)
		stimOnFirstPool = stimOnFirstPool[:totalTrialCount]

		logger.debug(f'Building {blockCount} blocks of {trialsPerBlock} trials each')
		for b in range(blockCount):
			for i in range(trialsPerBlock):
				trials.append(Trial_2AFC(stimOnFirstPool.pop()))

		random.shuffle(trials)

		blocks = []
		for b in range(blockCount):
			blocks.append([])
			for t in range(trialsPerBlock):
				blocks[-1].append(trials.pop())

		random.shuffle(blocks)

		for blockIdx, block in enumerate(blocks):
			for trialIdx, trial in enumerate(block):
				trial.id = f'{(blockIdx+1):02d}-{(trialIdx+1):02d}'

		return blocks

	def _buildStateSpace(self, fixationDuration, stimulusDuration, maskDuration, interStimulusInterval, feedbackDuration, waitForReady):
		'''Build states and define their transition edges'''

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

	def start(self):
		'''Insert `update` function call into the Qt event loop and initiate the starting state'''

		self.tick = QtCore.QTimer(self)
		self.tick.timeout.connect(self._update)
		self.tick.start()
		self.stateTransition.emit(self.state.name, self.getCurrentTrial())

	def getCurrentTrial(self):
		if len(self.blocks) > 0 and len(self.blocks[0]) > 0:
			return self.blocks[0][0]
		else:
			return None

	def checkState(self, okStates):
		if not type(okStates) is list:
			okStates = [okStates]

		return self.state.name in okStates

	def isFinished(self):
		return self.checkState('FINISHED')

	def onParticipantReady(self):
		if self.checkState(['INSTRUCTIONS', 'WAIT_FOR_READY', 'BREAKING', 'FINISHED']):
			self.state.finished = True

	def onParticipantResponse(self, selectedFirstOption):
		if self.checkState('WAIT_FOR_RESPONSE'):
			trial = self.getCurrentTrial()
			trial.correct = (selectedFirstOption == trial.stimulusOnFirst)
			self.stimulusGenerator.markResponse(trial.correct)
			self.state.finished = True

	def _update(self):
		'''Update the current state, transition to the next state if finished

			Note:
				This is called automatically by Qt's event loop after `start()` has been called
		'''

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
				self.state = None
				self.tick.stop()
				QtWidgets.QApplication.quit()
			else:
				self.state = self.stateSpace[nextStateName]
				self.state.start()

				if self.state.name == 'FINISHED':
					self.stateTransition.emit(self.state.name, self.stimulusGenerator.getResults())
				else:
					self.stateTransition.emit(self.state.name, self.getCurrentTrial())
