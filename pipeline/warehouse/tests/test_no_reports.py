"""The warehouse keeps numbers only: no institution-report text, no report placeholders."""

import unittest
from pathlib import Path

from pipeline.warehouse.catalog.mapping import load_mapping, load_series
from pipeline.warehouse.db.store import SQLiteStore

REPO = Path(__file__).resolve().parents[3]
WAREHOUSE = REPO / "pipeline" / "warehouse"


class NoInstitutionReportsTests(unittest.TestCase):
    def test_no_indicator_waits_for_an_institution_report(self):
        methods = {m["method"] for m in load_mapping().values()}
        self.assertNotIn("report", methods)

    def test_former_report_indicators_are_excluded_with_reason(self):
        m = load_mapping()["05-002"]
        self.assertEqual(m["method"], "excluded")
        self.assertIn("机构周报", m["coverage_note"])

    def test_factset_numbers_are_kept(self):
        keys = {s["key"] for s in load_series()}
        self.assertIn("FACTSET:forward_pe", keys)
        uses_factset = [m for m in load_mapping().values() if "{FACTSET:" in m["formula"]]
        self.assertTrue(uses_factset)
        self.assertTrue(all(m["method"] == "api" for m in uses_factset))

    def test_sqlite_store_has_no_report_text_table(self):
        store = SQLiteStore()
        store.init_schema()
        tables = {row[0] for row in store.conn.execute("select name from sqlite_master where type='table'")}
        self.assertNotIn("report_pages", tables)
        self.assertFalse(hasattr(store, "upsert_report_pages"))

    def test_postgres_schema_drops_report_text_table(self):
        sql = (WAREHOUSE / "db" / "schema.sql").read_text(encoding="utf-8")
        self.assertNotIn("create table if not exists public.report_pages", sql)
        self.assertIn("drop table if exists public.report_pages", sql)

    def test_cli_has_no_archive_command(self):
        from pipeline.warehouse.__main__ import main

        with self.assertRaises(SystemExit):
            main(["archive-reports"])

    def test_workflow_stores_no_report_or_page_text(self):
        workflow = (REPO / ".github" / "workflows" / "warehouse.yml").read_text(encoding="utf-8")
        self.assertNotIn("archive-reports", workflow)
        self.assertNotIn("inspect_sources", workflow)

    def test_report_archive_module_is_gone(self):
        self.assertFalse((WAREHOUSE / "providers" / "reports.py").exists())


if __name__ == "__main__":
    unittest.main()
