# 3dprinting-webhooks

Sends message in channel when a new file is created in Google Drive and move the file to another folder
Requires the Google Drive and Sheets API to be enabled with write permissions on Drive

``config.json`` contains the Webhook URL to use and is intended for Slack compatible webhooks (works with Discord)

``svc_credentials.json`` must be provided from the Google Developers Console for a service account

``token.pickle`` is created automatically on first run