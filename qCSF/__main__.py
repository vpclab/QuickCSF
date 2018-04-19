import os
from collections import OrderedDict

from psychopy import core, visual, gui, data, event, monitors
from psychopy.tools.filetools import fromFile, toFile

import numpy, random

import qcsf


def blank(win):
	oldColor = win.color
	win.color = [ .25, .25, 0 ]
	win.clearBuffer()
	win.flip()
	core.wait(0.5)
	win.color = oldColor
	win.flip()

def getSettings():
	defaultSettings = OrderedDict(
		monitorWidth = 40,
		monitorDistance = 57,
		monitorResolution = '2560x1440',
	#	monitorResolution = '1920x1200',
	)

	# try to get a previous parameters file
	settingsFile = os.path.join('data/lastParams.psydat')
	try: 
		expInfo = fromFile(settingsFile)
	except:  # if not there then use a default set
		expInfo = defaultSettings

	expInfo['Participant'] = ''
	expInfo['Datetime'] = data.getDateStr()  # add the current time

	# present a dialogue to change params
	dlg = gui.DlgFromDict(expInfo, title='Quick CSF', fixed=['Datetime'])
	if dlg.OK:
		toFile(settingsFile, expInfo)  # save params to file for next time
	else:
		core.quit()  # the user hit cancel so exit

	return expInfo

def setupMonitor(settings):
	mon = monitors.Monitor('testMonitor')
	mon.setDistance(settings['monitorDistance'])  # Measure first to ensure this is correct
	mon.setWidth(settings['monitorWidth'])  # Measure first to ensure this is correct
	mon.setSizePix([int(dimension) for dimension in settings['monitorResolution'].split('x')])

	win = visual.Window(fullscr=True, monitor='testMonitor', units='deg')

	return mon, win

def setupOutput(settings):
	# make a text file to save data
	fileName = settings['Participant'] + settings['Datetime']
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
	message1 = visual.TextStim(win, text='Press ⇨ if you can see the stimulus.\nPress ⇦ if you cannot.')
	message1.draw()
	win.flip()

	#pause until there's a keypress
	event.waitKeys()

def runTrials(win, stepHandler, dataFile):
	stim = visual.GratingStim(win, contrast=1, sf=6, size=4, mask='gauss')

	#for thisIncrement in staircase:  # will continue the staircase until it terminates!
	for trial in range(5):
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

		# add the data to the staircase so it can calculate the next level
		stepHandler.markResponse(thisResponse)
		logLine = '%i %.4f %.4f %i %s' % (trial, stim.contrast, stim.sf[0], thisResponse, stepHandler.getParameterEstimates().T)
		print(logLine.replace(' ', ','))
		dataFile.write(logLine)

		blank(win)

def showFeedback(win, params):
	message = f'Your CSF Parameters:\n\n'
	message += f'Peak Sensitivity:\n\t{params[0]:.4f}\n\n'
	message += f'Peak Frequency:\n\t{params[1]:.4f}\n\n'
	message += f'Bandwidth:\n\t{params[2]:.4f}\n\n'
	message += f'Delta:\n\t{params[3]:.4f}\n\n'
	message += '[Escape] to quit'

	feedback1 = visual.TextStim(win, text=message)
	feedback1.draw()
	win.flip()

	while True:
		allKeys = event.waitKeys()
		if 'q' in allKeys or 'escape' in allKeys:
			return



expInfo = getSettings()
mon, win = setupMonitor(expInfo)
dataFile = setupOutput(expInfo)
stepHandler = setupStepHandler()

showIntro(win)
runTrials(win, stepHandler, dataFile)

dataFile.close()

showFeedback(win, stepHandler.getParameterEstimates())
win.close()

core.quit()
