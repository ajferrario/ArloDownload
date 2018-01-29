#!/usr/bin/python3

import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import ntpath
import time
import sys
# Local imports
from abstractBackend import abstractBackend


class driveBackend(abstractBackend):
    def __init__(self, config):
        super().__init__()
        gauth = GoogleAuth(settings_file=os.path.join(config['drive.google.com']['drive_config_dir'], config['drive.google.com']['auth_config_filename']))
        self.drive_connection = GoogleDrive(gauth)

    def backup(self, clip):
        parent_id = self.build_folder_structure(clip['output_path'])
        filename = ntpath.basename(clip['local_path'])
        file = self.drive_connection.CreateFile({
            'title': filename,
            'parents': [{'id': parent_id}]
        })
        file.SetContentFile(clip['local_path'])
        file.Upload()
        file = None  # this is to force python to close the file handle opened by pydrive. they have a bug.
        os.remove(clip['local_path'])


    def build_folder_structure(self, path_and_file):
        folders = self.split_path(path_and_file)
        parent_id, remaining_folders = self.find_deepest_folder(folders)
        # if remaining_folders is not
        for folder in remaining_folders:
            parent_id = self.create_folder(parent_id, folder)
        return parent_id

    def find_deepest_folder(self, folders, parent_id='root'):
        file_list = []
        if len(folders) > 0:
            file_list = self.drive_connection.ListFile(
                {'q': "'{0}' in parents and trashed=false and title='{1}'".format(parent_id, folders[0])}).GetList()
        if len(file_list) > 0:
            return self.find_deepest_folder(folders[1:], file_list[0]['id'])
        else:
            return parent_id, folders


    @staticmethod
    def split_path(path_and_file):
        path, file = os.path.split(path_and_file)
        folders = []
        while 1:
            path, folder = os.path.split(path)

            if folder != '':
                folders.append(folder)
            else:
                if path != '':
                    folders.append(path)

                break
        folders.reverse()
        return folders

    def create_folder(self, parent_id, name):
        folder = self.drive_connection.CreateFile({
            'title': name,
            'parents':  [{'id': parent_id}],
            'mimeType': 'application/vnd.google-apps.folder'})
        folder.Upload()
        return folder['id']
