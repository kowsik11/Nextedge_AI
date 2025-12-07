from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings


class GoogleSheetsService:
    """Service for Google Sheets API operations"""

    def __init__(self, access_token: str, refresh_token: str):
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_sheets_client_id,
            client_secret=settings.google_sheets_client_secret,
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    def list_spreadsheets(self) -> List[Dict[str, str]]:
        """List user's Google Sheets"""
        try:
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
                pageSize=20,
                fields="nextPageToken, files(id, name)"
            ).execute()
            items = results.get('files', [])
            return [{"id": item['id'], "name": item['name']} for item in items]
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def create_spreadsheet(self, title: str = "NextEdge Emails") -> Dict[str, str]:
        """Create a new spreadsheet and return its id and url."""
        try:
            body = {"properties": {"title": title}}
            result = self.service.spreadsheets().create(body=body, fields="spreadsheetId,spreadsheetUrl,properties/title").execute()
            return {
                "id": result.get("spreadsheetId"),
                "url": result.get("spreadsheetUrl"),
                "name": result.get("properties", {}).get("title") or title,
            }
        except HttpError as error:
            print(f"An error occurred creating spreadsheet: {error}")
            raise

    def initialize_sheet_headers(self, spreadsheet_id: str, sheet_name: str = "Sheet1"):
        """Create headers in the sheet if not exists (writes to the given tab)."""
        headers = [
            "Timestamp",
            "Email ID",
            "From",
            "From Name",
            "Subject",
            "Classification Type",
            "Body Preview",
            "Full Body",
            "AI Confidence",
            "Urgency",
            "Sentiment",
            "Intent",
            "Entities",
            "AI Reasoning",
            "Has Attachments",
            "Labels",
            "Thread ID",
            "Synced At",
            "Status",
        ]

        try:
            # Check if sheet exists, if not create it
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_exists = any(s['properties']['title'] == sheet_name for s in sheets)

            if not sheet_exists:
                # Add new sheet
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()

            # Check if headers exist (read first row)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:S1"
            ).execute()
            
            existing_headers = result.get('values', [])

            if not existing_headers:
                # Append headers
                self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1:S1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [headers]},
                ).execute()

                # Format headers (Bold)
                # Need sheetId for formatting
                sheet_id = (
                    next(
                        s["properties"]["sheetId"]
                        for s in sheets
                        if s["properties"]["title"] == sheet_name
                    )
                    if sheet_exists
                    else self.service.spreadsheets()
                    .get(spreadsheetId=spreadsheet_id)
                    .execute()["sheets"][-1]["properties"]["sheetId"]
                )

                requests = [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                            },
                            "cell": {
                                "userEnteredFormat": {"textFormat": {"bold": True}}
                            },
                            "fields": "userEnteredFormat.textFormat.bold",
                        }
                    }
                ]
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": requests}
                ).execute()

        except HttpError as error:
            print(f"An error occurred initializing headers: {error}")
            raise

    def append_email_row(
        self, spreadsheet_id: str, email_data: Dict[str, Any], sheet_name: str = "Sheet1"
    ) -> int:
        """Append email data as a new row"""

        # Ensure headers exist
        self.initialize_sheet_headers(spreadsheet_id, sheet_name)

        # Format data into row
        row = [
            email_data.get("received_at"),
            email_data.get("email_id"),
            email_data.get("from_email"),
            email_data.get("from_name"),
            email_data.get("subject"),
            email_data.get("classification"),
            email_data.get("body_preview"),
            email_data.get("body_full"),
            email_data.get("confidence_score"),
            email_data.get("urgency"),
            email_data.get("sentiment"),
            email_data.get("intent"),
            email_data.get("entities"),
            email_data.get("reasoning"),
            email_data.get("has_attachments"),
            email_data.get("labels"),
            email_data.get("thread_id"),
            email_data.get("synced_at"),
            email_data.get("status"),
        ]
        
        try:
            # Append to sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A:S',
                valueInputOption='USER_ENTERED',
                body={'values': [row]}
            ).execute()
            
            # Return row number that was written
            # updatedRange looks like "Emails!A2:S2"
            updated_range = result.get('updates', {}).get('updatedRange', '')
            if updated_range:
                # Extract end row number
                import re
                match = re.search(r'\d+$', updated_range)
                if match:
                    return int(match.group())
            return 0
            
        except HttpError as error:
            print(f"An error occurred appending row: {error}")
            raise

    def get_spreadsheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Get spreadsheet metadata"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return {
                "name": result.get('properties', {}).get('title'),
                "url": result.get('spreadsheetUrl'),
                "sheets": [sheet['properties']['title'] for sheet in result.get('sheets', [])]
            }
        except HttpError as error:
            print(f"An error occurred getting info: {error}")
            raise
