"""Bounded HTTP GET transport for official data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from typing import Any, Callable, Mapping, Sequence

import requests

from pipeline.internal.common import sanitize_audit_text


@dataclass(frozen=True)
class OfficialHttpPolicy:
    connect_timeout: float
    read_timeout: float
    total_timeout: float
    max_attempts: int
    backoff_seconds: Sequence[float]
    retry_after_cap: float

    def __post_init__(self) -> None:
        if self.connect_timeout <= 0 or self.read_timeout <= 0:
            raise ValueError("HTTP connect/read timeouts must be positive")
        if self.total_timeout <= 0:
            raise ValueError("HTTP total timeout must be positive")
        if self.max_attempts < 1:
            raise ValueError("HTTP max_attempts must be at least one")
        if self.retry_after_cap < 0:
            raise ValueError("HTTP retry_after_cap cannot be negative")
        if any(float(delay) < 0 for delay in self.backoff_seconds):
            raise ValueError("HTTP backoff_seconds cannot contain negatives")


@dataclass(frozen=True)
class OfficialHttpTrace:
    attempts: int
    elapsed_ms: int
    status_codes: list[int]
    final_url: str


@dataclass(frozen=True)
class OfficialHttpResponse:
    body: bytes
    url: str
    headers: dict[str, str]
    trace: OfficialHttpTrace


class OfficialHttpError(RuntimeError):
    """Safe, structured failure from the bounded official HTTP executor."""

    def __init__(
        self,
        code: str,
        phase: str,
        retryable: bool,
        attempts: int,
        safe_message: str,
    ) -> None:
        self.code = code
        self.phase = phase
        self.retryable = retryable
        self.attempts = attempts
        self.safe_message = safe_message
        super().__init__(safe_message)


_RETRY_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
_RETRY_EXCEPTIONS = (requests.Timeout, requests.ConnectionError)


def official_get(
    session: requests.Session,
    url: str,
    *,
    policy: OfficialHttpPolicy,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    audit_secrets: Sequence[str] = (),
    sleep: Callable[[float], Any] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> OfficialHttpResponse:
    """GET an official endpoint with bounded retries and safe diagnostics."""
    started = monotonic()
    status_codes: list[int] = []
    attempts = 0
    request_url = _request_url(url, params)

    while attempts < policy.max_attempts:
        remaining = _remaining(policy, started, monotonic)
        if remaining <= 0:
            raise _deadline_error(attempts)
        attempts += 1
        request_kwargs: dict[str, Any] = {
            "timeout": (policy.connect_timeout, policy.read_timeout),
        }
        if headers is not None:
            request_kwargs["headers"] = headers
        if params is not None:
            request_kwargs["params"] = params

        try:
            response = session.get(url, **request_kwargs)
        except _RETRY_EXCEPTIONS as error:
            if _remaining(policy, started, monotonic) <= 0:
                raise _deadline_error(attempts) from None
            if attempts >= policy.max_attempts:
                raise _transport_error(error, attempts, audit_secrets) from None
            _sleep_before_retry(
                _backoff(policy, attempts), policy, started, monotonic, sleep, attempts
            )
            continue
        except requests.RequestException as error:
            raise _request_error(error, attempts, audit_secrets) from None
        except Exception as error:
            raise _schema_error(error, attempts, audit_secrets) from None

        try:
            status_code = int(response.status_code)
        except (AttributeError, TypeError, ValueError) as error:
            raise _schema_error(error, attempts, audit_secrets) from None
        status_codes.append(status_code)

        if 200 <= status_code < 400:
            try:
                body = _response_body(response)
                raw_final_url = getattr(response, "url", None) or request_url
                safe_url = sanitize_audit_text(
                    raw_final_url,
                    secrets=tuple(str(secret) for secret in audit_secrets),
                )
                safe_headers = _safe_headers(
                    getattr(response, "headers", {}), audit_secrets
                )
            except Exception as error:
                raise _schema_error(error, attempts, audit_secrets) from None
            return OfficialHttpResponse(
                body=body,
                url=safe_url,
                headers=safe_headers,
                trace=OfficialHttpTrace(
                    attempts=attempts,
                    elapsed_ms=_elapsed_ms(started, monotonic),
                    status_codes=status_codes,
                    final_url=safe_url,
                ),
            )

        retryable = status_code in _RETRY_STATUS_CODES
        if not retryable:
            raise _http_error(status_code, attempts, request_url, audit_secrets) from None
        if attempts >= policy.max_attempts:
            raise _http_error(
                status_code,
                attempts,
                getattr(response, "url", None) or request_url,
                audit_secrets,
                retryable=True,
            ) from None
        retry_after = _retry_after(response, policy.retry_after_cap)
        delay = retry_after if retry_after is not None else _backoff(policy, attempts)
        _sleep_before_retry(delay, policy, started, monotonic, sleep, attempts)

    raise _deadline_error(attempts)


def _remaining(
    policy: OfficialHttpPolicy,
    started: float,
    monotonic: Callable[[], float],
) -> float:
    return float(policy.total_timeout) - max(0.0, float(monotonic() - started))


def _elapsed_ms(started: float, monotonic: Callable[[], float]) -> int:
    return max(0, int(round((float(monotonic()) - started) * 1000)))


def _request_url(url: str, params: Mapping[str, Any] | None) -> str:
    if params is None:
        return str(url)
    try:
        prepared = requests.Request("GET", url, params=params).prepare()
        return prepared.url or str(url)
    except Exception:
        return str(url)


def _response_body(response: Any) -> bytes:
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content
    if isinstance(content, bytearray):
        return bytes(content)
    if content is not None:
        return str(content).encode("utf-8")
    text = getattr(response, "text", "")
    return text if isinstance(text, bytes) else str(text).encode("utf-8")


def _safe_headers(headers: Any, secrets: Sequence[str]) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        return {}
    normalized_secrets = tuple(str(secret) for secret in secrets)
    return {
        str(key): sanitize_audit_text(value, secrets=normalized_secrets)
        for key, value in headers.items()
    }


def _backoff(policy: OfficialHttpPolicy, attempt: int) -> float:
    if not policy.backoff_seconds:
        return 0.0
    index = min(max(attempt - 1, 0), len(policy.backoff_seconds) - 1)
    return max(0.0, float(policy.backoff_seconds[index]))


def _sleep_before_retry(
    delay: float,
    policy: OfficialHttpPolicy,
    started: float,
    monotonic: Callable[[], float],
    sleep: Callable[[float], Any],
    attempts: int,
) -> None:
    remaining = _remaining(policy, started, monotonic)
    if remaining <= 0:
        raise _deadline_error(attempts)
    sleep(min(max(0.0, float(delay)), remaining))


def _retry_after(response: Any, cap: float) -> float | None:
    headers = getattr(response, "headers", {})
    if not isinstance(headers, Mapping):
        return None
    value = next(
        (raw for key, raw in headers.items() if str(key).lower() == "retry-after"),
        None,
    )
    if value is None:
        return None
    text = str(value).strip()
    try:
        delay = float(text)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(text)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None
    return min(max(0.0, delay), float(cap))


def _safe_message(value: Any, secrets: Sequence[str]) -> str:
    message = sanitize_audit_text(value, secrets=tuple(str(secret) for secret in secrets))
    return message or type(value).__name__


def _transport_error(error: BaseException, attempts: int, secrets: Sequence[str]) -> OfficialHttpError:
    code = "TIMEOUT" if isinstance(error, requests.Timeout) else "CONNECTION_ERROR"
    return OfficialHttpError(code, "transport", True, attempts, _safe_message(error, secrets))


def _request_error(error: BaseException, attempts: int, secrets: Sequence[str]) -> OfficialHttpError:
    return OfficialHttpError(
        "REQUEST_ERROR", "transport", False, attempts, _safe_message(error, secrets)
    )


def _schema_error(error: BaseException, attempts: int, secrets: Sequence[str]) -> OfficialHttpError:
    return OfficialHttpError(
        "SCHEMA_ERROR", "schema", False, attempts, _safe_message(error, secrets)
    )


def _http_error(
    status_code: int,
    attempts: int,
    url: str,
    secrets: Sequence[str],
    *,
    retryable: bool = False,
) -> OfficialHttpError:
    safe_url = sanitize_audit_text(url, secrets=tuple(str(secret) for secret in secrets))
    return OfficialHttpError(
        f"HTTP_{status_code}",
        "http",
        retryable,
        attempts,
        f"HTTP {status_code} response from {safe_url}",
    )


def _deadline_error(attempts: int) -> OfficialHttpError:
    return OfficialHttpError(
        "DEADLINE_EXCEEDED", "deadline", False, attempts, "HTTP total deadline exceeded"
    )


__all__ = [
    "OfficialHttpError",
    "OfficialHttpPolicy",
    "OfficialHttpResponse",
    "OfficialHttpTrace",
    "official_get",
]
