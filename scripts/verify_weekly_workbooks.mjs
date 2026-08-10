import path from "node:path";
import { pathToFileURL } from "node:url";

export function derivePeriod(weekDirArg) {
  const weekDir = path.resolve(weekDirArg);
  const match = path.basename(weekDir).match(/^week_(\d{8}-\d{8})$/);
  if (!match) {
    throw new Error("week directory must be named week_YYYYMMDD-YYYYMMDD");
  }
  return match[1];
}

export function workbookCases(period) {
  return [
    [`01_股票指数_${period}.xlsx`, 3, "股票指数"],
    [`02_跨市场行业_${period}.xlsx`, 6, "跨市场行业"],
    [`03_宏观资产_${period}.xlsx`, 8, "宏观资产"],
    [`04_事件与市场背景_${period}.xlsx`, 8, "事件与市场背景"],
  ];
}

export async function verifyWeek(weekDirArg) {
  const { FileBlob, SpreadsheetFile } = await import("@oai/artifact-tool");
  const weekDir = path.resolve(weekDirArg);
  const period = derivePeriod(weekDir);

  for (const [fileName, expectedSheets, title] of workbookCases(period)) {
    const workbook = await SpreadsheetFile.importXlsx(
      await FileBlob.load(path.join(weekDir, fileName)),
    );
    const sheets = Array.from(workbook.worksheets);
    if (sheets.length !== expectedSheets) {
      throw new Error(
        `${fileName}: ${sheets.length} sheets, expected ${expectedSheets}`,
      );
    }

    const coverTitle = workbook.worksheets
      .getItem("目录")
      .getRange("A1")
      .values[0][0];
    if (coverTitle !== `${period} ${title}`) {
      throw new Error(
        `${fileName}: unexpected cover title ${JSON.stringify(coverTitle)}`,
      );
    }

    const errors = await workbook.inspect({
      kind: "match",
      searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
      options: { useRegex: true, maxResults: 200 },
      summary: "final formula error scan",
    });
    if (!/matched 0 entries/i.test(errors.ndjson)) {
      throw new Error(
        `${fileName}: formula error scan failed\n${errors.ndjson}`,
      );
    }

    console.log(
      `${fileName}: sheets=${sheets.length}; formula_errors=0; cover=PASS`,
    );
  }
}

const isMain = process.argv[1]
  && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;

if (isMain) {
  const [weekDirArg] = process.argv.slice(2);
  if (!weekDirArg) {
    throw new Error("usage: node verify_weekly_workbooks.mjs WEEK_DIR");
  }
  await verifyWeek(weekDirArg);
}
