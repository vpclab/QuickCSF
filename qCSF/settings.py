import os, re
import argparse

import psychopy
import psychopy.gui, psychopy.core

from psychopy.tools import filetools

settingGroups = {
	'Session settings': [ 
		['Session ID', ''],
		['Skip settings dialog', False],
	],
	'Display settings': [
		['Monitor width (cm)', 40],
		['Monitor distance (cm)', 57]
	],
	'Experiment settings': [
		['Trials per condition', 25],
		['Eccentricities (degrees)', '4 8 12'],
		['Orientations (degrees)', '45 67.5 90 112.5 135']
	]
}

def labelToFieldName(label):
	val = re.sub('\\([^\\)]*\\)', '', label) # strip stuff in parentheses
	val = val.strip().replace(' ', '_').lower()

	return val.strip()

def formatLabel(label):
	return f'&nbsp;&nbsp;&nbsp;&nbsp;<span>{label}</span>'

def formattedLabelToFieldName(label):
	return labelToFieldName(label[label.index('<span>')+6:-7])

def parseArguments():
	parser = argparse.ArgumentParser()

	for _, fields in settingGroups.items():
		for field in fields:
			label, default = field
			if isinstance(default, bool):
				default = not default
			parser.add_argument('--' + labelToFieldName(label), nargs='?', const=default)

	args, unknown = parser.parse_known_args()
	if len(unknown) > 0:
		print(f'UNRECOGNIZED ARGUMENTS: {unknown}')

	return vars(args)

def getSettings(save=True):
	settings = {}
	# Defaults
	for group, fields in settingGroups.items():
		for field in fields:
			label, value = field
			fieldName = labelToFieldName(label)
			settings[fieldName] = value

	# Saved parameters
	settingsFile = os.path.join('settings.psydat')
	try: 
		savedInfo = filetools.fromFile(settingsFile)
		for k,v in savedInfo.items():
			if k != 'session_id':
				settings[k] = v
	except:  # if not there then use a default set
		pass

	# Command line arguments
	commandLineArgs = parseArguments()
	for k,v in commandLineArgs.items():
		if v is not None:
			settings[k] = v

	# GUI
	if not settings['skip_settings_dialog']:
		# build the dialog
		settingsDialog = psychopy.gui.Dlg(title='qCSF Settings')

		for group, fields in settingGroups.items():
			settingsDialog.addText(f'<h3 style="text-align:left;weight:bold">{group}</h3>')

			for field in fields:
				label, value = field

				fieldName = labelToFieldName(label)
				formattedLabel = formatLabel(label)

				if value is not None and value != '':
					tip = f'Default: {value}'
				else:
					tip = ''

				if fieldName in settings:
					value = settings[fieldName]

				settingsDialog.addField(formattedLabel, value, tip=tip)

		# show the dialog
		data = settingsDialog.show()

		# retrieve data from the dialog
		if data is not None:
			for i,value in enumerate(data):
				fieldName = formattedLabelToFieldName(settingsDialog.inputFieldNames[i])
				settings[fieldName] = value
		else:
			psychopy.core.quit()

	if save:
		filetools.toFile(settingsFile, settings)  # save params to file for next time

	return settings

if __name__ == '__main__':
	settings = getSettings()
	for k,v in settings.items():
		print(f'{k} = {v}')
