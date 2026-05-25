---
description: Append Employee ID, attempt, and score into Google Sheets columns 1, 4, and 7
agent: google-sheets-logger
subtask: true
---

Run this exact command from the project root and return the output:

```bash
npm run add-google-spreadsheets -- $1 $2 $3
```

Validate that exactly three arguments were provided:
- `$1`: Employee ID, written to column 1: Employee ID
- `$2`: Attempt, written to column 4: Attempt
- `$3`: Score, written to column 7: Score

The spreadsheet row must preserve the configured table layout:

```txt
Employee ID | Name | Challenge | Attempt | Report URL | Status | Score
```

Never print service account secrets.
