from functools import partial
import os
from collections import OrderedDict

from psychopy import core, visual, gui, data, event, monitors

import numpy, random

import qcsf, settings

def setupMonitor(settings):
	mon = monitors.Monitor('testMonitor')
	mon.setDistance(settings['Monitor distance'])  # Measure first to ensure this is correct
	mon.setWidth(settings['Monitor width'])  # Measure first to ensure this is correct

	win = visual.Window(fullscr=True, monitor='testMonitor', units='deg')

	return mon, win

def setupOutput(settings):
	# make a text file to save data
	fileName = settings['Session ID'] + data.getDateStr()
	dataFile = open('data/'+fileName+'.csv', 'w')  # a simple text file with 'comma-separated-values'
	dataFile.write('Trial,Contrast,Frequency,Response,Estimates\n')

	return dataFile

def setupStepHandler():
	stimulusSpace = numpy.array([
		numpy.arange(0, 24),	# Contrast
		numpy.arange(0, 31),	# Frequency
	])
	parameterSpace = numpy.array([
		numpy.arange(0, 28),	# Peak sensitivity
		numpy.arange(0, 21),	# Peak frequency
		numpy.arange(0, 21),	# Log bandwidth
		numpy.arange(0, 21)		# Low frequency truncation (log delta)
	])

	return qcsf.QCSF(stimulusSpace, parameterSpace)

def showIntro(win):
	lines = [
		visual.TextStim(win, text='Press → if you can see the stimulus.', pos=(0,0.75)),
		visual.TextStim(win, text='Press ← if you cannot.', pos=(0,-0.75))
	]
	for line in lines:
		line.color = -1
		line.wrapWidth = 20
		line.draw()

	win.flip()

	event.waitKeys()

def blank(win):
	static = [
		visual.DotStim(win, nDots=1024, fieldSize=60, dotSize=8, color=3*[-.75]),
		visual.DotStim(win, nDots=1024, fieldSize=60, dotSize=8, color=3*[0.75]),
	]
	for i in range(2):
		[dots.draw() for dots in static]
	
	win.flip()
	core.wait(0.3)

def runTrials(win, stepHandler, dataFile):
	stim = visual.GratingStim(win, contrast=1, sf=6, size=4, mask='gauss')

	#for thisIncrement in staircase:  # will continue the staircase until it terminates!
	for trial in range(15):
		stimParams = stepHandler.next()
		print('Presenting %s' % stimParams)

		# @TODO: These parameters are indices - not real values :(
		stim.contrast = stimParams[0]
		stim.sf = stimParams[1]

		stim.draw()
		win.flip()

		# get response
		thisResponse = None
		while thisResponse is None:
			allKeys = event.waitKeys()
			for thisKey in allKeys:
				if thisKey=='left':
					thisResponse = 0
				elif thisKey=='right':
					thisResponse = 1
				elif thisKey in ['q', 'escape']:
					core.quit()
			event.clearEvents()  # clear other (eg mouse) events - they clog the buffer

		blank(win)
		# add the data to the staircase so it can calculate the next level

		logLine = '%i %.4f %.4f %i %s' % (trial, stim.contrast, stim.sf[0], thisResponse, stepHandler.getParameterEstimates().T)
		print(logLine.replace(' ', ','))
		dataFile.write(logLine)
		stepHandler.markResponse(thisResponse)


def showFeedback(win, params):
	message  = f'Peak Sensitivity:\n\t{params[0]:.4f}\n\n'
	message += f'Peak Frequency:\n\t{params[1]:.4f}\n\n'
	message += f'Bandwidth:\n\t{params[2]:.4f}\n\n'
	message += f'Delta:\n\t{params[3]:.4f}\n\n'

	feedback1 = visual.TextStim(win, text=message)
	feedback1.draw()
	win.flip()

	while True:
		allKeys = event.waitKeys()
		if 'q' in allKeys or 'escape' in allKeys:
			return



expInfo = settings.getSettings()
mon, win = setupMonitor(expInfo)
dataFile = setupOutput(expInfo)
stepHandler = setupStepHandler()

showIntro(win)
runTrials(win, stepHandler, dataFile)

dataFile.close()

showFeedback(win, stepHandler.getParameterEstimates())
win.close()

core.quit()
