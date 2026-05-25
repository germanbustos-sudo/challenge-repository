# Google Sheets Integration

Version: `0.8.7`

The challenge orchestrator can append final challenge results to a Google Spreadsheet after `final-evaluation.json` is generated.

## Command

```text
/add-google-spreadsheets EMPLOYEE_ID ATTEMPT SCORE
```

Argument mapping:

| Argument | Report field | Google Sheets column |
|---|---|---|
| `EMPLOYEE_ID` | `employee_id` | Column 1: Employee ID |
| `ATTEMPT` | `attempt_number` | Column 4: Attempt |
| `SCORE` | `numeric_score` | Column 7: Score |

The target sheet layout is:

```text
Employee ID | Name | Challenge | Attempt | Report URL | Status | Score
```

Columns 2, 3, 5, and 6 are intentionally left empty by this integration.

## Automatic publish from `/challenge-reviewer-global`

After the unified final report renderer creates:

```text
reports/final-evaluation.json
```

it calls:

```bash
python scripts/publish_review_to_google_sheets.py "<review-session>"
```

That helper reads:

```text
employee_id     -> final-evaluation.json.employee_id
attempt_number  -> final-evaluation.json.attempt_number
numeric_score   -> final-evaluation.json.numeric_score
```

and internally calls:

```bash
npm run add-google-spreadsheets -- EMPLOYEE_ID ATTEMPT SCORE
```

A status artifact is always written to:

```text
review-sessions/<session>/integrations/google-sheets-publish-status.json
```

## Configuration

Copy the example config:

```bash
cp config/google/sheets.config.example.json config/google/sheets.config.json
```

Place your Google service account JSON at:

```text
config/google/service-account.json
```

Then edit:

```text
config/google/sheets.config.json
```

with your spreadsheet ID, sheet name, and credential file path.

## Validate locally

```bash
npm install
npm run google-sheets:validate-config
npm run add-google-spreadsheets -- EMP001 1 86
```

## Security

Never commit:

```text
config/google/service-account.json
config/google/sheets.config.json
```

Both files are ignored by `.gitignore` and `.dockerignore`.


## Connectivity Test

Use this command before running a full challenge review in a new machine or container:

```text
/test-google-spreadsheets
```

Equivalent shell command:

```bash
npm run test-google-spreadsheets
```

The test verifies:

- Google Sheets config file exists.
- The configured `credentialsFile` exists and can authenticate.
- The configured `spreadsheetId` is reachable.
- The configured `sheetName` exists.
- The configured range can be read.
- The sheet has records or is currently empty.
- Headers match the configured `columns` layout when records are present.

The command must never print private keys or raw service account secrets.
