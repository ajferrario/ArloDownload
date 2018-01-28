#!/usr/bin/python3

import dropbox
import os
# Local imports
from abstractBackend import abstractBackend


class dropboxBackend(abstractBackend):
    def __init__(self, config):
        super().__init__()
        self.backend = dropbox.Dropbox(config['dropbox.com']['token'])
        print("Dropbox login!")

    def backup(self, file):
        print("Dropboxing " + file['local_path'])
        self.backend.files_upload(file['local_path'], "/" + 'NEEDSWORK.mp4')
