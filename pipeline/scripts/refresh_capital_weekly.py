#!/usr/bin/env python3
"""Compatibility wrapper; use ``python3 -m pipeline.refresh``."""

from pipeline.refresh import main


if __name__ == "__main__":
    raise SystemExit(main())
