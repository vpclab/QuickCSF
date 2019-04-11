# -*- coding: utf-8 -*
'''Gabor patches as QImages'''

import math

from qtpy import QtGui

class GaborPatchImage(QtGui.QImage):
	'''Create a gabor patch'''

	def __init__(self,
		size=100,
		orientation=45,
		gaussianStd=None,
		frequency=.1,
		phase=math.tau/4,
		color1=QtGui.QColor(255, 255, 255),
		color2=QtGui.QColor(0, 0, 0)
	):
		'''Create a gabor patch QImage

			Args:
				size: the width and height in pixels
				orienation: grating orientation in degrees
				gaussianStd: gaussian smoothing standard deviation in pixels
				frequency: spatial frequency in cycles per pixel
				phase: phase shift
				color1: the first color
				color2: the second color
		'''
		super().__init__(size, size, QtGui.QImage.Format_ARGB32)
		
		self.size = size
		self.orientation = orientation
		self.gaussianStd = gaussianStd if not gaussianStd is None else size/8
		self.frequency = frequency
		self.phase = phase
		self.color1 = color1
		self.color2 = color2

		self.setPixels()

	def setPixels(self):
		# convert orientation degrees to radians
		self.orientation = (self.orientation+90) * math.tau / 360

		# Convert the size to a factor of the standard deviation
		self.size = self.size / self.gaussianStd

		self.color1 = self.color1.getRgb()
		self.color2 = self.color2.getRgb()

		for rx in range(0, int(self.size * self.gaussianStd)):
			for ry in range(0, int(self.size * self.gaussianStd)):
				# The x,y from the center
				dx = rx - 0.5 * self.gaussianStd * self.size
				dy = ry - 0.5 * self.gaussianStd * self.size

				# The angle of the pixel
				t = math.atan2(dy, dx) + self.orientation

				# The distance of the pixel from the center
				r = math.sqrt(dx * dx + dy * dy)
				
				# The coordinates in the unrotated image
				x = r * math.cos(t)
				y = r * math.sin(t)

				# The amplitude without envelope (from 0 to 1)
				amp = 0.5 + 0.5 * math.cos(self.phase + math.tau * (x * self.frequency))

				# The amplitude of the pixel (from 0 to 1)
				f = math.e**(-0.5 * pow(x / self.gaussianStd, 2) - 0.5 * pow(y / self.gaussianStd, 2))

				# color components
				r = self.color1[0] * amp + self.color2[0]*(1-amp)
				g = self.color1[1] * amp + self.color2[1]*(1-amp)
				b = self.color1[2] * amp + self.color2[2]*(1-amp)
				a = f * (self.color1[3] * amp + self.color2[3] * (1-amp))

				self.setPixel(rx, ry, QtGui.qRgba(r, g, b, a))

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return f'{self.__class__.__name__}(' + str(vars(self)) + ')'


class ContrastGaborPatchImage(GaborPatchImage):
	def __init__(self, contrast=1.0, *args, **kwargs):
		'''Create a black-and-white gabor patch QImage by specifiying contrast

			Args:
				contrast: a value between 0-1 indicating how much contrast should be present between dark and light bands
		'''

		self.contrast = contrast

		luminance = 255 * (0.5 + 0.5 * contrast)
		color1 = QtGui.QColor(luminance, luminance, luminance)

		luminance = 255 * (0.5 - 0.5 * contrast)
		color2 = QtGui.QColor(luminance, luminance, luminance)

		super().__init__(color1=color1, color2=color2, *args, **kwargs)

