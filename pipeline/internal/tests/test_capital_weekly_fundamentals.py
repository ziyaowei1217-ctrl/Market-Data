from datetime import date
import json
import unittest

from pipeline.internal.capital_weekly.context.fundamentals import (
    COMPANY_FUNDAMENTAL_FIELDS,
    build_company_fundamentals,
    validate_company_fundamental_input_references,
)


def _duration(
    start,
    end,
    value,
    filed,
    frame,
    *,
    form="10-Q",
    accession=None,
):
    return {
        "start": start,
        "end": end,
        "val": value,
        "accn": accession or f"acc-{frame}-{filed}",
        "fy": int(end[:4]),
        "fp": "FY" if form == "10-K" else frame[-2:],
        "form": form,
        "filed": filed,
        "frame": frame,
    }


def _instant(end, value, filed, frame, *, form="10-Q", accession=None):
    return {
        "end": end,
        "val": value,
        "accn": accession or f"acc-{frame}-{filed}",
        "fy": int(end[:4]),
        "fp": "FY" if form == "10-K" else "Q2",
        "form": form,
        "filed": filed,
        "frame": frame,
    }


def company_facts_payload():
    quarter_periods = [
        ("2025-07-01", "2025-09-30", "2025-10-20", "CY2025Q3"),
        ("2025-10-01", "2025-12-31", "2026-02-20", "CY2025Q4"),
        ("2026-01-01", "2026-03-31", "2026-05-01", "CY2026Q1"),
        ("2026-04-01", "2026-06-30", "2026-08-07", "CY2026Q2"),
    ]
    annual_periods = [
        ("2021-01-01", "2021-12-31", "2022-02-20", "CY2021", 300.0),
        ("2022-01-01", "2022-12-31", "2023-02-20", "CY2022", 320.0),
        ("2023-01-01", "2023-12-31", "2024-02-20", "CY2023", 340.0),
        ("2024-01-01", "2024-12-31", "2025-02-20", "CY2024", 360.0),
    ]
    quarter_values = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": [100, 110, 120, 130],
        "GrossProfit": [40, 44, 48, 52],
        "OperatingIncomeLoss": [20, 22, 24, 26],
        "NetIncomeLoss": [15, 16.5, 18, 19.5],
        "NetCashProvidedByUsedInOperatingActivities": [25, 27, 29, 31],
        "PaymentsToAcquirePropertyPlantAndEquipment": [5, 6, 7, 8],
        "DepreciationDepletionAndAmortization": [2, 2.2, 2.4, 2.6],
        "EarningsPerShareDiluted": [1.5, 1.65, 1.8, 1.95],
    }
    facts = {}
    for concept, values in quarter_values.items():
        unit = "USD/shares" if concept == "EarningsPerShareDiluted" else "USD"
        observations = [
            _duration(start, end, value, filed, frame)
            for (start, end, filed, frame), value in zip(quarter_periods, values)
        ]
        if concept == "RevenueFromContractWithCustomerExcludingAssessedTax":
            observations.append(
                _duration(
                    "2026-04-01",
                    "2026-06-30",
                    999,
                    "2026-08-10",
                    "CY2026Q2",
                    accession="monday-restatement",
                )
            )
        for start, end, filed, frame, revenue in annual_periods:
            scale = revenue / 300.0
            annual_value = {
                "RevenueFromContractWithCustomerExcludingAssessedTax": revenue,
                "GrossProfit": revenue * 0.4,
                "OperatingIncomeLoss": revenue * 0.2,
                "NetIncomeLoss": revenue * 0.15,
                "NetCashProvidedByUsedInOperatingActivities": revenue * 0.24,
                "PaymentsToAcquirePropertyPlantAndEquipment": revenue * 0.05,
                "DepreciationDepletionAndAmortization": revenue * 0.02,
                "EarningsPerShareDiluted": 4.5 * scale,
            }[concept]
            observations.append(
                _duration(
                    start,
                    end,
                    annual_value,
                    filed,
                    frame,
                    form="10-K",
                )
            )
        facts[concept] = {"label": concept, "units": {unit: observations}}

    instant_concepts = {
        "EntityCommonStockSharesOutstanding": ("shares", 10.0),
        "StockholdersEquity": ("USD", 100.0),
        "CashAndCashEquivalentsAtCarryingValue": ("USD", 10.0),
        "LongTermDebtCurrent": ("USD", 5.0),
        "LongTermDebtNoncurrent": ("USD", 25.0),
    }
    annual_instants = [
        ("2021-12-31", "2022-02-20", "CY2021I", 0.70),
        ("2022-12-31", "2023-02-20", "CY2022I", 0.80),
        ("2023-12-31", "2024-02-20", "CY2023I", 0.90),
        ("2024-12-31", "2025-02-20", "CY2024I", 0.95),
    ]
    for concept, (unit, current) in instant_concepts.items():
        observations = [
            _instant("2026-06-30", current, "2026-08-07", "CY2026Q2I")
        ]
        observations += [
            _instant(end, current * scale, filed, frame, form="10-K")
            for end, filed, frame, scale in annual_instants
        ]
        facts[concept] = {"label": concept, "units": {unit: observations}}

    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {"us-gaap": facts},
    }


class CompanyFundamentalsTests(unittest.TestCase):
    def setUp(self):
        self.rows = build_company_fundamentals(
            json.dumps(company_facts_payload()),
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            as_of_date=date(2026, 8, 9),
            price_history=[
                {"date": "2022-02-18", "close": 8.0},
                {"date": "2023-02-17", "close": 10.0},
                {"date": "2024-02-20", "close": 12.0},
                {"date": "2025-02-20", "close": 14.0},
                {"date": "2026-08-07", "close": 20.0},
                {"date": "2026-08-10", "close": 200.0},
            ],
        )

    def _latest(self, code):
        candidates = [row for row in self.rows if row["metric_code"] == code]
        self.assertTrue(candidates, code)
        return max(candidates, key=lambda row: (row["observation_date"], row["known_as_of"]))

    def test_rows_follow_the_typed_contract_and_cutoff(self):
        self.assertTrue(all(set(COMPANY_FUNDAMENTAL_FIELDS) == set(row) for row in self.rows))
        self.assertTrue(all(row["filing_date"] <= "2026-08-09" for row in self.rows if row["filing_date"]))
        self.assertTrue(all(row["observation_date"] <= "2026-08-09" for row in self.rows))
        self.assertNotIn("monday-restatement", {row["accession_number"] for row in self.rows})
        self.assertEqual(self._latest("share_price")["value"], 20.0)

    def test_reported_ttm_margin_and_fcf_calculations_are_auditable(self):
        self.assertEqual(self._latest("revenue")["value"], 130.0)
        self.assertEqual(self._latest("revenue_ttm")["value"], 460.0)
        self.assertAlmostEqual(self._latest("free_cash_flow_ttm")["value"], 86.0)
        self.assertAlmostEqual(self._latest("gross_margin_ttm")["value"], 0.4)
        self.assertAlmostEqual(self._latest("operating_margin_ttm")["value"], 0.2)
        self.assertAlmostEqual(self._latest("net_margin_ttm")["value"], 0.15)
        for code in (
            "revenue_ttm",
            "free_cash_flow_ttm",
            "gross_margin_ttm",
            "operating_margin_ttm",
            "net_margin_ttm",
        ):
            row = self._latest(code)
            self.assertTrue(row["calculation_id"])
            self.assertEqual(row["formula_version"], "fundamentals-v1")
            self.assertTrue(row["input_record_ids"])

    def test_trailing_valuation_and_historical_percentiles_use_published_inputs(self):
        self.assertAlmostEqual(self._latest("trailing_pe")["value"], 200.0 / 69.0)
        self.assertAlmostEqual(self._latest("price_to_book")["value"], 2.0)
        self.assertAlmostEqual(self._latest("price_to_sales")["value"], 200.0 / 460.0)
        self.assertAlmostEqual(
            self._latest("ev_to_ebitda")["value"], 220.0 / 101.2
        )
        for code in (
            "trailing_pe_percentile",
            "price_to_book_percentile",
            "price_to_sales_percentile",
            "ev_to_ebitda_percentile",
        ):
            row = self._latest(code)
            self.assertEqual(row["proxy_type"], "historical_point_in_time_percentile")
            self.assertGreaterEqual(row["value"], 0.0)
            self.assertLessEqual(row["value"], 100.0)
        validate_company_fundamental_input_references(self.rows)

    def test_missing_inputs_suppress_only_the_affected_multiple(self):
        payload = company_facts_payload()
        del payload["facts"]["us-gaap"]["DepreciationDepletionAndAmortization"]
        rows = build_company_fundamentals(
            json.dumps(payload),
            ticker="AAPL",
            cik="0000320193",
            company_name="Apple Inc.",
            as_of_date=date(2026, 8, 9),
            price_history=[{"date": "2026-08-07", "close": 20.0}],
        )
        codes = {row["metric_code"] for row in rows}
        self.assertIn("trailing_pe", codes)
        self.assertNotIn("ev_to_ebitda", codes)
        self.assertFalse(any(code.endswith("_percentile") for code in codes))

    def test_unresolved_calculation_input_is_rejected(self):
        broken = [dict(row) for row in self.rows]
        derived = next(row for row in broken if row["calculation_id"])
        derived["input_record_ids"] = "missing-record"
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            validate_company_fundamental_input_references(broken)

    def test_ytd_differences_and_annual_residual_form_four_standalone_quarters(self):
        observations = [
            _duration(
                "2025-01-01",
                "2025-03-31",
                10,
                "2025-05-01",
                "CY2025Q1",
            ),
            _duration(
                "2025-01-01",
                "2025-06-30",
                25,
                "2025-08-01",
                "CY2025Q2",
            ),
            _duration(
                "2025-01-01",
                "2025-09-30",
                45,
                "2025-11-01",
                "CY2025Q3",
            ),
            _duration(
                "2025-01-01",
                "2025-12-31",
                70,
                "2026-02-20",
                "CY2025",
                form="10-K",
            ),
        ]
        payload = {
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {"USD": observations}
                    }
                }
            }
        }

        rows = build_company_fundamentals(
            json.dumps(payload),
            ticker="TEST",
            cik="1",
            company_name="Test Inc.",
            as_of_date=date(2026, 8, 9),
            price_history=[],
        )

        standalone = sorted(
            row["value"]
            for row in rows
            if row["metric_code"] == "revenue"
            and row["frequency"] == "quarterly_derived"
        )
        self.assertEqual(standalone, [15.0, 20.0, 25.0])
        self.assertEqual(
            max(
                (
                    row
                    for row in rows
                    if row["metric_code"] == "revenue_ttm"
                ),
                key=lambda row: row["observation_date"],
            )["value"],
            70.0,
        )
        validate_company_fundamental_input_references(rows)


if __name__ == "__main__":
    unittest.main()
