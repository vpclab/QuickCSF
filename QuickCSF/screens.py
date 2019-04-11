# -*- coding: utf-8 -*
'''Useful functions for working with different monitors'''

import math

from qtpy import QtCore, QtGui

def getPrimaryScreen():
	return QtGui.QGuiApplication.primaryScreen()

def getSecondaryScreen():
	primary = getPrimaryScreen()
	for screen in QtGui.QGuiApplication.screens():
		if screen.name() != primary.name():
			return screen

def getActiveScreen(widget=None):
	'''Returns the screen object which is currently active

		Args:
			widget (optional): if specified, it's center will be used to determine the "active" screen
				If not specified, widget with focus will be used
				If no widget has focus, returns primary screen
	'''
	if widget is None:
		widget = QtGui.QGuiApplication.focusWindow()
		if widget is None:
			return getPrimaryScreen()
			
	windowCenter = widget.geometry().center()
	return QtGui.QGuiApplication.screenAt(windowCenter)

def degreesToPixels(degrees, distance_mm, screen=None):
	'''Converts visual angle to pixels
		Note:
			Does NOT account for monitor flatness!

		Args:
			degrees: the size of the visual angle
			distance_mm: the distance between the observer and the screen in millimeters
			screen (optional): which screen's metrics to use
	'''
	if screen is None:
		screen = getActiveScreen()

	return degrees / math.degrees(math.atan((screen.physicalSize().width() / screen.geometry().width()) / distance_mm))

def moveToScreen(window, screen):
	'''Moves a window to a specific screen and attempts to preserve state / location

		Args:
			window: the window to be moved
			screen: the target screen to receive the window
	'''
	state = window.windowState()
	window.showNormal()
	window.move(screen.geometry().center() - QtCore.QPoint(window.geometry().width(), window.geometry().height())/2)
	QtCore.QTimer.singleShot(1, lambda: window.setWindowState(state))

def moveToSecondaryScreen(window):
	moveToScreen(window, getSecondaryScreen())

def moveToPrimaryScreen(window):
	moveToScreen(window, getPrimaryScreen())

if __name__ == '__main__':
	from qtpy import QtWidgets

	def updateButton():
		screen = getActiveScreen()
		print(screen.name())

		window.setText(str(degreesToPixels(3, 750)))
		moveToSecondaryScreen(window)

	app = QtWidgets.QApplication()
	window = QtWidgets.QPushButton()
	window.setText('hi')

	window.clicked.connect(updateButton)

	window.show()
	app.exec_()
