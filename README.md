# qCSF

A fast, adaptive approach to estimating contrast sensitivity function parameters across multiple eccentricities and stimulus orientations.

This implmentation is based on:

> Lesmes, L. A., Lu, Z. L., Baek, J., & Albright, T. D. (2010). Bayesian adaptive estimation of the contrast sensitivity function: The quick CSF method. *Journal of visio*n, 10(3), 17-17.

Special thanks to Dr. Tianshi Lu at Wichita State University for providing a Matlab implemenation of the fundamental algorithm.

## Install dependencies
~~~~
$ pip3 install -r requirements.txt
~~~~

## Execute
To run an evaluation:
~~~~
$ python3 qCSF --help

usage: python3 qCSF

optional arguments:
  -h, --help            show this help message and exit
  --session_id [SESSION_ID]
  --skip_settings_dialog [SKIP_SETTINGS_DIALOG]
  --always_show_help [ALWAYS_SHOW_HELP]
  --data_filename [DATA_FILENAME]
  --monitor_width [MONITOR_WIDTH]
  --monitor_distance [MONITOR_DISTANCE]
  --fixation_size [FIXATION_SIZE]
  --trials_per_condition [TRIALS_PER_CONDITION]
  --eccentricities [ECCENTRICITIES]
  --orientations [ORIENTATIONS]
  --stimulus_angle [STIMULUS_ANGLE]
  --stimulus_duration [STIMULUS_DURATION]
  --time_between_stimuli [TIME_BETWEEN_STIMULI]
  --first_stimulus_key [FIRST_STIMULUS_KEY]
  --second_stimulus_key [SECOND_STIMULUS_KEY]
  ~~~~

To simulate and visualize an evaluation:
~~~~
$ python3 qCSF/qcsf.py
~~~~