import os, sys

def getFilePath(filename):
	if getattr(sys, 'frozen', False):
		# onefile frozen mode
		rootDir = sys._MEIPASS
	else:
		exe = os.path.basename(sys.executable)
		if exe[:6] == 'python':
			# Dev mode
			rootDir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		else:
			# onedir frozen mode
			rootDir = os.path.dirname(sys.executable)

	
	return os.path.join(rootDir, filename)
