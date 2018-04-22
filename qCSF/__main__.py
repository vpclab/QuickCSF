import os, platform
import argparse
import time, random
import logging

from functools import partial
from collections import OrderedDict

from psychopy import core, visual, gui, data, event, monitors, sound
import numpy

import qcsf, settings

def setupMonitor(settings):
	mon = monitors.Monitor('testMonitor')
	mon.setDistance(settings['monitor_distance'])  # Measure first to ensure this is correct
	mon.setWidth(settings['monitor_width'])  # Measure first to ensure this is correct

	win = visual.Window(fullscr=True, monitor='testMonitor', allowGUI=False, units='deg')

	return mon, win

def setupOutput(settings):
	# make a text file to save data
	fileName = settings['session_id'] + data.getDateStr()
	dataFile = open('data/'+fileName+'.csv', 'w')  # a simple text file with 'comma-separated-values'
	dataFile.write('Eccentricity,Orientation,Trial,Contrast,Frequency,Correct\n')

	return dataFile

def setupStepHandler():
	stimulusSpace = numpy.array([
		numpy.arange(0, 31),	# Contrast
		numpy.arange(0, 24),	# Frequency
	])
	parameterSpace = numpy.array([
		numpy.arange(0, 28),	# Peak sensitivity
		numpy.arange(0, 21),	# Peak frequency
		numpy.arange(0, 21),	# Log bandwidth
		numpy.arange(0, 21)		# Low frequency truncation (log delta)
	])

	return qcsf.QCSF(stimulusSpace, parameterSpace)

def showIntro(win, settings):
	key1 = settings['first_stimulus_key']
	key2 = settings['second_stimulus_key']

	instructions = 'In this experiment, you will be presented with two options - one will be blank, and the other will be a stimulus.\n\n'
	instructions += 'A tone will play when each option is displayed. After both tones, you will need to select which option contained the stimulus.\n\n'
	instructions += 'If the stimulus appeared during the FIRST tone, press [' + key1.upper() + '].\n'
	instructions += 'If the stimulus appeared during the SECOND tone, press [' + key2.upper() + '].\n\n'
	instructions += 'If you are uncertain, make a guess.\n\n\nPress any key to start.'
	
	instructionsStim = visual.TextStim(win, text=instructions, color=-1, wrapWidth=40)
	instructionsStim.draw()

	win.flip()

	keys = event.waitKeys()
	if 'escape' in keys:
		core.quit()

def takeABreak(win):
	instructions = 'Good job - it\'s now time for a break!\n\nWhen you are ready to continue, press the SPACEBAR.'
	instructionsStim = visual.TextStim(win, text=instructions, color=-1, wrapWidth=20)
	instructionsStim.draw()

	win.flip()

	keys = []
	while not 'space' in keys:
		keys = event.waitKeys()
		if 'escape' in keys:
			core.quit()

def blank(win):
	static = [
		visual.DotStim(win, nDots=1024, fieldSize=60, dotSize=16, color=3*[-.75]),
		visual.DotStim(win, nDots=1024, fieldSize=60, dotSize=16, color=3*[0.75]),
	]
	for i in range(2):
		[dots.draw() for dots in static]
	
	win.flip()

def getSettings():
	config = settings.getSettings()
	for k in ['eccentricities', 'orientations']:
		if isinstance(config[k], str):
			config[k] = config[k].split(' ')
		else:
			config[k] = [config[k]]

	return config

def getSound(fileName, freq, duration):
	try:
		return sound.Sound(fileName, stereo=True)
	except ValueError:
		return sound.Sound(freq, secs=duration, stereo=True)

def runTrials(settings, win, dataFile):
	key1 = settings['first_stimulus_key']
	key2 = settings['second_stimulus_key']

	stim = visual.GratingStim(win, contrast=1, sf=6, size=4, mask='gauss')

	instructions = 'If the stimulus appeard during the FIRST tone, press [' + key1.upper() + '].\n\n'
	instructions += 'If the stimulus appeard during the SECOND tone, press [' + key2.upper() + '].\n\n'
	instructionsStim = visual.TextStim(win, text=instructions, color=-1, wrapWidth=20)

	sitmulusTone = getSound('qCSF/assets/300Hz_sine_25.wav', 300, .2)
	positiveFeedback = getSound('qCSF/assets/1000Hz_sine_50.wav', 1000, .077)
	negativeFeedback = getSound('qCSF/assets/600Hz_square_25.wav', 600, .185)

	eccentricities = settings['eccentricities']
	random.shuffle(eccentricities)
	logging.debug(f'Eccentricity order: {eccentricities}')

	results = OrderedDict()

	for eccentricity in eccentricities:
		showIntro(win, settings)

		stepHandlers = {}
		for orientation in settings['orientations']:
			stepHandlers[orientation] = setupStepHandler()
		
		for trial in range(int(settings['trials_per_condition'])):
			orientations = list(settings['orientations']) # make a copy
			random.shuffle(orientations)
			logging.debug(f'Orientation order: {orientations}')

			for orientation in orientations:
				win.flip()
				time.sleep(.5)
				stepHandler = stepHandlers[orientation]

				stimParams = stepHandler.next()
				contrast = 1/stimParams[0] # convert sensitivity to contrast
				frequency = stimParams[1]
				logging.info(f'Presenting contrast={contrast}, frequency={frequency}, orientation={orientation}')

				# These parameters are indices - not real values. They must be mapped
				stimParams = qcsf.mapStimParams(numpy.array([stimParams]), True)

				stim.contrast = contrast
				stim.sf = frequency
				stim.ori = float(orientation)

				whichStim = int(random.random() * 2)
				logging.info(f'Correct stimulus = {whichStim+1}')
				for i in range(2):
					if whichStim == i:
						stim.draw()

					win.flip()          # show the stimulus
					sitmulusTone.play() # play the tone
					win.flip()          # hide the stimulus
					time.sleep(0.5)     # pause between stimuli

				instructionsStim.draw()
				win.flip()

				# get response
				correct = None
				while correct is None:
					keys = event.waitKeys()
					if key1 in keys:
						logging.info(f'User selected key1 ({key1})')
						correct = (whichStim == 0)
					if key2 in keys:
						logging.info(f'User selected key1 ({key2})')
						correct = (whichStim == 1)
					if 'q' in keys or 'escape' in keys:
						core.quit()
					event.clearEvents()  # clear other (eg mouse) events - they clog the buffer

				if correct:
					logging.debug('Correct response')
					positiveFeedback.play()
				else:
					logging.debug('Incorrect response')
					negativeFeedback.play()

				win.flip()
				logLine = f'{eccentricity},{orientation},{trial},{contrast},{frequency},{correct}'
				logging.debug(f'Logging: {logLine}')
				dataFile.write(logLine + '\n')
				stepHandler.markResponse(correct)

			logging.debug(f'Done with trial {trial}')

		logging.debug(f'Done with orientation {orientation}')
		results[eccentricity] = OrderedDict()
		for orientation in settings['orientations']:
			results[eccentricity][orientation] = stepHandlers[orientation].getParameterEstimates()

		if eccentricity != eccentricities[-1]:
			logging.debug('Break time')
			takeABreak(win)

	logging.debug('User is done!')
	return results

def main():
	logFile = f'logs/{platform.node()}-{data.getDateStr()}.log'
	logging.basicConfig(filename=logFile, level=logging.DEBUG)

	os.makedirs('data', exist_ok=True)

	allSettings = getSettings()
	mon, win = setupMonitor(allSettings)
	dataFile = setupOutput(allSettings)

	sound.init()
	parameterEstimates = runTrials(allSettings, win, dataFile)

	print('*************')
	print(parameterEstimates)
	print('*************')
	dataFile.close()
	win.close()

	core.quit()

main()