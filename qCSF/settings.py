import os, re

import psychopy
from psychopy.tools import filetools

def getSettings(save=True):
	fields = [
		[ 'Session ID', '' ],
		[ '' ],
		[ 'Monitor width (cm)', 40 ],
		[ 'Monitor distance (cm)', 57],
	]

	# try to get a previous parameters file
	settingsFile = os.path.join('data/lastParams.psydat')
	try: 
		savedInfo = filetools.fromFile(settingsFile)
		savedInfo['Session ID'] = ''
	except:  # if not there then use a default set
		savedInfo = {}
		pass

	# build the dialog
	settingsDialog = psychopy.gui.Dlg(title='qCSF Settings')
	def nameConverter(label):
		val = re.sub('\\([^\\)]*\\)', '', label)
		return val.strip()

	for field in fields:
		if len(field) == 2:
			label, value = field
			fieldName = nameConverter(label)

			if fieldName in savedInfo:
				value = savedInfo[fieldName]

			settingsDialog.addField(label, value)
		else:
			settingsDialog.addText(field[0])

	# show the dialog
	data = settingsDialog.show()

	# save the data from the dialog
	if data is not None:
		for i,value in enumerate(data):
			fieldName = nameConverter(settingsDialog.inputFieldNames[i])
			savedInfo[fieldName] = value

		if save:
			filetools.toFile(settingsFile, savedInfo)  # save params to file for next time
	else:
		psychopy.core.quit()

	return savedInfo