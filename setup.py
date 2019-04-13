#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

import importlib

dependencies = [ 'QtPy>=1.7.0', 'numpy>=1.16.2', 'matplotlib>=3.0.3', 'argparseqt>=0.2.1' ]

for binding in ['PySide2', 'PyQt5', 'PySide', 'PyQt']:
	spec = importlib.util.find_spec(binding)
	if spec is not None:
		break
else:
	dependencies.append('PySide2>=5.12.2')

setup(
	name='QuickCSF',
	version='2.0',
	description='A fast, adaptive approach to estimating contrast sensitivity function parameters across multiple eccentricities and stimulus orientations.',
	author='Dominic Canare',
	author_email='dom@dominiccanare.com',
	packages=['QuickCSF'],
	install_requires=dependencies,
	package_data={'QuickCSF': ['assets/*']},
	include_package_data=True
)
