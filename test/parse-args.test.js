import assert from "node:assert/strict";
import { parseArgs, buildSpreadsheetRow } from "../src/add-google-spreadsheets.js";

const parsed = parseArgs(["EMP001", "1", "70.5"]);
assert.deepEqual(parsed, { employeeId: "EMP001", attempt: 1, score: 70.5 });

assert.deepEqual(buildSpreadsheetRow(parsed), ["EMP001", "", "", 1, "", "", 70.5]);

assert.throws(() => parseArgs(["EMP001", "x", "70.5"]), /Attempt must be a number/);
assert.throws(() => parseArgs(["EMP001", "1", "x"]), /Score must be a number/);
assert.throws(() => parseArgs(["EMP001", "1"]), /Usage/);

console.log("parse-args.test.js passed");
