import random

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
	def __init__(self, fixedSize, *params, **kwargs):
		super().__init__(*params, **kwargs)

		self.fixedSize = fixedSize

	def next(self):
		stimulus = super().next()

		return gaborPatch.ContrastGaborPatchImage(
			size=self.fixedSize,
			contrast=stimulus.contrast,
			frequency=stimulus.frequency/100,
			orientation=random.random() * 360,
		)
