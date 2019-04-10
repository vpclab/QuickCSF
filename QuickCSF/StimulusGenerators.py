import random

import numpy

from . import QuickCSF
from . import gaborPatch

class Stimulus:
	def __init__(self, contrast, frequency, orientation, size):
		self.contrast = contrast
		self.frequency = frequency
		self.orientation = orientation
		self.size = size

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return f'c={self.contrast},f={self.frequency},o={self.orientation},s={self.size}'

class RandomOrientationGenerator(QuickCSF.QuickCSFEstimator):
	def __init__(self,
		size=100,
		minContrast=.01, maxContrast=1.0, contrastResolution=24,
		minFrequency=0.2, maxFrequency=36.0, frequencyResolution=20,
		degreesToPixels=None
	):
		print(locals())
		super().__init__(
			stimulusSpace = numpy.array([
				QuickCSF.makeContrastSpace(minContrast, maxContrast, contrastResolution),
				QuickCSF.makeFrequencySpace(minFrequency, maxFrequency, frequencyResolution)
			])
		)

		if degreesToPixels is None:
			self.degreesToPixels = lambda x: x

		self.size = size
		self.degreesToPixels = degreesToPixels

	def next(self):
		stimulus = super().next()

		return gaborPatch.ContrastGaborPatchImage(
			size=self.degreesToPixels(self.size),
			contrast=stimulus.contrast,
			frequency=1/self.degreesToPixels(1/stimulus.frequency),
			orientation=random.random() * 360,
		)
