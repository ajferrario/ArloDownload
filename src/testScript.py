from arloConnector import arloConnector
from driveBackend import driveBackend
from localBackend import localBackend
import configparser

config = configparser.ConfigParser()
config.read('C:/ArloDownload/arlo.conf')
rootdir = config['Default']['rootdir']
arlo = arloConnector(config, localBackend(rootdir))
arlo.readLibrary()
arlo.backupLibrary(driveBackend(config, rootdir))
