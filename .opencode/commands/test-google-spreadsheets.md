---
description: Test Google Sheets authentication, spreadsheet access, target sheet, configured range, and records
agent: google-sheets-logger
subtask: true
---

Run this exact command from the project root and return the JSON output:

```bash
npm run test-google-spreadsheets
```

Validation goals:
- Load `config/google/sheets.config.json` or `GOOGLE_SHEETS_CONFIG`.
- Resolve the configured `credentialsFile` relative to the project root.
- Authenticate with the Google Sheets API using the service account.
- Verify the configured `spreadsheetId` exists and is accessible.
- Verify the configured `sheetName` exists.
- Read the configured range and report whether it has records.
- Validate the configured header layout when records are present.

Never print or expose private keys or raw service account secrets.
