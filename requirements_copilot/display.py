"""Console formatting, so every demo prints in the same shape."""

from __future__ import annotations

import textwrap

WIDTH = 78


def banner(title: str) -> None:
    print("\n" + "=" * WIDTH)
    print(title.upper())
    print("=" * WIDTH)


def step(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(0, WIDTH - len(title) - 5))


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def kv(label: str, value, width: int = 24) -> None:
    print(f"  {label:<{width}}{value}")


def wrap(text, indent: int = 9) -> str:
    return textwrap.fill(str(text), width=WIDTH, subsequent_indent=" " * indent)
