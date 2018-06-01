import os, sys

def getFilePath(filename):
	if getattr(sys, 'frozen', False):
		# onefile frozen mode
		rootDir = sys._MEIPASS
	else:
		if sys.executable.endswith('python') or sys.executable.endswith('python.exe'):
			# Dev mode
			rootDir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
		else:
			# onedir frozen mode
			rootDir = os.path.dirname(sys.executable)

	
	return os.path.join(rootDir, filename)
