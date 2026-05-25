#!/usr/bin/env node
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";
import { loadSheetsConfig } from "./config.js";

function usage() {
  return `Usage: test-google-spreadsheets\n\nValidates Google Sheets configuration, service account authentication, spreadsheet access, target sheet existence, configured range readability, and whether the sheet has records.\n\nConfiguration source: GOOGLE_SHEETS_CONFIG or ./config/google/sheets.config.json`;
}

function readCredentialSummary(credentialsFile) {
  try {
    const raw = JSON.parse(fs.readFileSync(credentialsFile, "utf8"));
    return {
      credentialFile: path.basename(credentialsFile),
      serviceAccountEmail: raw.client_email || null,
      projectId: raw.project_id || null
    };
  } catch (_error) {
    return {
      credentialFile: path.basename(credentialsFile),
      serviceAccountEmail: null,
      projectId: null
    };
  }
}

function countNonEmptyRows(rows) {
  return rows.filter((row) => Array.isArray(row) && row.some((cell) => String(cell ?? "").trim() !== "")).length;
}

function compareHeaders(actualHeader, expectedColumns) {
  if (!Array.isArray(actualHeader) || actualHeader.length === 0) {
    return { headerPresent: false, headerMatchesConfiguredColumns: false, missingColumns: expectedColumns };
  }

  const normalizedActual = actualHeader.map((cell) => String(cell ?? "").trim().toLowerCase());
  const normalizedExpected = expectedColumns.map((cell) => String(cell ?? "").trim().toLowerCase());
  const missingColumns = [];

  normalizedExpected.forEach((expected, index) => {
    if (normalizedActual[index] !== expected) {
      missingColumns.push(expectedColumns[index]);
    }
  });

  return {
    headerPresent: true,
    headerMatchesConfiguredColumns: missingColumns.length === 0,
    missingColumns
  };
}

export async function testGoogleSheetsConnection() {
  const config = loadSheetsConfig();
  const { google } = await import("googleapis");

  const auth = new google.auth.GoogleAuth({
    keyFile: config.credentialsFile,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"]
  });

  const sheets = google.sheets({ version: "v4", auth });

  const spreadsheet = await sheets.spreadsheets.get({
    spreadsheetId: config.spreadsheetId,
    includeGridData: false
  });

  const spreadsheetTitle = spreadsheet.data.properties?.title || null;
  const sheetNames = (spreadsheet.data.sheets || [])
    .map((sheet) => sheet.properties?.title)
    .filter(Boolean);

  if (!sheetNames.includes(config.sheetName)) {
    throw new Error(`Target sheet not found: ${config.sheetName}. Available sheets: ${sheetNames.join(", ") || "none"}`);
  }

  const targetRange = `${config.sheetName}!${config.range}`;
  const valuesResponse = await sheets.spreadsheets.values.get({
    spreadsheetId: config.spreadsheetId,
    range: targetRange
  });

  const rows = valuesResponse.data.values || [];
  const nonEmptyRows = countNonEmptyRows(rows);
  const headerCheck = compareHeaders(rows[0] || [], config.columns);
  const credentialSummary = readCredentialSummary(config.credentialsFile);

  return {
    ok: true,
    authentication: "passed",
    spreadsheetAccess: "passed",
    spreadsheetId: config.spreadsheetId,
    spreadsheetTitle,
    sheetName: config.sheetName,
    sheetExists: true,
    configuredRange: config.range,
    targetRange,
    totalRowsRead: rows.length,
    nonEmptyRows,
    hasRecords: nonEmptyRows > 0,
    headerPresent: headerCheck.headerPresent,
    headerMatchesConfiguredColumns: headerCheck.headerMatchesConfiguredColumns,
    missingConfiguredColumns: headerCheck.missingColumns,
    configuredColumns: config.columns,
    writeMapping: config.writeMapping,
    credential: credentialSummary,
    notes: nonEmptyRows > 0
      ? "Google Sheets connection is valid and the configured sheet/range has records."
      : "Google Sheets connection is valid, but the configured sheet/range has no records yet."
  };
}

async function main() {
  try {
    const argv = process.argv.slice(2);
    if (argv.includes("--help") || argv.includes("-h")) {
      console.log(usage());
      process.exit(0);
    }

    const result = await testGoogleSheetsConnection();
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  } catch (error) {
    console.error(JSON.stringify({
      ok: false,
      authentication: "failed_or_not_verified",
      spreadsheetAccess: "failed_or_not_verified",
      error: error.message
    }, null, 2));
    process.exit(1);
  }
}

const currentFilePath = fileURLToPath(import.meta.url);
const executedFilePath = process.argv[1] ? path.resolve(process.argv[1]) : "";

if (currentFilePath === executedFilePath) {
  main();
}
