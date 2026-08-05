#!/usr/bin/env python3
"""Validate poi_master.csv and print line numbers for fixable CSV errors."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_PATH = PROJECT_ROOT / "data" / "metadata" / "poi_master.csv"
DEFAULT_CATEGORY_PATH = PROJECT_ROOT / "data" / "metadata" / "dictionary.csv"

REQUIRED_FIELDS = [
    "id",
    "name_zh",
    "name_en",
    "category",
    "department",
    "faculty_leads",
    "occupants",
    "aliases",
    "description",
    "public_access",
    "source",
    "status",
]


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_csv_rows(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = [clean_cell(header) for header in reader.fieldnames or []]
        rows: list[tuple[int, dict[str, str]]] = []

        for line_number, row in enumerate(reader, start=2):
            cleaned_row = {
                clean_cell(header): clean_cell(value)
                for header, value in row.items()
                if header is not None
            }
            rows.append((line_number, cleaned_row))

    return headers, rows


def load_categories(path: Path) -> set[str]:
    if not path.exists():
        return set()

    headers, rows = read_csv_rows(path)
    if "category" not in headers:
        return set()
    return {row.get("category", "") for _, row in rows if row.get("category", "")}


def print_duplicate_ids(rows: list[tuple[int, dict[str, str]]]) -> int:
    line_numbers_by_id: dict[str, list[int]] = {}
    rows_by_id: dict[str, list[tuple[int, dict[str, str]]]] = {}

    for line_number, row in rows:
        poi_id = row.get("id", "")
        if not poi_id:
            continue
        line_numbers_by_id.setdefault(poi_id, []).append(line_number)
        rows_by_id.setdefault(poi_id, []).append((line_number, row))

    duplicate_ids = {
        poi_id: line_numbers
        for poi_id, line_numbers in sorted(line_numbers_by_id.items())
        if len(line_numbers) > 1
    }

    if not duplicate_ids:
        return 0

    print("\n[ERROR] Duplicate id(s)")
    for poi_id, line_numbers in duplicate_ids.items():
        lines = ", ".join(str(line_number) for line_number in line_numbers)
        print(f"- {poi_id}: CSV lines {lines}")
        for line_number, row in rows_by_id[poi_id]:
            name = row.get("name_zh", "")
            category = row.get("category", "")
            print(f"  line {line_number}: name_zh={name}, category={category}")

    return len(duplicate_ids)


def print_empty_ids(rows: list[tuple[int, dict[str, str]]]) -> int:
    empty_id_lines = [
        line_number
        for line_number, row in rows
        if not row.get("id", "")
    ]

    if not empty_id_lines:
        return 0

    print("\n[ERROR] Empty id row(s)")
    print("- CSV lines " + ", ".join(str(line_number) for line_number in empty_id_lines))
    return len(empty_id_lines)


def print_missing_fields(headers: list[str]) -> int:
    missing = [field for field in REQUIRED_FIELDS if field not in headers]
    if not missing:
        return 0

    print("\n[ERROR] Missing required field(s)")
    print("- " + ", ".join(missing))
    return len(missing)


def print_unsupported_categories(
    rows: list[tuple[int, dict[str, str]]],
    valid_categories: set[str],
) -> int:
    if not valid_categories:
        return 0

    unsupported = [
        (line_number, row)
        for line_number, row in rows
        if row.get("category", "") and row.get("category", "") not in valid_categories
    ]

    if not unsupported:
        return 0

    print("\n[ERROR] Unsupported category value(s)")
    for line_number, row in unsupported:
        print(
            f"- line {line_number}: id={row.get('id', '')}, "
            f"category={row.get('category', '')}"
        )
    return len(unsupported)


def print_empty_categories(rows: list[tuple[int, dict[str, str]]]) -> int:
    empty_category_rows = [
        (line_number, row)
        for line_number, row in rows
        if row.get("id", "") and not row.get("category", "")
    ]

    if not empty_category_rows:
        return 0

    print("\n[WARNING] Empty category row(s)")
    for line_number, row in empty_category_rows:
        print(f"- line {line_number}: id={row.get('id', '')}")
    return len(empty_category_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check data/metadata/poi_master.csv and print CSV line numbers."
    )
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER_PATH)
    parser.add_argument("--categories", type=Path, default=DEFAULT_CATEGORY_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    master_path = args.master.resolve()
    category_path = args.categories.resolve()

    try:
        headers, rows = read_csv_rows(master_path)
    except FileNotFoundError:
        print(f"[ERROR] Missing file: {master_path}")
        return 1
    except csv.Error as exc:
        print(f"[ERROR] Invalid CSV: {master_path}: {exc}")
        return 1

    valid_categories = load_categories(category_path)

    print(f"Checking {master_path}")
    error_count = 0
    warning_count = 0
    error_count += print_missing_fields(headers)
    error_count += print_empty_ids(rows)
    error_count += print_duplicate_ids(rows)
    error_count += print_unsupported_categories(rows, valid_categories)
    warning_count += print_empty_categories(rows)

    print("\nSummary")
    print(f"- rows checked: {len(rows)}")
    print(f"- errors: {error_count}")
    print(f"- warnings: {warning_count}")

    if error_count:
        return 1

    print("\nOK: poi_master.csv passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
