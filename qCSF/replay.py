import sys, time, logging

import matplotlib
import matplotlib.pyplot as plt
import numpy

import qcsf

def replay(qcsfObject, history, fig=None):
	if fig is None:
		fig = plt.figure()

	graph = fig.add_subplot(1, 1, 1)
	#plt.ion()
	#plt.show()

	qcsfObject.visual(graph)

	for i,record in enumerate(history):
		stimValues = [1/record['contrast'], record['frequency']]
		stimIndex = qcsfObject.getStimIndex(stimValues)
		qcsfObject.markResponse(record['correct'], numpy.array([[stimIndex]]))
	graph.clear()
	graph.set_title(f'Estimated CSF @ {record["orientation"]} ({i+1})')
	qcsfObject.visual(graph, None, True)

	

if __name__ == '__main__':
	histories = {}

	with open(sys.argv[1], 'r') as logFile:
		lines = logFile.readlines()
		for line in lines:
			timeStamp = line[:19]
			level = line[20:29].strip()
			message = line[29:].strip()

			if message.startswith('Presenting '):
				lastRecord = {'time': timeStamp}

				tokens = message[11:].replace('[', '').replace(']', '').split(', ')
				keyValues = [t.split('=') for t in tokens]
				for key, value in keyValues:
					lastRecord[key] = float(value)

				if lastRecord['orientation'] not in histories:
					histories[lastRecord['orientation']] = []

				histories[lastRecord['orientation']].append(lastRecord)
			elif message.startswith('Correct stimulus = '):
				lastRecord['correctStimulus'] = message[19:]
			elif message.startswith('Correct response'):
				lastRecord['correct'] = True
			elif message.startswith('Incorrect response'):
				lastRecord['correct'] = False

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
	for orientation,records in histories.items():
		qcsfObject = qcsf.QCSF(stimulusSpace, parameterSpace)
		replay(qcsfObject, records)
		
	plt.ion()
	plt.show(block=True)

	#time.sleep(99999)
