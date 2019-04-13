#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from setuptools import setup
import importlib

dependencies = [ 'QtPy>=1.7.0', 'numpy>=1.16.2', 'matplotlib>=3.0.3', 'argparseqt>=0.2.1' ]

for binding in ['PySide2', 'PyQt5', 'PySide', 'PyQt']:
	spec = importlib.util.find_spec(binding)
	if spec is not None:
		break
else:
	dependencies.append('PySide2>=5.12.2')



this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
	long_description = f.read()

setup(
	name='QuickCSF',
	version='2.0',
	description='A fast, adaptive approach to estimating contrast sensitivity function parameters',
	url='https://github.com/domstoppable/QuickCSF',
	author='Dominic Canare',
	author_email='dom@dominiccanare.com',
	license='GPL',
	packages=['QuickCSF'],
	install_requires=dependencies,
	long_description=long_description,
	long_description_content_type='text/markdown',
	package_data={'QuickCSF': ['assets/*']},
	include_package_data=True
)
