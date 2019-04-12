from . import log
from . import app

settings = app.getSettings()

if not settings is None:
	log.startLog(settings['sessionID'])
	app.run(settings)
