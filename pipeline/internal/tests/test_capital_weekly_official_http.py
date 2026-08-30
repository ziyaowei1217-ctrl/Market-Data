from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest

import requests

from pipeline.internal.capital_weekly.official_http import (
    OfficialHttpError,
    OfficialHttpPolicy,
    official_get,
)


class _Response:
    def __init__(self, status_code, body=b"", *, headers=None, url=None):
        self.status_code = status_code
        self.content = body
        self.headers = headers or {}
        self.url = url


class _Session:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = self.sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class _DeadlineResponseSession(_Session):
    def __init__(self, clock, response):
        super().__init__([response])
        self.clock = clock

    def get(self, url, **kwargs):
        result = super().get(url, **kwargs)
        self.clock.now = 1.0
        return result


class OfficialHttpTests(unittest.TestCase):
    def setUp(self):
        self.policy = OfficialHttpPolicy(2, 5, 20, 3, (0.5, 1.0), 5)

    def test_retries_transport_and_rate_limit_with_exact_body_and_safe_trace(self):
        session = _Session(
            [
                requests.ConnectionError("https://api.eia.gov/?api_key=secret"),
                _Response(
                    429,
                    b"rate limited; secret",
                    headers={"Retry-After": "2"},
                    url="https://api.eia.gov/v2/data/?api_key=secret",
                ),
                _Response(
                    200,
                    b'{"data":[1]}',
                    headers={"X-Audit": "secret"},
                    url="https://api.eia.gov/v2/data/?api_key=secret",
                ),
            ]
        )
        sleeps = []
        clock = _Clock()

        response = official_get(
            session,
            "https://api.eia.gov/v2/data/?api_key=secret",
            policy=self.policy,
            audit_secrets=("secret",),
            sleep=lambda seconds: (sleeps.append(seconds), setattr(clock, "now", clock.now + seconds))[0],
            monotonic=clock,
        )

        self.assertEqual(response.body, b'{"data":[1]}')
        self.assertEqual(response.trace.attempts, 3)
        self.assertEqual(response.trace.status_codes, [429, 200])
        self.assertEqual(sleeps, [0.5, 2.0])
        self.assertNotIn("secret", response.url)
        self.assertNotIn("secret", response.trace.final_url)
        self.assertEqual(response.headers["X-Audit"], "[REDACTED]")
        self.assertEqual(session.calls[0][1]["timeout"], (2, 5))

    def test_parses_http_date_retry_after(self):
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=2)
        session = _Session(
            [
                _Response(503, headers={"Retry-After": format_datetime(retry_at, usegmt=True)}),
                _Response(200, b"ok", url="https://example.test/final"),
            ]
        )
        sleeps = []
        official_get(
            session,
            "https://example.test/data",
            policy=self.policy,
            sleep=sleeps.append,
        )
        self.assertEqual(len(sleeps), 1)
        self.assertGreaterEqual(sleeps[0], 0.0)
        self.assertLessEqual(sleeps[0], 2.0)

    def test_http_400_is_not_retried(self):
        session = _Session([_Response(400, b"do not archive this body")])

        with self.assertRaises(OfficialHttpError) as raised:
            official_get(session, "https://example.test/data", policy=self.policy)

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(raised.exception.code, "HTTP_400")
        self.assertFalse(raised.exception.retryable)
        self.assertNotIn("do not archive", raised.exception.safe_message)

    def test_schema_callback_error_is_not_retried(self):
        session = _Session([ValueError("schema callback rejected payload"), _Response(200, b"ok")])

        with self.assertRaises(OfficialHttpError) as raised:
            official_get(session, "https://example.test/data", policy=self.policy)

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(raised.exception.code, "SCHEMA_ERROR")
        self.assertEqual(raised.exception.phase, "schema")
        self.assertFalse(raised.exception.retryable)

    def test_total_deadline_prevents_a_further_attempt(self):
        clock = _Clock()
        session = _Session(
            [
                requests.Timeout("read timed out"),
                _Response(200, b"unexpected"),
            ]
        )

        def sleep(seconds):
            clock.now += seconds

        with self.assertRaises(OfficialHttpError) as raised:
            official_get(
                session,
                "https://example.test/data",
                policy=OfficialHttpPolicy(2, 5, 0.25, 3, (1.0,), 5),
                sleep=sleep,
                monotonic=clock,
            )

        self.assertEqual(len(session.calls), 1)
        self.assertEqual(raised.exception.code, "DEADLINE_EXCEEDED")
        self.assertEqual(raised.exception.attempts, 1)

    def test_remaining_deadline_limits_connect_and_read_timeout(self):
        clock = _Clock()
        monotonic_values = iter((0.0, 0.10, 0.10, 0.10))
        session = _Session([_Response(200, b"ok")])

        official_get(
            session,
            "https://example.test/data",
            policy=OfficialHttpPolicy(2, 5, 0.25, 1, (), 5),
            monotonic=lambda: next(monotonic_values),
        )

        timeout = session.calls[0][1]["timeout"]
        self.assertAlmostEqual(timeout[0], 0.15)
        self.assertAlmostEqual(timeout[1], 0.15)

    def test_response_after_total_deadline_is_rejected_even_when_http_200(self):
        clock = _Clock()
        session = _DeadlineResponseSession(clock, _Response(200, b"late"))

        with self.assertRaises(OfficialHttpError) as raised:
            official_get(
                session,
                "https://example.test/data",
                policy=OfficialHttpPolicy(2, 5, 0.25, 1, (), 5),
                monotonic=clock,
            )

        self.assertEqual(raised.exception.code, "DEADLINE_EXCEEDED")
        self.assertEqual(raised.exception.attempts, 1)

    def test_transport_error_text_and_final_url_redact_plain_percent_and_plus_secrets(self):
        secret = "a+b c"
        session = _Session(
            [
                requests.ConnectionError(
                    "plain=a+b c percent=a%2Bb%20c plus=a%2Bb+c"
                )
            ]
        )
        with self.assertRaises(OfficialHttpError) as raised:
            official_get(
                session,
                "https://example.test/data?api_key=a%2Bb%20c",
                policy=OfficialHttpPolicy(2, 5, 20, 1, (), 5),
                audit_secrets=(secret,),
            )

        self.assertNotIn("a+b c", raised.exception.safe_message)
        self.assertNotIn("a%2Bb%20c", raised.exception.safe_message)
        self.assertNotIn("a%2Bb+c", raised.exception.safe_message)


if __name__ == "__main__":
    unittest.main()
