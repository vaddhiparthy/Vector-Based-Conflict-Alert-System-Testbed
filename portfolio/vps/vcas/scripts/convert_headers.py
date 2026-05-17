#!/usr/bin/env python3
"""Convert the vCAS license header docstring into a comment block.

Python `from __future__ import ...` must appear right after the module docstring
(and optionally comments). A leading string-literal header breaks that rule.

This script rewrites files that start with the generated header docstring into:
  - shebang (if present)
  - comment header
  - original remaining content
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


HEADER_DOCSTRING_PREFIX = '"""Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.'

HEADER_COMMENT = (
    "# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.\n"
    "#\n"
    "# All rights reserved.\n"
    "#\n"
    "# Non-commercial use is permitted for review and research only.\n"
    "\n"
)


def iter_py_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if ".git" in path.parts:
            continue
        if ".venv" in path.parts or ".venv_ci" in path.parts or ".venv_uv" in path.parts:
            continue
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
            continue
        yield path


def _strip_header_docstring(content: str) -> str | None:
    if not content.startswith(HEADER_DOCSTRING_PREFIX) and not content.startswith("#!" + "\n" + HEADER_DOCSTRING_PREFIX):
        return None

    # Handle shebang, if any.
    shebang = ""
    rest = content
    if rest.startswith("#!"):
        nl = rest.find("\n")
        if nl != -1:
            shebang = rest[: nl + 1]
            rest = rest[nl + 1 :]

    if not rest.startswith(HEADER_DOCSTRING_PREFIX):
        return None

    # Drop the leading header docstring (first triple-quoted block).
    end = rest.find('"""', 3)
    if end == -1:
        return None
    end += 3
    rest2 = rest[end:]
    # Trim one optional blank line.
    if rest2.startswith("\r\n"):
        rest2 = rest2[2:]
    elif rest2.startswith("\n"):
        rest2 = rest2[1:]
    return shebang + HEADER_COMMENT + rest2.lstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Root directory to scan")
    args = parser.parse_args()

    root = Path(args.root)
    updated = 0
    for path in iter_py_files(root):
        content = path.read_text(encoding="utf-8")
        rewritten = _strip_header_docstring(content)
        if rewritten is None:
            continue
        if rewritten != content:
            path.write_text(rewritten, encoding="utf-8")
            updated += 1

    print(f"updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

