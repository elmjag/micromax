"""Settings for Spock session"""

#
# Please do not delete the next lines has they are used to check the version
# number for possible upgrades
# spock_creation_version = 3.4.0
# door_name = tango://tango-cs:10000/Micromax/Door/01
#

import itango

import sardana.spock.genutils
from sardana.spock.config import Spock

config = get_config()
config.Spock.macro_server_name = 'tango://tango-cs:10000/MacroServer/micromax/1'
config.Spock.door_name = 'tango://tango-cs:10000/Micromax/Door/01'

load_subconfig('ipython_config.py', profile='default')
sardana.spock.load_config(config)

# Put any additional environment here and/or overwrite default sardana config
config.IPKernelApp.pylab = 'inline'

