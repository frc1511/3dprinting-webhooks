import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import json
import datetime
import re
from cachetools import cached, TTLCache

message = "New print request: \n Part: %s \n Material: %s \n Quality: %s \n Other notes: %s"

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets.readonly']

with open('config.json', 'r') as json_file:
    data = json.load(json_file)


@cached(cache=TTLCache(maxsize=1, ttl=86400))
def get_folder(service):
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
            pass
        parent = file.get('parents')
        if parent:
            tree = []
            while True:
                folder = service.files().get(fileId=parent[0], fields='name, id, parents').execute()
                parent = folder.get('parents')
                if str(datetime.date.today().year) in str(folder['name']):
                    current_year = [folder['id'], idx]  # [id of parent folder, id of appropriate 'processed' folder]
                if parent is None:
                    break
                tree.append({'id': parent[0], 'name': folder.get('name')})
        root.append(tree)

    current_unprocessed_parent = service.files().get(fileId=folder_ids[current_year[1]], fields='name, id, parents').execute().get('parents')[0]
    return current_unprocessed_parent, folder_ids[current_year[1]]


@cached(cache=TTLCache(maxsize=1, ttl=86400))
def get_current_parts_log(service):
    page_token = None
    while True:
        files = service.files().list(q="name='%s PARTS AND ASSEMBLY LOG'" % str(datetime.date.today().year),
                                     spaces='drive',
                                     fields='nextPageToken, files(id, name)',
                                     pageToken=page_token).execute()

        page_token = files.get('nextPageToken', None)
        if page_token is None:
            break
    return files.get('files', [])[0].get('id')


def main():
    # folder struct: <year>/02 Build Season/<year> PARTS AND ASSEMBLY LOG
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('svc_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    service_sheets = build('sheets', 'v4', credentials=creds)

    current_unprocessed_parent, processed_folder = get_folder(service)
    partslog_id = get_current_parts_log(service)

    page_token = None
    unprocessed_files = []
    error_files = []
    regex = r"(S?P\d+)([ :\"'.\-\(\)a-zA-z0-9]+)\.(ipt|stl)"
    while True:
        unprocessed = service.files().list(q="'%s' in parents" % current_unprocessed_parent,
                                           spaces='drive',
                                           fields='nextPageToken, files(id, name, mimeType)',
                                           pageToken=page_token).execute()
        for file in unprocessed.get('files', []):
            result = re.match(regex, file.get('name'))
            if result is None:
                if str(file.get('mimeType')) == 'application/vnd.google-apps.folder':
                    continue
                error_files.append([file.get('name'), str(file.get('id'))])
                continue
            elif result.group(3) not in ['ipt', 'stl']:
                error_files.append([file.get('name'), str(file.get('id'))])
            else:
                unprocessed_files.append([result.group(1), str(file.get('id'))])
        page_token = unprocessed.get('nextPageToken', None)
        if page_token is None:
            break
    sheet_ranges = ['Parts List!A13:A', 'Parts List!H13:J']
    sheet = service_sheets.spreadsheets()
    partsnums = sheet.values().get(spreadsheetId=partslog_id,
                                   range=sheet_ranges[0]).execute().get('values', [])
    partsfoo = sheet.values().get(spreadsheetId=partslog_id,
                                  range=sheet_ranges[1]).execute().get('values', [])

    for unp in unprocessed_files:
        file = service.files().get(fileId=unp[1],
                                   fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        name = [unp[0]]
        idx = partsnums.index(name)
        params = partsfoo[idx]
        requests.post(data['url'], data={'text': message % (unp[0].strip('\n'), params[0].strip('\n'), params[1].strip('\n'), params[2].strip('\n'))})
        file = service.files().update(fileId=unp[1],
                                      addParents=processed_folder,
                                      removeParents=previous_parents,
                                      fields='id, parents').execute()
        print('moving file %s' % unp[0])


if __name__ == '__main__':
    main()
