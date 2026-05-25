import fs from "node:fs";
import path from "node:path";

const DEFAULT_CONFIG_PATH = "./config/google/sheets.config.json";

export function loadSheetsConfig(configPath = process.env.GOOGLE_SHEETS_CONFIG || DEFAULT_CONFIG_PATH) {
  const absoluteConfigPath = path.resolve(process.cwd(), configPath);

  if (!fs.existsSync(absoluteConfigPath)) {
    throw new Error(`Config file not found: ${absoluteConfigPath}. Copy config/google/sheets.config.example.json to config/google/sheets.config.json and update it.`);
  }

  const config = JSON.parse(fs.readFileSync(absoluteConfigPath, "utf8"));
  const requiredFields = ["spreadsheetId", "sheetName", "range", "credentialsFile"];

  for (const field of requiredFields) {
    if (!config[field] || typeof config[field] !== "string") {
      throw new Error(`Missing or invalid config field: ${field}`);
    }
  }

  const credentialsPath = path.resolve(process.cwd(), config.credentialsFile);
  if (!fs.existsSync(credentialsPath)) {
    throw new Error(`Credentials file not found: ${credentialsPath}. Place the service account JSON there or update credentialsFile.`);
  }

  return {
    spreadsheetId: config.spreadsheetId,
    sheetName: config.sheetName,
    range: config.range,
    valueInputOption: config.valueInputOption || "USER_ENTERED",
    credentialsFile: credentialsPath,
    columns: config.columns || ["Employee ID", "Name", "Challenge", "Attempt", "Report URL", "Status", "Score"],
    writeMapping: config.writeMapping || {
      argument1: "Column 1 - Employee ID",
      argument2: "Column 4 - Attempt",
      argument3: "Column 7 - Score"
    }
  };
}
