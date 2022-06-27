#
# (c) 2022 Copyright, Real-Time Innovations.  All rights reserved.
# No duplications, whole or partial, manual or electronic, may be made
# without express written permission.  Any such copies, or revisions thereof,
# must display this notice unaltered.
# This code contains trade secrets of Real-Time Innovations, Inc.
#
import os, sys
import json
from pathlib import Path

# class for managing settings / config for RTI TypeRepo GUI
class CfgSettings():

    def __init__(self, cfgFilePath):
        self.my_cwd = cfgFilePath
        self.cfgFile = Path(self.my_cwd, 'trg-config.json')
        # open and read the config file - if it exists
        if self.cfgFile.is_file():
            with open(self.cfgFile, 'r') as cfgFileContents:
                # FIXME: this needs a try/except to watch for 0-length files and other errors
                self.cfgVal = json.loads(cfgFileContents.read())
                cfgFileContents.close()
                self.cleanUpDbFileList()
        else:
            # config file does not exist, create one with default values
            self.cfgVal = {
                'dbLoadPath': '{}'.format(self.my_cwd),         # path to find .db files for loading
                'exportPath': '{}'.format(self.my_cwd),         # path to export data type files
                'scanPath': '{}'.format(self.my_cwd),           # path to scan for ROS data types
                'scanDbStorePath': '{}'.format(self.my_cwd),    # path to store the resulting scan database file
                'lastLoadedDbFiles': [],                        # list of databases to auto-load (if selected)
                'reloadLastDbOnStartup': True                   # automatically load database on startup
            }
            self.updateFile()

    
    def updateFile(self):
        with open(self.cfgFile, 'w') as cfgFileContents:
            self.cleanUpDbFileList()
            cfgFileContents.write(json.dumps(self.cfgVal, indent=2))
            cfgFileContents.close()

    # this is to de-duplicate and remove blanks from the dbFileList
    def cleanUpDbFileList(self):
        dbFileSet = set(self.cfgVal['lastLoadedDbFiles'])
        dbFilesToRemove = set()
        for dbFile in dbFileSet:
            if len(dbFile) < 2:
                dbFilesToRemove.add(dbFile)
        for removeMe in dbFilesToRemove:
            dbFileSet.remove(removeMe)
        self.cfgVal['lastLoadedDbFiles'] = list(dbFileSet)

