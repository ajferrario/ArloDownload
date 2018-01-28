#!/usr/bin/python3

import os
import shutil
# Local imports
from abstractBackend import abstractBackend


class localBackend(abstractBackend):
    def __init__(self, rootdir):
        super().__init__()
        self.rootdir = rootdir

    def backup(self, file):
        output_path, filename = os.path.split(file['output_path'])
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        with open(output_path, 'wb') as out_file:
            shutil.copyfileobj(file['local_path'], out_file)