import os
ROOT_DIR='.'

    


import pkg_resources
__version__ = pkg_resources.resource_string(__name__, 'VERSION')


import pynmeatools_nmea0183logger as nmea0183logger
from pynmeatools_nmea0183logger import parse
