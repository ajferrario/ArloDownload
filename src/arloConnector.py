#!/usr/bin/python3

import requests
import datetime
import os
import json
import platform
import random

# Local imports
from abstractBackend import abstractBackend
from abstractConnector import abstractConnector

class arloConnector(abstractConnector):
    def __init__(self, config):
        self.scratch_dir = os.path.join(config['Default']['rootdir'], 'temp')
        if not os.path.exists(self.scratch_dir):
            os.makedirs(self.scratch_dir)
        self.config = config
        # Define camera common names by serial number.
        self.cameras = {}
        self.cameraLibs = {}
        self.concatgap = int(config['ConcatGap']['concatgap'])
        for cameraNum in range(1, 10):
            sectionName = "Camera.{}".format(cameraNum)
            if sectionName in config:
                self.cameras[config[sectionName]['serial']] = config[sectionName]['name']

        # No customization of the following should be needed.
        self.loginUrl = "https://arlo.netgear.com/hmsweb/login"
        self.deviceUrl = "https://arlo.netgear.com/hmsweb/users/devices"
        self.metadataUrl = "https://arlo.netgear.com/hmsweb/users/library/metadata"
        self.libraryUrl = "https://arlo.netgear.com/hmsweb/users/library"
        self.headers = {'Content-type': 'application/json', 'Accept': 'text/plain, application/json'}
        self.session = requests.Session()

        # Login and read library
        self.login()

    # Log into arlo servers
    def login(self):
        loginData = {"email": self.config['arlo.netgear.com']['userid'],
                     "password": self.config['arlo.netgear.com']['password']}
        response = self.session.post(self.loginUrl, data=json.dumps(loginData), headers=self.headers)
        jsonResponseData = response.json()['data']
        print("Arlo login!")
        self.token = jsonResponseData['token']
        self.deviceID = jsonResponseData['serialNumber']
        self.userID = jsonResponseData['userId']
        self.headers['Authorization'] = self.token

    # Create list of all videos in the past 7 days
    def readLibrary(self):
        today = datetime.date.today()
        now = today.strftime("%Y%m%d")
        # A 7-day window ought to be enough to catch everything!
        then = (today - datetime.timedelta(days=7)).strftime("%Y%m%d")
        params = {"dateFrom": then, "dateTo": now}
        response = self.session.post(self.libraryUrl, data=json.dumps(params), headers=self.headers)
        self.library = response.json()['data']
        # Separate the videos in their different cameras (oldest first)
        self.cameraLibs = {}
        for item in self.library:
            if item['deviceId'] in self.cameras:
                if item['deviceId'] not in self.cameraLibs:
                    self.cameraLibs[item['deviceId']] = []
                self.cameraLibs[item['deviceId']].append(item)
        return self.cameraLibs

    # Backs up all clips in the past 7 days. Intended to be the basic way to interact with this class
    def backupLibrary(self, backend):
        # Make sure we've read in the library
        if self.cameraLibs == {}:
            self.readLibrary()
        if not isinstance(backend, abstractBackend):
            print('Backend provided is not a legitimate backend.')
            return
        for camera in self.cameraLibs:
            while len(self.cameraLibs[camera]) > 0:
                backend.backup(self.getNextClip(camera))

    # Pass back a clip for backup
    def getNextClip(self, camera):
        clips = self.cameraLibs[camera]
        clip = {
            'meta': None,
            'local_path': None,
            'output_path': None
        }
        # If we need to concat and we're on Linux (Concat is Linux dependent)
        if len(clips) > 1 and self.needToConcat(clips[0], clips[1]) and platform.system() == 'Linux':
            clip_group = [clips.pop(0), clips.pop(0)]
            while len(clips) > 0 and self.needToConcat(clip_group[-1], clips[0]):
                clip_group.append(clips.pop(0))
            clip = self.concatenate(clip_group)
        # If there is a clip to pull but don't need to concat
        elif len(clips) > 0:
            output_path = os.path.join(self.getOutputDir(clips[0]), self.getOutputFile(clips[0]))
            local_path = self.download(self.getOutputFile(clips[0]), clips[0]['presignedContentUrl'])
            clip = {
                'meta': clips.pop(0),
                'local_path': local_path,
                'output_path': output_path
            }
        return clip

    # download a file to temp space
    def download(self, name, url):
        download_handle = self.session.get(url, stream=True)
        temp_path = os.path.join(self.scratch_dir, name)
        temp_file = open(temp_path, 'wb')
        for chunk in download_handle.iter_content(chunk_size=1024):
            temp_file.write(chunk)
        temp_file.close()
        return temp_path

    # Identify whether these videos need to be concatenated
    def needToConcat(self, older, newer):
        # Whether the difference between the start of the second clip and the end of the first is within the concat gap
        return self.getTimestampInSecs(newer) - (self.getTimestampInSecs(older) + int(older['mediaDurationSecond'])) <= self.concatgap

    def concatenate(self, videos):
        print("Concatenating videos:")
        flist = []
        # Get the videos to concatenate locally
        for item in reversed(videos):
            url = item['presignedContentUrl']
            filename = item['name'] + ".mp4"
            self.download(filename, url)
            flist.append(filename)

        # How long does the concatenated video cover?
        # Remember, videos are in reverse order (most recent first)
        totalSecs = self.getTimestampInSecs(videos[0]) - self.getTimestampInSecs(videos[-1]) + int(
            videos[0]['mediaDurationSecond'])
        time = str(datetime.datetime.fromtimestamp(self.getTimestampInSecs(videos[-1])).strftime('%H:%M:%S'))
        try:
            # First, convert the MP4 into something that can be concatenated
            for mp4 in (flist):
                os.system(
                    "cd " + self.scratch_dir + "; ffmpeg -i " + mp4 + " -c copy -bsf:v h264_mp4toannexb -f mpegts " + mp4 + ".ts")
            # Concatenate using ffmpeg...
            os.system("cd " + self.scratch_dir + "; ffmpeg -i 'concat:" + '.ts|'.join(
                flist) + ".ts' -c copy -bsf:a aac_adtstoasc concat.mp4")
            return {
                # build our own metadata for this file
                'meta': {
                    {
                        'ownerId': 'K9C7C-300-8648016',
                        'uniqueId': 'K9C7C-300-8648016_55W17779AA660',
                        'deviceId': '55W17779AA660',
                        'createdDate': '',
                        'currentState': 'new',
                        'name': 'concat_' + str(random.randint(1000000000000,9999999999999)),
                        'contentType': 'video/mp4',
                        'reason': 'motionRecord',
                        'createdBy': '55W17779AA660',
                        'lastModified': 0,
                        'localCreatedDate': 0,
                        'presignedContentUrl': '',
                        'presignedThumbnailUrl': '',
                        'utcCreatedDate': 0,
                        'timeZone': 'America/Los_Angeles',
                        'mediaDuration': '',
                        'mediaDurationSecond': totalSecs,
                        'donated': False
                    }
                },
                'local_path': self.scratch_dir + "/concat.mp4"
            }
        except:
            print("Something went wrong during concatenation...")

    # Return the timestamp, in seconds, of an Arlo video item
    def getTimestampInSecs(self, item):
        return int(int(item['name']) / 1000)

    # Return the output directory name corresponding to an Arlo video item
    def getOutputDir(self, item):
        camera = str(self.cameras[item['deviceId']])
        year = str(datetime.datetime.fromtimestamp(self.getTimestampInSecs(item)).strftime('%Y'))
        month = str(datetime.datetime.fromtimestamp(self.getTimestampInSecs(item)).strftime('%m'))
        date = str(datetime.datetime.fromtimestamp(self.getTimestampInSecs(item)).strftime('%d'))
        return os.path.join(year, month, date, camera)

    # Return the output file name corresponding to an Arlo video item
    def getOutputFile(self, item):
        time = str(datetime.datetime.fromtimestamp(self.getTimestampInSecs(item)).strftime('%H%M%S'))
        secs = item['mediaDurationSecond']
        return time + "+" + str(secs) + "s.mp4"
