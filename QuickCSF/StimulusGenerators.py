'''Classes to generate stimuli for testing'''

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

class QuickCSFGenerator(QuickCSF.QuickCSFEstimator):
	''' Generate fixed-size stimuli with contrast/spatial frequency determined by QuickCSF
	
		If orientation is None, random orientations will be generated
	'''

	def __init__(self,
		size=100, orientation=None,
		minContrast=.01, maxContrast=1.0, contrastResolution=24,
		minFrequency=0.2, maxFrequency=36.0, frequencyResolution=20,
		minPeakSensitivity=2, maxPeakSensitivity=1000, peakSensitivityResolution=28,
		minPeakFrequency=0.2, maxPeakFrequency=20, peakFrequencyResolution=21,
		minBandwidth=1, maxBandwidth=10, bandwidthResolution=21,
		minLogDelta=0.02, maxLogDelta=2, logDeltaResolution=21,
		degreesToPixels=None
	):
		super().__init__(
			stimulusSpace = numpy.array([
				QuickCSF.makeContrastSpace(minContrast, maxContrast, contrastResolution),
				QuickCSF.makeFrequencySpace(minFrequency, maxFrequency, frequencyResolution)
			]),
			parameterSpace = numpy.array([
				QuickCSF.makePeakSensitivitySpace(minPeakSensitivity, maxPeakSensitivity, peakSensitivityResolution),
				QuickCSF.makePeakFrequencySpace(minPeakFrequency, maxPeakFrequency, peakFrequencyResolution),
				QuickCSF.makeBandwidthSpace(minBandwidth, maxBandwidth, bandwidthResolution),
				QuickCSF.makeLogDeltaSpace(minLogDelta, maxLogDelta, logDeltaResolution)
			])
		)

		self.size = size
		self.orientation = orientation

		if degreesToPixels is None:
			self.degreesToPixels = lambda x: x
		else:
			self.degreesToPixels = degreesToPixels

	def next(self):
		stimulus = super().next()

		if self.orientation is None:
			orientation = random.random() * 360
		else:
			orientation = self.orientation

		return gaborPatch.ContrastGaborPatchImage(
			size=self.degreesToPixels(self.size),
			contrast=stimulus.contrast,
			frequency=1/self.degreesToPixels(1/stimulus.frequency),
			orientation=orientation
		)
