#!/usr/bin/env python3
"""Append copyright headers to repository Python files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

HEADER = '''"""Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.

All rights reserved.

Non-commercial use is permitted for review and research only.
"""\n\n'''


def iter_py_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if ".git" in path.parts:
            continue
        yield path


def has_header(content: str) -> bool:
    return "Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy." in content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="src")
    args = parser.parse_args()

    root = Path(args.root)
    count = 0
    for path in iter_py_files(root):
        content = path.read_text(encoding="utf-8")
        if has_header(content):
            continue
        path.write_text(HEADER + content, encoding="utf-8")
        count += 1
    print(f"updated={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
