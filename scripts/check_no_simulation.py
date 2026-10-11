#!/usr/bin/env python3
"""
Production Guard: No-Simulation Policy Validator
Scans source files in backend/src and frontend/src for synthetic/simulated logic,
fake responses, hardcoded test topologies, or fake token streams.

Exits with code 1 if violations are found.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Banned pattern tokens as specified in engineering standards
BANNED_PATTERN = re.compile(
    r"\b(simulat\w*|fake_\w+|mock_data|hardcoded|time\.sleep)\b",
    re.IGNORECASE,
)

# Allowed file extensions to inspect
CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
    ".sh",
    ".ps1",
}

# Directories to ignore
IGNORED_DIRS = {
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "tests",
    "fixtures",
    "test_fixtures",
    "datasets",
}

# Scanned source roots relative to repository root
DEFAULT_TARGET_DIRS = ["backend/src", "frontend/src"]


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for banned tokens. Returns list of (line_num, match_token, line_text)."""
    violations: list[tuple[int, str, str]] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"Warning: could not read {file_path}: {exc}", file=sys.stderr)
        return violations

    for idx, line in enumerate(content.splitlines(), start=1):
        # Ignore comments if line starts with # or //
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        match = BANNED_PATTERN.search(line)
        if match:
            violations.append((idx, match.group(0), line.strip()))

    return violations


def scan_directory(base_dir: Path, target_subdirs: list[str]) -> dict[Path, list[tuple[int, str, str]]]:
    """Scan targeted directories for banned tokens."""
    all_violations: dict[Path, list[tuple[int, str, str]]] = {}

    for subdir in target_subdirs:
        target_path = base_dir / subdir
        if not target_path.exists():
            continue

        for root, dirs, files in os.walk(target_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext in CODE_EXTENSIONS:
                    file_path = Path(root) / filename
                    file_violations = scan_file(file_path)
                    if file_violations:
                        all_violations[file_path] = file_violations

    return all_violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that no synthetic, simulated, or fake logic exists in production code."
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        default=Path("."),
        help="Path to project repository root (default: current directory)",
    )
    parser.add_argument(
        "--subdirs",
        nargs="+",
        default=DEFAULT_TARGET_DIRS,
        help="Subdirectories to scan (default: backend/src frontend/src)",
    )
    args = parser.parse_args()

    repo_path = args.path.resolve()
    print(f"--> [NO-SIMULATION GUARD] Scanning {repo_path} across {args.subdirs}...")

    violations = scan_directory(repo_path, args.subdirs)

    total_violations = sum(len(v) for v in violations.values())

    if total_violations == 0:
        print("--> [NO-SIMULATION GUARD] PASS: 0 simulated/fake patterns found. Codebase is clean.")
        return 0

    print(
        f"\n[ERROR] Found {total_violations} banned pattern(s) across {len(violations)} file(s):\n",
        file=sys.stderr,
    )
    for file_path, items in violations.items():
        rel_path = file_path.relative_to(repo_path)
        print(f"  File: {rel_path}", file=sys.stderr)
        for line_no, token, line_content in items:
            print(f"    Line {line_no:4d} | Token: '{token}' | {line_content}", file=sys.stderr)
        print(file=sys.stderr)

    print(
        "--> [NO-SIMULATION GUARD] FAIL: Banned patterns detected in production code.\n"
        "Replace simulated logic with real implementations or return RFC 7807 503 degraded states.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
