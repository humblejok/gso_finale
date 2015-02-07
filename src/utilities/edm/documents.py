'''
Created on Feb 6, 2015

@author: sdejonckheere
'''
from finale.settings import EDM_PATH
import os
from shutil import copyfile
import uuid
from seq_common.db import dbutils

def get_documents_manager():
    return document_manager

class DocumentsManager(object):

    def get_unique_id(self):
        with self.lock:
            results = dbutils.query_to_dicts("SELECT nextval('edm_sequence')")
            for result in results:
                return str(result['nextval'])

    def create_get_project(self, project_name):
        fullpath = os.path.join(EDM_PATH, project_name)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)
        return fullpath

    def append_document(self, project_name, document_path, document_name, attributes={}):
        fullpath = self.create_get_project(project_name)
        #TODO Handle error
        unique_id = self.get_unique_id()
        copyfile(document_path, os.path.join(fullpath, unique_id))
        attributes['_id'] = unique_id
        
document_manager = DocumentsManager()