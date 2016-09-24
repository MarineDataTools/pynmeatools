from setuptools import setup
import os

ROOT_DIR='pynmeatools'
with open(os.path.join(ROOT_DIR, 'VERSION')) as version_file:
    version = version_file.read().strip()

setup(name='pynmeatools',
      version=version,
      description='A setup of python tools to read, parse, and save NMEA 0183 daa',
      url='https://github.com/MarineDataTools/pynmeatools/',
      author='Peter Holtermann',
      author_email='peter.holtermann@systemausfall.org',
      license='GPLv03',
      packages=['pynmeatools'],
      scripts = [],
      entry_points={ 'console_scripts': ['pynmea0183logger=pynmeatools.nmea0183logger:main',] },
      package_data = {'':['VERSION']},
      zip_safe=False)
