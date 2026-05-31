# Contributing

Thank you for contributing to `open-idotmatrix`.

## Design Rules

- Keep protocol logic in pure functions inside `open_idotmatrix/protocol.py`.
- Keep BLE code in `open_idotmatrix/transport.py`.
- Keep the user-facing API in `open_idotmatrix/device.py`.
- Every new packet must have an exact-byte test.
- Every protocol hypothesis must be documented in `docs/PROTOCOL.md`.
- Do not copy code from projects with incompatible licenses; reimplement behavior from documented observations and tests.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
ruff check .
```

## Pull Requests

An ideal PR includes:

1. an explanation of the command or function;
2. sent bytes;
3. the source of the hypothesis or capture;
4. a unit test;
5. updated documentation;
6. hardware results when applicable.
