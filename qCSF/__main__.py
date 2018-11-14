import sys, os, platform
import math
import traceback
import argparse
import time, random
import logging

from functools import partial
from collections import OrderedDict

import psychopy

psychopy.prefs.general['audioLib'] = ['pyo','pygame', 'sounddevice']

from psychopy import core, visual, gui, data, event, monitors, sound, tools
import numpy

import qcsf, settings, assets

import monitorTools

class Trial():
	def __init__(self, eccentricity, orientation, stimPositionAngle):
		self.eccentricity = eccentricity
		self.orientation = orientation
		self.stimPositionAngle = stimPositionAngle

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return f'Trial(e={self.eccentricity},o={self.orientation},a={self.stimPositionAngle})'

class UserExit(Exception):
	def __init__(self):
		super().__init__('User asked to quit.')

def getSound(filename, freq, duration):
	try:
		filename = os.path.join('assets', 'qCSF', filename)
		filename = assets.getFilePath(filename)
		return sound.Sound(filename)
	except ValueError:
		logging.warning(f'Failed to load sound file: {filename}. Synthesizing sound instead.')
		return sound.Sound(freq, secs=duration)

def getConfig():
	config = settings.getSettings('qCSF Settings.ini')
	config['General settings']['start_time'] = data.getDateStr()
	logFile = config['General settings']['data_filename'].format(**config['General settings']) + '.log'
	logging.basicConfig(filename=logFile, level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

	config['sitmulusTone'] = getSound('600Hz_square_25.wav', 600, .185)
	config['positiveFeedback'] = getSound('1000Hz_sine_50.wav', 1000, .077)
	config['negativeFeedback'] = getSound('300Hz_sine_25.wav', 300, .2)
	config['gazeTone'] = getSound('hurt.wav', 200, .2)

	return config

class PeripheralCSFTester():
	def __init__(self, config):
		self.config = config

		sound.init()

		self.setupMonitor()
		self.setupHUD()
		self.setupDataFile()

		self.setupBlocks()

	def setupMonitor(self):
		physicalSize = monitorTools.getPhysicalSize()
		resolution = monitorTools.getResolution()

		self.mon = monitors.Monitor('testMonitor')
		self.mon.setDistance(self.config['Display settings']['monitor_distance'])  # Measure first to ensure this is correct
		self.mon.setWidth(physicalSize[0]/10)
		self.mon.setSizePix(resolution)
		self.mon.save()

		self.win = visual.Window(fullscr=True, monitor='testMonitor', allowGUI=False, units='deg', size=resolution, color=self.config['Display settings']['background_color'])

		self.stim = visual.GratingStim(self.win, contrast=1, sf=6, size=self.config['Stimuli settings']['stimulus_size'], mask='gauss')
		fixationVertices = (
			(0, -0.5), (0, 0.5),
			(0, 0),
			(-0.5, 0), (0.5, 0),
		)
		self.fixationStim = visual.ShapeStim(self.win, vertices=fixationVertices, lineColor=-1, closeShape=False, size=self.config['Display settings']['fixation_size']/60.0)
		self.fixationAid = [
			visual.Circle(self.win,
				radius = self.config['Gaze tracking']['gaze_offset_max'] * .5,
				lineColor = 'black',
				fillColor = None,
			), visual.Circle(self.win,
				radius = self.config['Gaze tracking']['gaze_offset_max'] * .1,
				lineColor = None,
				fillColor = 'black',
			)
		]

		if self.config['Display settings']['show_annuli']:
			self.annuli = {}
			for eccentricity in self.config['Stimuli settings']['eccentricities']:
				self.annuli[eccentricity] = []

				for angle in self.config['Stimuli settings']['stimulus_position_angles']:
					pos = [
						numpy.cos(angle * numpy.pi/180.0) * eccentricity,
						numpy.sin(angle * numpy.pi/180.0) * eccentricity,
					]
					self.annuli[eccentricity].append(
						visual.Circle(
							self.win,
							pos=pos,
							radius = .7 * self.config['Stimuli settings']['stimulus_size'],
							lineColor = self.config['Display settings']['annuli_color'],
							fillColor = None,
							units = 'deg'
						)
					)

		if self.config['Stimuli settings']['mask_time'] > 0:
			self.masks = {}
			size = self.config['Stimuli settings']['stimulus_size']
			for eccentricity in self.config['Stimuli settings']['eccentricities']:
				self.masks[eccentricity] = []
				for angle in self.config['Stimuli settings']['stimulus_position_angles']:
					pos = [
						numpy.cos(angle * numpy.pi/180.0) * eccentricity,
						numpy.sin(angle * numpy.pi/180.0) * eccentricity,
					]
					self.masks[eccentricity].append(
						visual.NoiseStim(
							self.win,
							pos=pos,
							size=[size,size],
							mask='circle',
							units = 'deg',
							noiseType='White',
							noiseElementSize=4,
						)
					)

		if self.config['Gaze tracking']['wait_for_fixation'] or self.config['Gaze tracking']['render_at_gaze']:
			self.screenMarkers = PyPupilGazeTracker.PsychoPyVisuals.ScreenMarkers(self.win)
			self.gazeTracker = PyPupilGazeTracker.GazeTracker.GazeTracker(
				smoother=PyPupilGazeTracker.smoothing.SimpleDecay(),
				screenSize=resolution
			)
			self.gazeTracker.start()
			self.gazeMarker = PyPupilGazeTracker.PsychoPyVisuals.FixationStim(self.win, size=self.config['Gaze tracking']['gaze_offset_max'], units='deg', autoDraw=False)
		else:
			self.gazeTracker = None

	def setTopLeftPos(self, stim, pos):
		# convert pixels to degrees
		stimDim = stim.boundingBox
		screenDim = self.mon.getSizePix()
		centerPos = [
			pos[0] + (stimDim[0] - screenDim[0]) / 2,
			(screenDim[1] - stimDim[1]) / 2 - pos[1],
		]
		stim.pos = centerPos

	def updateHUD(self, item, text, color=None):
		element, pos, labelText = self.hudElements[item]
		element.text = text
		self.setTopLeftPos(element, pos)
		if color != None:
			element.color = color

	def setupHUD(self):
		lineHeight = 40
		xOffset = 325
		yOffset = 10

		self.hudElements = OrderedDict(
			lastStim = [visual.TextStim(self.win, text=' '), [xOffset, 0 + yOffset], 'Last stim'],
			lastResp = [visual.TextStim(self.win, text=' '), [xOffset + 40, lineHeight + yOffset], None],
			lastOk = [visual.TextStim(self.win, text=' '), [xOffset -10, lineHeight + yOffset], 'Last resp'],
			thisStim = [visual.TextStim(self.win, text=' '), [xOffset, 2*lineHeight + yOffset], 'This stim'],
			expectedResp = [visual.TextStim(self.win, text=' '), [xOffset, 3*lineHeight + yOffset], 'Exp resp'],
		)

		for key in list(self.hudElements):
			stim, pos, labelText = self.hudElements[key]
			if labelText is not None:
				label = visual.TextStim(self.win, text=labelText+':')
				pos = [130, pos[1]]
				self.hudElements[key+'_label'] = [label, pos, None]

		for key in list(self.hudElements):
			stim, pos, labelText = self.hudElements[key]

			stim.color = 1
			stim.units = 'pix'
			stim.height = lineHeight * .88
			stim.wrapWidth = 9999
			self.setTopLeftPos(stim, pos)

	def enableHUD(self):
		for key, hudArgs in self.hudElements.items():
			stim, pos, labelText = hudArgs
			stim.autoDraw = True

	def disableHUD(self):
		for key, hudArgs in self.hudElements.items():
			stim, pos, labelText = hudArgs
			stim.autoDraw = False

	def setupDataFile(self):
		self.dataFilename = self.config['General settings']['data_filename'].format(**self.config['General settings']) + '.csv'
		logging.info(f'Starting data file {self.dataFilename}')

		if not os.path.exists(self.dataFilename):
			dataFile = open(self.dataFilename, 'w')
			dataFile.write('Eccentricity,Orientation,PeakSensitivity,PeakFrequency,Bandwidth,Delta\n')
			dataFile.close()

	def writeOutput(self, eccentricity, orientation, parameterEstimates):
		logging.debug(f'Saving record to {self.dataFilename}, e={eccentricity}, o={orientation}, p={parameterEstimates.T}')

		dataFile = open(self.dataFilename, 'a')  # a simple text file with 'comma-separated-values'
		dataFile.write(f'{eccentricity},{orientation},{parameterEstimates[0]},{parameterEstimates[1]},{parameterEstimates[2]},{parameterEstimates[3]}\n')
		dataFile.close()

	def setupStepHandler(self):
		# Maximums lowered for older adults
		stimulusSpace = numpy.array([
			numpy.arange(0, 31),	# Contrast
			numpy.arange(0, 20),	# Frequency
		])
		parameterSpace = numpy.array([
			numpy.arange(0, 28),	# Peak sensitivity
			numpy.arange(0, 21),	# Peak frequency
			numpy.arange(0, 21),	# Log bandwidth
			numpy.arange(0, 21)		# Low frequency truncation (log delta)
		])

		logging.info('Stimulus space (contrast): numpy.arange(0, 31))')
		logging.info('Stimulus space (frequency): numpy.arange(0, 20))')

		logging.info('Parameter space (peak sensitivity): numpy.arange(0, 28))')
		logging.info('Parameter space (peak frequency): numpy.arange(0, 21))')
		logging.info('Parameter space (log bandwidth): numpy.arange(0, 21))')
		logging.info('Parameter space (log delta): numpy.arange(0, 21))')

		return qcsf.QCSF(stimulusSpace, parameterSpace)

	def showMessage(self, msg):
		instructionsStim = visual.TextStim(self.win, text=msg, color=-1, wrapWidth=40)
		instructionsStim.draw()

		self.win.flip()

		keys = event.waitKeys()
		if 'escape' in keys:
			raise UserExit()

	def showInstructions(self, firstTime=False):
		key1 = self.config['Input settings']['first_stimulus_key_label']
		key2 = self.config['Input settings']['second_stimulus_key_label']

		instructions = 'In this experiment, you will be presented with two options - one will be blank, and the other will be a stimulus.\n\n'
		instructions += 'A tone will play when each option is displayed. After both tones, you will need to select which option contained the stimulus.\n\n'
		instructions += 'If the stimulus appeared during the FIRST tone, press [' + key1.upper() + '].\n'
		instructions += 'If the stimulus appeared during the SECOND tone, press [' + key2.upper() + '].\n\n'
		instructions += 'During the process, keep your gaze fixated on the small cross at the center of the screen.\n\n'
		instructions += 'If you are uncertain, make a guess.\n\n\nPress any key to start.'

		if not firstTime:
			instructions = 'These instructions are the same as before.\n\n' + instructions

		self.showMessage(instructions)

	def takeABreak(self, waitForKey=True):
		self.showMessage('Good job - it\'s now time for a break!\n\nWhen you are ready to continue, press the [SPACEBAR].')

	def checkResponse(self, whichStim):
		key1 = self.config['Input settings']['first_stimulus_key']
		key2 = self.config['Input settings']['second_stimulus_key']

		label1 = self.config['Input settings']['first_stimulus_key_label']
		label2 = self.config['Input settings']['second_stimulus_key_label']

		correct = None
		while correct is None:
			keys = event.waitKeys()
			logging.debug(f'Keys detected: {keys}')
			if key1 in keys:
				logging.info(f'User selected key1 ({key1})')
				self.updateHUD('lastResp', label1)
				correct = (whichStim == 0)
			if key2 in keys:
				self.updateHUD('lastResp', label2)
				logging.info(f'User selected key1 ({key2})')
				correct = (whichStim == 1)
			if 'q' in keys or 'escape' in keys:
				raise UserExit()

			event.clearEvents()

		return correct

	def getBlockAndNonBlock(self):
		blockSeparatorKey = self.config['General settings']['separate_blocks_by'].lower()
		if blockSeparatorKey == 'orientations':
			nonBlockedKey = 'eccentricities'
		else:
			nonBlockedKey = 'orientations'

		return blockSeparatorKey, nonBlockedKey

	def blockVarsToEccentricityAndOrientation(self, blockVarName, blockVarValue, nonBlockVarValue):
		if blockVarName == 'eccentricities':
			return blockVarValue, nonBlockVarValue
		else:
			return nonBlockVarValue, blockVarValue

	def setupBlocks(self):
		'''
			blocks = [
				{'eccentricity': x, 'trials': [trial, trial, trial]},
				{'eccentricity': y, 'trials': [trial, trial, trial]},
				...
			]
		'''
		self.blocks = []

		self.stepHandlers = {}
		for eccentricity in self.config['Stimuli settings']['eccentricities']:
			self.stepHandlers[eccentricity] = {}
			for orientation in self.config['Stimuli settings']['orientations']:
				self.stepHandlers[eccentricity][orientation] = self.setupStepHandler()

		blockSeparatorKey, nonBlockedKey = self.getBlockAndNonBlock()
		for blockValue in self.config['Stimuli settings'][blockSeparatorKey]:
			block = {
				'blockBy': blockSeparatorKey,
				'blockValue': blockValue,
				'trials': [],
			}
			for nonBlockedValue in self.config['Stimuli settings'][nonBlockedKey]:
				eccentricity, orientation = self.blockVarsToEccentricityAndOrientation(blockSeparatorKey, blockValue, nonBlockedValue)
				possibleAngles = []

				for configTrial in range(self.config['Stimuli settings']['trials_per_stimulus_config']):
					if len(possibleAngles) == 0:
						possibleAngles = list(self.config['Stimuli settings']['stimulus_position_angles'])
						random.shuffle(possibleAngles)

					block['trials'].append(Trial(eccentricity, float(orientation), possibleAngles.pop()))

			random.shuffle(block['trials'])
			self.blocks.append(block)

		if self.config['General settings']['practice']:
			self.history = [0] * self.config['General settings']['practice_history']
			combinedBlock = {
				'blockBy': None,
				'blockValue': None,
				'trials': []
			}

			for block in self.blocks:
				combinedBlock['trials'] += block['trials']

			random.shuffle(combinedBlock['trials'])
			self.blocks = [combinedBlock]

		random.shuffle(self.blocks)
		for block in self.blocks:
			logging.debug('Block by {blockBy}:{blockValue}'.format(**block))
			for trial in block['trials']:
				logging.debug(f'\t{trial}')

	def runBlocks(self):
		blockSeparatorKey, nonBlockedKey = self.getBlockAndNonBlock()
		practiceWentOk = False

		for blockCounter, block in enumerate(self.blocks):
			# Show instructions
			self.showInstructions(blockCounter==0)
			# Run each trial in this block
			self.enableHUD()
			for trialCounter,trial in enumerate(block['trials']):
				self.win.flip()

				time.sleep(self.config['Stimuli settings']['time_between_stimuli'] / 1000.0)     # pause between trials
				self.runTrial(trial, self.stepHandlers[trial.eccentricity][trial.orientation])
				if self.config['General settings']['practice']:
					if sum(self.history) >= self.config['General settings']['practice_streak']:
						logging.info('Practice completed!')
						practiceWentOk = True
						break

			self.disableHUD()

			# Write output
			if self.config['General settings']['practice']:
				for eccentricity, eccDicts in self.stepHandlers.items():
					for orientation, stepHandler in eccDicts.items():
						result = self.stepHandlers[eccentricity][orientation].getBestParameters().T
						self.writeOutput(eccentricity, orientation, result)
			else:
				for nonBlockedValue in self.config['Stimuli settings'][nonBlockedKey]:
					eccentricity, orientation = self.blockVarsToEccentricityAndOrientation(blockSeparatorKey, block['blockValue'], nonBlockedValue)
					result = self.stepHandlers[eccentricity][orientation].getBestParameters().T
					self.writeOutput(eccentricity, orientation, result)

			# Take a break if it's time
			if blockCounter < len(self.blocks)-1:
				logging.debug('Break time')
				self.takeABreak()

		logging.debug('User is done!')
		if self.config['General settings']['practice']:
			return practiceWentOk
		else:
			return True

	def runTrial(self, trial, stepHandler):
		stimParams = stepHandler.next()[0]
		# These parameters are indices - not real values. They must be mapped
		stimParams = qcsf.mapStimParams(numpy.array([stimParams]), True)

		if len(config['Stimuli settings']['contrast_overrides']) > 0:
			# This is usually only used in practice mode
			contrast = random.choice(config['Stimuli settings']['contrast_overrides'])
		else:
			if stimParams[0] == 0:
				contrast = 1
			else:
				contrast = 1/stimParams[0] # convert sensitivity to contrast

		frequency = stimParams[1]
		logging.info(f'Presenting ecc={trial.eccentricity}, orientation={trial.orientation}, contrast={contrast}, frequency={frequency}, positionAngle={trial.stimPositionAngle}')
		whichStim = int(random.random() * 2)

		self.stim.sf = frequency
		self.stim.ori = trial.orientation
		self.stim.pos = (
			numpy.cos(trial.stimPositionAngle * numpy.pi/180.0) * trial.eccentricity,
			numpy.sin(trial.stimPositionAngle * numpy.pi/180.0) * trial.eccentricity,
		)

		stimString = 'F:%.2f, O:%.2f, C:%.2f, E:%.2f, P:%.2f' % (frequency, trial.orientation, contrast, trial.eccentricity, trial.stimPositionAngle)
		self.updateHUD('thisStim', stimString)
		expectedLabels = [
			self.config['Input settings']['first_stimulus_key_label'],
			self.config['Input settings']['second_stimulus_key_label'],
		]

		self.updateHUD('expectedResp', expectedLabels[whichStim])

		logging.info(f'Correct stimulus = {whichStim+1}')

		retries = 0
		needToRetry = True
		while retries <= self.config['Gaze tracking']['retries'] and needToRetry:
			retries += 1
			if self.config['Input settings']['wait_for_ready_key']:
				self.drawAnnuli(trial.eccentricity)
				self.waitForReadyKey()

			if self.config['Display settings']['show_fixation_aid']:
				self.drawFixationAid()
			else:
				self.fixationStim.draw()

			self.drawAnnuli(trial.eccentricity)
			self.win.flip()
			time.sleep(.5)
			if self.config['Gaze tracking']['wait_for_fixation']:
				if not self.waitForFixation():
					needToRetry = True
					self.config['gazeTone'].play()
					continue

			needToRetry = False

			for i in range(2):
				if self.config['Gaze tracking']['wait_for_fixation']:
					gazePos = self.getGazePosition()
					gazeAngle = math.sqrt(gazePos[0]**2 + gazePos[1]**2)

					logging.info(f'Gaze pos: {gazePos}')
					logging.info(f'Gaze angle: {gazeAngle}')
					if gazeAngle > self.config['Gaze tracking']['gaze_offset_max']:
						self.config['gazeTone'].play()
						logging.info('Participant looked away!')
						needToRetry = True
						continue

				if whichStim == i:
					self.stim.contrast = contrast
					if self.config['Gaze tracking']['render_at_gaze']:
						gazePos = self.getGazePosition()
						logging.info(f'Gaze pos: {gazePos}')
						self.stim.pos = [
							self.stim.pos[0] + gazePos[0],
							self.stim.pos[1] + gazePos[1]
						]
					self.stim.opacity = 1
				else:
					self.stim.opacity = 0

				self.config['sitmulusTone'].play() # play the tone
				self.stim.draw()
				self.drawFixationAid()

				self.drawAnnuli(trial.eccentricity)
				self.win.flip()          # show the stimulus

				time.sleep(self.config['Stimuli settings']['stimulus_duration'] / 1000.0)
				self.applyMasks(trial.eccentricity)
				self.drawFixationAid()
				self.drawAnnuli(trial.eccentricity)
				self.win.flip()          # hide the stimulus

				interStimulusTime = self.config['Stimuli settings']['time_between_stimuli'] / 1000.0
				if i < 1:
					time.sleep(interStimulusTime)     # pause between stimuli

			if self.config['Display settings']['show_fixation_aid']:
				self.drawFixationAid()
			else:
				self.fixationStim.draw()

			self.drawAnnuli(trial.eccentricity)
			self.win.flip()

			if not needToRetry:
				correct = self.checkResponse(whichStim)
				self.updateHUD('lastStim', stimString)
				self.updateHUD('thisStim', '')

				if correct:
					logging.debug('Correct response')
					self.updateHUD('lastOk', '✔', (-1, 1, -1))
					self.config['positiveFeedback'].play()
				else:
					logging.debug('Incorrect response')
					self.updateHUD('lastOk', '✘', (1, -1, -1))
					self.config['negativeFeedback'].play()

		if retries > self.config['Gaze tracking']['retries']:
			raise Exception('Max retries exceeded!')

		self.win.flip()
		logLine = f'E={trial.eccentricity},O={trial.orientation},C={contrast},F={frequency},Correct={correct}'
		logging.info(f'Response: {logLine}')
		stepHandler.markResponse(correct)
		if self.config['General settings']['practice']:
			self.history.pop(0)
			self.history.append(1 if correct else 0)

	def applyMasks(self, eccentricity=None):
		if self.config['Stimuli settings']['mask_time'] > 0:
			if eccentricity is None:
				eccentricities = self.annuli.keys()
			else:
				eccentricities = [eccentricity]

			for ecc in eccentricities:
				for mask in self.masks[ecc]:
					mask.draw()

			self.drawFixationAid()
			self.drawAnnuli(eccentricity)
			self.win.flip()
			time.sleep(self.config['Stimuli settings']['mask_time']/1000)

	def drawFixationAid(self):
		if self.config['Display settings']['show_fixation_aid']:
			[_.draw() for _ in self.fixationAid]

	def drawAnnuli(self, eccentricity=None):
		if self.config['Display settings']['show_annuli']:
			if eccentricity is None:
				eccentricities = self.annuli.keys()
			else:
				eccentricities = [eccentricity]

			for eccentricity in eccentricities:
				for circle in self.annuli[eccentricity]:
					circle.draw()

	def waitForReadyKey(self):
		self.showMessage('Ready?')

	def waitForFixation(self, target=[0,0]):
		logging.info(f'Waiting for fixation...')
		distance = self.config['Gaze tracking']['gaze_offset_max'] + 1
		startTime = time.time()
		fixationStartTime = None

		self.fixationStim.autoDraw = True
		fixated = None

		while fixated is None:
			currentTime = time.time()
			pos = self.getGazePosition()
			self.gazeMarker.pos = pos
			if self.config['show_gaze']:
				self.gazeMarker.draw()
			self.win.flip()

			distance = math.sqrt((target[0]-pos[0])**2 + (target[1]-pos[1])**2)
			if distance < self.config['Gaze tracking']['gaze_offset_max']:
				if fixationStartTime is None:
					fixationStartTime = currentTime
				elif currentTime - fixationStartTime > self.config['Gaze tracking']['fixation_period']:
					fixated = True
			else:
				fixationStartTime = None

			if time.time() - startTime > self.config['Gaze tracking']['max_wait_time']:
				fixated = False

		self.fixationStim.autoDraw = False
		return fixated

	def getGazePosition(self):
		pos = None
		while pos is None:
			time.sleep(0.1)
			pos = self.gazeTracker.getPosition()

		return PyPupilGazeTracker.PsychoPyVisuals.screenToMonitorCenterDeg(self.mon, pos)

	def start(self):
		exitCode = 0
		try:
			if not self.runBlocks():
				logging.critical('Participant failed practice')
				exitCode = 66
		except UserExit as exc:
			exitCode = 2
			logging.info(exc)
		except Exception as exc:
			exitCode = 1

			print('Exception: %s' % exc)
			traceback.print_exc()
			logging.critical(exc)
			self.showMessage('Something went wrong!\n\nPlease let the research assistant know.')

		if self.gazeTracker is not None:
			self.gazeTracker.stop()

		self.fixationStim.autoDraw = False
		self.showMessage('Good job - you are finished with this part of the study!\n\nPress the [SPACEBAR] to exit.')

		self.win.close()
		core.quit(exitCode)

os.makedirs('data', exist_ok=True)
config = getConfig()

if config['Gaze tracking']['wait_for_fixation'] or config['Gaze tracking']['render_at_gaze']:
	import PyPupilGazeTracker
	import PyPupilGazeTracker.smoothing
	import PyPupilGazeTracker.PsychoPyVisuals
	import PyPupilGazeTracker.GazeTracker

tester = PeripheralCSFTester(config)
tester.start()
