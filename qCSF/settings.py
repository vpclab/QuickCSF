import typing
from ConfigHelper import ConfigHelper, ConfigGroup, Setting # https://git.vpclab.com/VPCLab/ConfigHelper
from PySide2.QtWidgets import QApplication

PROGRAM_NAME = 'PyOrientationDiscrimination'

SETTINGS_GROUP = [
	ConfigGroup('General settings',
		Setting('Session ID',           str, '', helpText='ex. Day1_ParticipantID'),
		Setting('Data filename',        str, 'data/PCSF_{start_time}_{session_id}'),

	), ConfigGroup('Gaze tracking',
		Setting('Wait for fixation',           bool,      False),
		Setting('Max wait time (s)',           int,       10,   helpText='In seconds'),
		Setting('Gaze offset max (degrees)',   float,     1.5,  helpText='In degrees'),
		Setting('Fixation period (seconds)',   float,     0.3,  helpText='In seconds'),
		Setting('Render at gaze',              bool,      False),
		Setting('Retries',                     int,       3),
		Setting('Show gaze',                   bool,      False),

	), ConfigGroup('Display settings',
		Setting('Monitor distance',   int,    57, helpText='In cm'),
		Setting('Fixation size',      int,    20, helpText='In arcmin'),
		Setting('Show fixation aid',  bool,   False),
		Setting('Show annuli',        bool,   False)

	), ConfigGroup('Stimuli settings',
		Setting('Eccentricities',               typing.List[int],        [4, 8, 12], helpText='In degrees'),
		Setting('Orientations',                 typing.List[float],      [45, 67.5, 90, 112.5, 135], helpText='In degrees'),
		Setting('Stimulus position angles',     typing.List[int],        [45, 135, 225, 315], helpText='In degrees'),
		Setting('Trials per stimulus config',   int,                     24),
		Setting('Stimulus duration',            int,                     200, helpText='In ms'),
		Setting('Time between stimuli',         int,                     1000, helpText='In ms'),
		Setting('Contrast overrides',           typing.List[float],      []),
		Setting('Stimulus size',                int,                     4, helpText='In degrees of visual angle'),

	), ConfigGroup('Input settings',
		Setting('First stimulus key',           str,     'num_4'),
		Setting('Second stimulus key',          str,     'num_6'),
		Setting('First stimulus key label',     str,     '1'),
		Setting('Second stimulus key label',    str,     '2'),
		Setting('Wait for ready key',           bool,    True),
	),
]

def getSettings(filename = f'{PROGRAM_NAME}-settings.ini'):
	print(filename)
	if QApplication.instance() is None:
		_ = QApplication(['tmpApplication'])
	return ConfigHelper(SETTINGS_GROUP, filename).getSettings()