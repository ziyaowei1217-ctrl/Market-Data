import assert from "node:assert/strict";
import test from "node:test";

import {
  derivePeriod,
  workbookCases,
} from "../scripts/verify_weekly_workbooks.mjs";

test("derivePeriod accepts a weekly output directory", () => {
  assert.equal(
    derivePeriod("/tmp/week_20260727-20260802"),
    "20260727-20260802",
  );
  assert.throws(
    () => derivePeriod("/tmp/latest"),
    /week directory must be named/,
  );
});

test("workbookCases derives all public workbook names", () => {
  assert.deepEqual(workbookCases("20260727-20260802"), [
    ["01_股票指数_20260727-20260802.xlsx", 3, "股票指数"],
    ["02_跨市场行业_20260727-20260802.xlsx", 6, "跨市场行业"],
    ["03_宏观资产_20260727-20260802.xlsx", 8, "宏观资产"],
    ["04_事件与市场背景_20260727-20260802.xlsx", 8, "事件与市场背景"],
  ]);
});
