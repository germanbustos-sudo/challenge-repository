#!/usr/bin/env node
import { fileURLToPath } from "node:url";
import path from "node:path";
import { loadSheetsConfig } from "./config.js";

export function parseArgs(argv) {
  if (argv.includes("--help") || argv.includes("-h")) {
    return { help: true };
  }
  if (argv.includes("--validate-config")) {
    return { validateConfig: true };
  }
  if (argv.length !== 3) {
    throw new Error("Usage: add-google-spreadsheets <EmployeeID> <Attempt> <Score>");
  }

  const [employeeId, attemptRaw, scoreRaw] = argv;
  const attempt = Number(attemptRaw);
  const score = Number(scoreRaw);

  if (!employeeId || String(employeeId).trim() === "") {
    throw new Error("Employee ID is required.");
  }
  if (!Number.isFinite(attempt)) {
    throw new Error("Attempt must be a number.");
  }
  if (!Number.isFinite(score)) {
    throw new Error("Score must be a number.");
  }

  return { employeeId, attempt, score };
}

export function buildSpreadsheetRow({ employeeId, attempt, score }) {
  return [
    employeeId, // Column 1: Employee ID
    "",         // Column 2: Name
    "",         // Column 3: Challenge
    attempt,    // Column 4: Attempt
    "",         // Column 5: Report URL
    "",         // Column 6: Status
    score       // Column 7: Score
  ];
}

async function appendRow(args) {
  const config = loadSheetsConfig();

  const { google } = await import("googleapis");

  const auth = new google.auth.GoogleAuth({
    keyFile: config.credentialsFile,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"]
  });

  const sheets = google.sheets({ version: "v4", auth });
  const targetRange = `${config.sheetName}!${config.range}`;

  const response = await sheets.spreadsheets.values.append({
    spreadsheetId: config.spreadsheetId,
    range: targetRange,
    valueInputOption: config.valueInputOption,
    insertDataOption: "INSERT_ROWS",
    requestBody: {
      values: [buildSpreadsheetRow(args)]
    }
  });

  return response.data;
}

async function main() {
  try {
    const args = parseArgs(process.argv.slice(2));

    if (args.help) {
      console.log("Usage: add-google-spreadsheets <EmployeeID> <Attempt> <Score>");
      console.log("Example: npm run add-google-spreadsheets -- EMP001 1 70.5");
      process.exit(0);
    }

    if (args.validateConfig) {
      const config = loadSheetsConfig();
      console.log(JSON.stringify({
        ok: true,
        spreadsheetId: config.spreadsheetId,
        sheetName: config.sheetName,
        range: config.range,
        columns: config.columns,
        writeMapping: config.writeMapping
      }, null, 2));
      process.exit(0);
    }

    const result = await appendRow(args);
    console.log(JSON.stringify({
      ok: true,
      updatedRange: result.updates?.updatedRange || null,
      updatedRows: result.updates?.updatedRows || null,
      updatedCells: result.updates?.updatedCells || null
    }, null, 2));
  } catch (error) {
    console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
    process.exit(1);
  }
}

const currentFilePath = fileURLToPath(import.meta.url);
const executedFilePath = process.argv[1] ? path.resolve(process.argv[1]) : "";

if (currentFilePath === executedFilePath) {
  main();
}
