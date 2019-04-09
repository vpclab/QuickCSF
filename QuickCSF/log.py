import logging
import pathlib
from datetime import datetime


def startLog(sessionID='NONE'):
	pathlib.Path('data').mkdir(parents=True, exist_ok=True)

	logger = logging.getLogger('QuickCSF')
	logger.setLevel(logging.DEBUG)
	
	fh = logging.FileHandler(pathlib.Path(f'data/QuickCSF {sessionID} ' + datetime.today().strftime('%Y-%m-%d %H-%M-%S') + '.log').resolve())
	fh.setLevel(logging.DEBUG)
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)8s: %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)
	logger.addHandler(fh)
	logger.addHandler(ch)
