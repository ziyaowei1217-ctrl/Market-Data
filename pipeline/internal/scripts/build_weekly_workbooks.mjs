import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [outputsRootArg, previewRootArg] = process.argv.slice(2);
if (!outputsRootArg || !previewRootArg) {
  throw new Error("usage: node build_weekly_workbooks.mjs OUTPUTS_ROOT PREVIEW_ROOT");
}

const outputsRoot = path.resolve(outputsRootArg);
const previewRoot = path.resolve(previewRootArg);
const COLORS = {
  navy: "#17365D",
  blue: "#244062",
  paleBlue: "#EAF2F8",
  border: "#D9E2F3",
  white: "#FFFFFF",
  green: "#E2F0D9",
  red: "#FCE4D6",
  yellow: "#FFF2CC",
};

const suffixLabels = {
  "02_equity_indices": "数据",
  "03_equity_sectors": "数据",
  "03_gics_sectors": "数据",
  sector_divergence: "分化",
  source_log: "来源",
  commodities: "商品",
  fixed_income: "固收",
  foreign_exchange: "外汇",
  macro_divergence: "分化",
  money_market: "货币市场",
  policy_rates: "政策利率",
  commodity_fundamentals: "商品基本面",
  company_events: "公司事件",
  events: "事件",
  financial_conditions: "金融条件",
  market_internals: "市场内部",
  positioning_flows: "仓位资金流",
};

async function walkCsv(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const results = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) results.push(...await walkCsv(full));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith(".csv")) results.push(full);
  }
  return results;
}

function columnName(index) {
  let result = "";
  for (let value = index + 1; value > 0; value = Math.floor((value - 1) / 26)) {
    result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
  }
  return result;
}

function displayLength(value) {
  return [...String(value ?? "")].reduce((sum, char) => sum + (char.codePointAt(0) > 255 ? 2 : 1), 0);
}

function sheetBaseName(csvPath, weekDir) {
  const stem = path.basename(csvPath, ".csv");
  const parent = path.basename(path.dirname(csvPath));
  const suffix = suffixLabels[stem] || stem.replace(/[^\p{L}\p{N}_]+/gu, "_");
  const dateMatch = parent.match(/(\d{8})$/);
  const mmdd = dateMatch ? dateMatch[1].slice(4) : "";
  if (parent.includes("equity_indices")) return `指数_${suffix}`;
  if (parent.includes("equity_sectors")) return `跨市行业_${suffix}`;
  if (parent.includes("gics_sectors")) return `GICS_${suffix}`;
  if (parent.includes("macro_assets")) return `宏观${mmdd}_${suffix}`;
  if (parent.includes("weekly_context")) return `背景_${suffix}`;
  if (path.dirname(csvPath) === weekDir) return suffix;
  return `${parent.slice(0, 12)}_${suffix}`;
}

function uniqueSheetName(base, used) {
  let clean = base.replace(/[\\/*?:\[\]]/g, "_").slice(0, 31) || "数据";
  let candidate = clean;
  let index = 2;
  while (used.has(candidate)) {
    const tail = `_${index++}`;
    candidate = `${clean.slice(0, 31 - tail.length)}${tail}`;
  }
  used.add(candidate);
  return candidate;
}

function relativeSource(csvPath, weekDir) {
  return path.relative(weekDir, csvPath).split(path.sep).join("/");
}

function inferRowsAndCols(sheet) {
  const used = sheet.getUsedRange(true);
  if (!used) return { used: null, values: [], rows: 0, cols: 0 };
  const values = used.values || [];
  const cols = values.reduce((max, row) => Math.max(max, row?.length || 0), 0);
  return { used, values, rows: Math.max(0, values.length - 1), cols };
}

function setSemanticFormats(sheet, values, rows, cols) {
  if (!values.length || !cols) return;
  const headers = (values[0] || []).map((value) => String(value ?? "").toLowerCase());
  const changeUnitIndex = headers.indexOf("change_unit");
  const changeUnits = changeUnitIndex >= 0
    ? new Set(values.slice(1).map((row) => String(row?.[changeUnitIndex] ?? "").toLowerCase()).filter(Boolean))
    : new Set();
  for (let col = 0; col < cols; col += 1) {
    const header = headers[col] || "";
    const letter = columnName(col);
    const dataRange = rows > 0 ? sheet.getRange(`${letter}2:${letter}${rows + 1}`) : null;
    if (!dataRange) continue;
    if (header === "date" || header.endsWith("_date") || header === "published_date") {
      dataRange.setNumberFormat("yyyy-mm-dd");
    } else if (["base_year", "forecast_year", "cagr_start_year", "cagr_end_year", "sort_order"].includes(header)
      || header.endsWith("_count") || header.endsWith("_rank") || header === "observations" || header === "elapsed_ms") {
      dataRange.setNumberFormat("#,##0");
    } else if (header === "breadth_ratio" || header === "median_return" || header === "leader_laggard_spread") {
      dataRange.setNumberFormat("0.00%;[Red](0.00%);-");
    } else if (header.endsWith("_change") && changeUnits.size === 1 && changeUnits.has("pct")) {
      dataRange.setNumberFormat("0.00%;[Red](0.00%);-");
    } else if (header.includes("value") || header === "cagr" || header === "dispersion" || header === "change_range") {
      dataRange.setNumberFormat("#,##0.0000;[Red](#,##0.0000);-");
    }
  }
}

function styleDataSheet(sheet, values, rows, cols, tableIndex) {
  sheet.showGridLines = false;
  const hasData = values.some((row) => row?.some((value) => value !== null && String(value).trim() !== ""));
  if (!hasData || !cols) {
    sheet.getRange("A1").values = [["源 CSV 当前为空"]];
    sheet.getRange("A1:D1").format = {
      fill: COLORS.yellow,
      font: { bold: true, color: COLORS.navy, size: 11 },
      rowHeight: 28,
    };
    sheet.getRange("A2").values = [["已保留此 Sheet，便于后续数据补录或替换。"]];
    sheet.getRange("A2:D2").format = { font: { color: "#666666", italic: true }, rowHeight: 24 };
    sheet.getRange("A1:A2").format.columnWidth = 56;
    return;
  }

  const lastCol = columnName(cols - 1);
  const lastRow = rows + 1;
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: COLORS.blue,
    font: { color: COLORS.white, bold: true, size: 9 },
    rowHeight: 32,
    wrapText: true,
    verticalAlignment: "center",
  };
  if (rows > 0) {
    sheet.getRange(`A2:${lastCol}${lastRow}`).format = {
      borders: {
        insideHorizontal: { style: "thin", color: COLORS.border },
        bottom: { style: "thin", color: COLORS.border },
      },
      font: { size: 9 },
      rowHeight: 22,
      verticalAlignment: "center",
    };
  }
  sheet.freezePanes.freezeRows(1);

  const headers = (values[0] || []).map((value) => String(value ?? "").toLowerCase());
  for (let col = 0; col < cols; col += 1) {
    const header = headers[col] || "";
    let width = Math.min(34, Math.max(10, ...values.slice(0, 80).map((row) => displayLength(row?.[col]) + 2)));
    if (/url|notes|sentence|commentary|watch_focus|market_impact/.test(header)) width = Math.min(60, Math.max(26, width));
    sheet.getCell(0, col).format.columnWidth = width;
    if (/url|notes|sentence|commentary|watch_focus|market_impact/.test(header) && rows > 0) {
      const letter = columnName(col);
      sheet.getRange(`${letter}2:${letter}${lastRow}`).format.wrapText = true;
      sheet.getRange(`${letter}2:${letter}${lastRow}`).format.rowHeight = 48;
    }
    if ((header === "status" || header === "qc_flag") && rows > 0) {
      const letter = columnName(col);
      const statusRange = sheet.getRange(`${letter}2:${letter}${lastRow}`);
      statusRange.conditionalFormats.add("containsText", { text: "OK", format: { fill: COLORS.green, font: { bold: true, color: COLORS.navy } } });
      statusRange.conditionalFormats.add("containsText", { text: "FAILED", format: { fill: COLORS.red, font: { bold: true, color: "#9C0006" } } });
      statusRange.conditionalFormats.add("containsText", { text: "NOT_CONFIGURED", format: { fill: COLORS.yellow, font: { bold: true, color: "#7F6000" } } });
    }
  }
  setSemanticFormats(sheet, values, rows, cols);

  const table = sheet.tables.add(`A1:${lastCol}${lastRow}`, true, `WeeklyData${tableIndex}`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
}

function styleCover(sheet, weekName, manifest, partTitle = "周度数据汇总") {
  const lastRow = manifest.length + 5;
  sheet.showGridLines = false;
  sheet.getRange("A1:E1").merge();
  sheet.getRange("A1").values = [[`${weekName.replace("week_", "")} ${partTitle}`]];
  sheet.getRange("A1").format = {
    fill: COLORS.navy,
    font: { color: COLORS.white, bold: true, size: 15 },
    rowHeight: 30,
  };
  sheet.getRange("A2:E2").merge();
  sheet.getRange("A2").values = [["每个数据 Sheet 对应一个源 CSV；原始 CSV 保留在本周文件夹中。"]];
  sheet.getRange("A2").format = {
    fill: COLORS.paleBlue,
    font: { color: COLORS.navy, italic: true, size: 10 },
    rowHeight: 24,
  };
  sheet.getRange("A4:E4").values = [["Sheet", "数据行数", "列数", "源文件", "状态"]];
  sheet.getRange("A4:E4").format = {
    fill: COLORS.blue,
    font: { color: COLORS.white, bold: true },
    rowHeight: 24,
  };
  if (manifest.length) {
    sheet.getRangeByIndexes(4, 0, manifest.length, 5).values = manifest.map((item) => [
      item.sheetName, item.rows, item.cols, item.source, item.status,
    ]);
    sheet.getRange(`A5:E${lastRow}`).format = {
      borders: { insideHorizontal: { style: "thin", color: COLORS.border }, bottom: { style: "thin", color: COLORS.border } },
      rowHeight: 24,
      verticalAlignment: "center",
    };
    sheet.getRange(`B5:C${lastRow}`).setNumberFormat("#,##0");
    const statusRange = sheet.getRange(`E5:E${lastRow}`);
    statusRange.conditionalFormats.add("containsText", { text: "有数据", format: { fill: COLORS.green, font: { bold: true, color: COLORS.navy } } });
    statusRange.conditionalFormats.add("containsText", { text: "空文件", format: { fill: COLORS.yellow, font: { bold: true, color: "#7F6000" } } });
  }
  [20, 12, 10, 72, 12].forEach((width, col) => { sheet.getCell(0, col).format.columnWidth = width; });
  sheet.getRange(`D5:D${lastRow}`).format.wrapText = true;
  sheet.freezePanes.freezeRows(4);
  const table = sheet.tables.add(`A4:E${lastRow}`, true, "ManifestTable");
  table.style = "TableStyleMedium2";
}

await fs.mkdir(previewRoot, { recursive: true });
const weekEntries = (await fs.readdir(outputsRoot, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory() && /^week_\d{8}-\d{8}$/.test(entry.name))
  .sort((a, b) => a.name.localeCompare(b.name));

if (!weekEntries.length) throw new Error("no weekly folders found");
const weekEntry = weekEntries.at(-1);
const weekDir = path.join(outputsRoot, weekEntry.name);
const period = weekEntry.name.slice(5);
const targets = [
  {
    sourceDirs: [`capital_weekly_equity_indices_python_${period.slice(-8)}`],
    title: "股票指数",
    outputFile: `01_股票指数_${period}.xlsx`,
  },
  {
    sourceDirs: [
      `capital_weekly_equity_sectors_python_${period.slice(-8)}`,
      `capital_weekly_gics_sectors_python_${period.slice(-8)}`,
    ],
    title: "跨市场行业",
    outputFile: `02_跨市场行业_${period}.xlsx`,
  },
  {
    sourceDirs: [`capital_weekly_macro_assets_python_${period.slice(-8)}`],
    title: "宏观资产",
    outputFile: `03_宏观资产_${period}.xlsx`,
  },
  {
    sourceDirs: [`capital_weekly_context_${period.slice(-8)}`],
    title: "事件与市场背景",
    outputFile: `04_事件与市场背景_${period}.xlsx`,
  },
];

for (const [targetIndex, target] of targets.entries()) {
  const csvFiles = (await Promise.all(
    target.sourceDirs.map((sourceDir) => walkCsv(path.join(weekDir, sourceDir))),
  )).flat().sort((a, b) => a.localeCompare(b));
  const workbook = Workbook.create();
  const cover = workbook.worksheets.add("目录");
  const usedNames = new Set(["目录"]);
  const manifest = [];
  const sheetsToRender = [cover];

  for (const [fileIndex, csvPath] of csvFiles.entries()) {
    const sheetName = uniqueSheetName(sheetBaseName(csvPath, weekDir), usedNames);
    const csvText = await fs.readFile(csvPath, "utf8");
    let sheet;
    if (csvText.trim()) {
      const parsedWorkbook = await Workbook.fromCSV(csvText, { sheetName: "ParsedCSV" });
      const parsedSheet = parsedWorkbook.worksheets.getItem("ParsedCSV");
      const parsedRange = parsedSheet.getUsedRange(true);
      const parsedValues = parsedRange?.values || [];
      sheet = workbook.worksheets.add(sheetName);
      if (parsedValues.length && parsedValues[0]?.length) {
        sheet.getRangeByIndexes(0, 0, parsedValues.length, parsedValues[0].length).values = parsedValues;
      }
    } else {
      sheet = workbook.worksheets.add(sheetName);
    }
    const { values, rows, cols } = inferRowsAndCols(sheet);
    styleDataSheet(sheet, values, rows, cols, targetIndex * 100 + fileIndex + 1);
    manifest.push({
      sheetName,
      rows,
      cols,
      source: relativeSource(csvPath, weekDir),
      status: rows > 0 ? "有数据" : "空文件",
    });
    sheetsToRender.push(sheet);
  }

  styleCover(cover, weekEntry.name, manifest, target.title);

  const sheetInspect = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 10000 });
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 200 },
    summary: "final formula error scan",
  });
  if (!/matched 0 entries/i.test(errors.ndjson)) throw new Error(`${weekEntry.name}: formula error scan failed\n${errors.ndjson}`);

  const weekPreviewDir = path.join(previewRoot, weekEntry.name, target.outputFile.replace(/\.xlsx$/, ""));
  await fs.mkdir(weekPreviewDir, { recursive: true });
  for (const sheet of sheetsToRender) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 0.8, format: "png" });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    if (bytes.length < 100) throw new Error(`${weekEntry.name}/${sheet.name}: render was unexpectedly small`);
    await fs.writeFile(path.join(weekPreviewDir, `${sheet.name}.png`), bytes);
  }

  const outputPath = path.join(weekDir, target.outputFile);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
  const reopenedSheets = Array.from(reopened.worksheets);
  if (reopenedSheets.length !== manifest.length + 1) {
    throw new Error(`${weekEntry.name}: reopened sheet count ${reopenedSheets.length} != ${manifest.length + 1}`);
  }
  const coverInspect = await reopened.inspect({
    kind: "table",
    sheetId: "目录",
    range: `A1:E${manifest.length + 5}`,
    include: "values,formulas",
    tableMaxRows: manifest.length + 5,
    tableMaxCols: 5,
    maxChars: 12000,
  });
  const reopenedErrors = await reopened.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 200 },
    summary: "reopened workbook formula error scan",
  });
  if (!/matched 0 entries/i.test(reopenedErrors.ndjson)) {
    throw new Error(`${weekEntry.name}: reopened formula error scan failed\n${reopenedErrors.ndjson}`);
  }
  const inspectDir = path.join(previewRoot, weekEntry.name, "inspects");
  await fs.mkdir(inspectDir, { recursive: true });
  await fs.writeFile(
    path.join(inspectDir, `${target.outputFile}.inspect.ndjson`),
    `${sheetInspect.ndjson}\n${errors.ndjson}\n${coverInspect.ndjson}\n${reopenedErrors.ndjson}\n`,
    "utf8",
  );
  console.log(`${target.title}: ${csvFiles.length} CSV -> ${manifest.length + 1} sheets -> ${outputPath}`);
}
