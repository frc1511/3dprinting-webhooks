import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import json

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
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
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

    for id in folder_ids:
        file = service.files().get(fileId=id, fields='id, name, parents').execute()
        parent = file.get('parents')
        if parent:
            tree = []
            while True:             
                folder = service.files().get(fileId=parent[0], fields='name, id, parents').execute()
                parent = folder.get('parents')
                if parent is None:
                    break
                tree.append({'id': parent[0], 'name': folder.get('name')})
        root.append(tree)
        
            
    print(root)





if __name__ == '__main__':
    main()
