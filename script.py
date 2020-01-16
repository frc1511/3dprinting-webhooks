import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import json
import datetime
import re

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

with open('config.json', 'r') as json_file:
    data = json.load(json_file)



def main():
    # requests.post(data['url'], data={'text':'hello world'})

    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('drive', 'v3', credentials=creds)

    folder_ids = []
    root = []
    page_token = None
    while True:
        folders = service.files().list(q="mimeType='application/vnd.google-apps.folder' and name='Processed'",
                                        spaces='drive',
                                        fields='nextPageToken, files(id, name)',
                                        pageToken=page_token).execute()
        for folder in folders.get('files', []):
            
            folder_ids.append(folder.get('id'))
        page_token = folders.get('nextPageToken', None)
        if page_token is None: 
            break

    current_year = None
    for idx, i in enumerate(folder_ids):
        file = service.files().get(fileId=i, fields='id, name, parents').execute()
        if str(datetime.date.today().year) in str(file['name']):
            parent = file.get('parents')
        if parent:
            tree = []
            while True:             
                folder = service.files().get(fileId=parent[0], fields='name, id, parents').execute()
                parent = folder.get('parents')
                if str(datetime.date.today().year) in str(folder['name']):
                    current_year = [folder['id'], idx] # [id of parent folder, id of appropriate 'processed' folder]
                if parent is None:
                    break
                tree.append({'id': parent[0], 'name': folder.get('name')})
        root.append(tree)
        
    current_unprocessed_parent = service.files().get(fileId=folder_ids[current_year[1]], fields='name, id, parents').execute().get('parents')[0]
    

    page_token = None
    unprocessed_files = {}
    error_files = {}
    regex = r"(S?P\d+)([ :\"'.\-\(\)a-zA-z0-9]+)\.(ipt|stl)"
    while True:
        unprocessed = service.files().list(q="'%s' in parents" %current_unprocessed_parent,
                                            spaces='drive', 
                                            fields='nextPageToken, files(id, name)',
                                            pageToken=page_token).execute()
        for file in unprocessed.get('files', []):
            result = re.match(regex, file.get('name'))
            if result.group(3) not in ['ipt, stl']:
                error_files["%s" %file.get('name')] = str(file.get('id'))
            else:
                unprocessed_files["%s" % result.group(1)] = str(file.get('id'))
        page_token = folders.get('nextPageToken', None)
        if page_token is None: 
            break

    

if __name__ == '__main__':
    main()
