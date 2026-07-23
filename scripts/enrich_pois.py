#!/usr/bin/env python3
"""Merge SVG-generated POI geometry with manually maintained metadata."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_POIS_PATH = PROJECT_ROOT / "data" / "pois.json"
DEFAULT_MASTER_PATH = PROJECT_ROOT / "data" / "metadata" / "poi_master.csv"
DEFAULT_CATEGORY_PATH = PROJECT_ROOT / "data" / "metadata" / "dictionary.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "pois_enriched.json"

MASTER_REQUIRED_FIELDS = [
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
CATEGORY_REQUIRED_FIELDS = ["category"]
MULTI_VALUE_FIELDS = {"aliases", "faculty_leads", "occupants"}


class ValidationReport:
    def __init__(self) -> None:
        self.info: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def add_info(self, message: str) -> None:
        self.info.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def print(self) -> None:
        print("\nValidation Report")
        print("=================")
        self._print_section("ERROR", self.errors)
        self._print_section("WARNING", self.warnings)
        self._print_section("INFO", self.info)

    @staticmethod
    def _print_section(title: str, messages: list[str]) -> None:
        print(f"\n[{title}]")
        if not messages:
            print("- None")
            return
        for message in messages:
            print(f"- {message}")


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def split_multi_value(value: str) -> list[str]:
    normalized = value.replace("；", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def find_duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if value and count > 1)


def format_list(values: list[str], limit: int = 30) -> str:
    if not values:
        return "None"
    shown = values[:limit]
    suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit} more)"
    return ", ".join(shown) + suffix


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing required file: {relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {relative(path)}: {exc}") from exc


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                return [], [], []

            raw_headers = reader.fieldnames
            headers = [clean_cell(header) for header in raw_headers]
            rows: list[dict[str, str]] = []
            raw_rows: list[dict[str, str]] = []

            for row in reader:
                cleaned_row: dict[str, str] = {}
                raw_row: dict[str, str] = {}
                for raw_header, header in zip(raw_headers, headers):
                    raw_value = row.get(raw_header)
                    cleaned_row[header] = clean_cell(raw_value)
                    raw_row[header] = "" if raw_value is None else str(raw_value)
                rows.append(cleaned_row)
                raw_rows.append(raw_row)

            return headers, rows, raw_rows
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing required file: {relative(path)}") from exc
    except csv.Error as exc:
        raise RuntimeError(f"Invalid CSV in {relative(path)}: {exc}") from exc


def resolve_category_path(requested_path: Path, report: ValidationReport) -> Path:
    if requested_path.exists():
        return requested_path
    raise RuntimeError(f"Missing required file: {relative(requested_path)}")


def validate_required_fields(
    file_label: str,
    headers: list[str],
    required_fields: list[str],
    report: ValidationReport,
) -> None:
    missing = [field for field in required_fields if field not in headers]
    if missing:
        report.add_error(f"{file_label} is missing required CSV field(s): {format_list(missing)}")


def index_master_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["id"]: row for row in rows if row.get("id")}


def normalize_metadata(row: dict[str, str] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    row = row or {}

    for field in MASTER_REQUIRED_FIELDS:
        if field == "id":
            continue
        if field in MULTI_VALUE_FIELDS:
            normalized[field] = split_multi_value(clean_cell(row.get(field)))
        else:
            normalized[field] = clean_cell(row.get(field))

    return normalized


def validate_pois(pois: Any, report: ValidationReport) -> list[dict[str, Any]]:
    if not isinstance(pois, list):
        report.add_error("data/pois.json must contain a JSON array.")
        return []

    clean_pois: list[dict[str, Any]] = []
    ids: list[str] = []
    empty_id_indexes: list[str] = []

    for index, poi in enumerate(pois, start=1):
        if not isinstance(poi, dict):
            report.add_error(f"data/pois.json item #{index} is not an object.")
            continue
        poi_id = clean_cell(poi.get("id"))
        if not poi_id:
            empty_id_indexes.append(str(index))
        else:
            ids.append(poi_id)
        clean_pois.append(poi)

    duplicate_ids = find_duplicate_values(ids)
    if empty_id_indexes:
        report.add_error(f"pois.json has POI item(s) with empty id at index: {format_list(empty_id_indexes)}")
    if duplicate_ids:
        report.add_error(f"pois.json has duplicate id(s): {format_list(duplicate_ids)}")

    return clean_pois


def validate_master(
    headers: list[str],
    rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
    valid_categories: set[str],
    report: ValidationReport,
) -> None:
    error_count = len(report.errors)
    validate_required_fields("poi_master.csv", headers, MASTER_REQUIRED_FIELDS, report)
    if len(report.errors) > error_count:
        return

    ids = [row.get("id", "") for row in rows if row.get("id", "")]
    empty_ids = [str(index) for index, row in enumerate(rows, start=2) if not row.get("id", "")]
    duplicate_ids = find_duplicate_values(ids)
    empty_categories = [row["id"] for row in rows if row.get("id") and not row.get("category")]
    unsupported = sorted(
        {
            f"{row['id']}={row['category']}"
            for row in rows
            if row.get("id") and row.get("category") and row["category"] not in valid_categories
        }
    )
    category_whitespace = sorted(
        {
            f"{row.get('id') or f'line {index}'}={raw_row.get('category', '')}"
            for index, (row, raw_row) in enumerate(zip(rows, raw_rows), start=2)
            if raw_row.get("category", "") != row.get("category", "")
        }
    )

    if empty_ids:
        report.add_error(f"poi_master.csv has row(s) with empty id at CSV line: {format_list(empty_ids)}")
    if duplicate_ids:
        report.add_error(f"poi_master.csv has duplicate id(s): {format_list(duplicate_ids)}")
    if unsupported:
        report.add_error(
            "poi_master.csv has unsupported category value(s): "
            f"{format_list(unsupported)}"
        )
    if empty_categories:
        report.add_warning(f"poi_master.csv row(s) with empty category: {format_list(sorted(empty_categories))}")
    if category_whitespace:
        report.add_warning(
            "poi_master.csv category value(s) had leading/trailing whitespace and were trimmed: "
            f"{format_list(category_whitespace)}"
        )


def load_valid_categories(
    path: Path,
    headers: list[str],
    rows: list[dict[str, str]],
    raw_rows: list[dict[str, str]],
    report: ValidationReport,
) -> set[str]:
    validate_required_fields(relative(path), headers, CATEGORY_REQUIRED_FIELDS, report)
    if "category" not in headers:
        return set()

    raw_categories = [row.get("category", "") for row in raw_rows]
    categories = [row.get("category", "") for row in rows]
    non_empty_categories = [category for category in categories if category]
    duplicate_categories = find_duplicate_values(non_empty_categories)
    blank_lines = [
        str(index)
        for index, category in enumerate(categories, start=2)
        if not category
    ]
    whitespace_categories = sorted(
        {
            f"line {index}: {raw_categories[index - 2]}"
            for index, raw_category in enumerate(raw_categories, start=2)
            if raw_category != categories[index - 2]
        }
    )

    if duplicate_categories:
        report.add_error(
            f"{relative(path)} has duplicate category value(s): {format_list(duplicate_categories)}"
        )
    if blank_lines:
        report.add_warning(
            f"{relative(path)} has blank category value(s) at CSV line: {format_list(blank_lines)}"
        )
    if whitespace_categories:
        report.add_warning(
            f"{relative(path)} category value(s) had leading/trailing whitespace and were trimmed: "
            f"{format_list(whitespace_categories)}"
        )

    return set(non_empty_categories)


def enrich_pois(
    pois: list[dict[str, Any]],
    master_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for poi in pois:
        poi_id = clean_cell(poi.get("id"))
        merged = dict(poi)
        merged.update(normalize_metadata(master_by_id.get(poi_id)))
        enriched.append(merged)
    return enriched


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge data/pois.json with CSV-maintained POI metadata."
    )
    parser.add_argument("--pois", type=Path, default=DEFAULT_POIS_PATH)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER_PATH)
    parser.add_argument("--categories", type=Path, default=DEFAULT_CATEGORY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = ValidationReport()

    pois_path = args.pois.resolve()
    master_path = args.master.resolve()
    output_path = args.output.resolve()

    try:
        category_path = resolve_category_path(args.categories.resolve(), report)
        pois_raw = read_json(pois_path)
        master_headers, master_rows, master_raw_rows = read_csv_rows(master_path)
        category_headers, category_rows, category_raw_rows = read_csv_rows(category_path)
    except RuntimeError as exc:
        report.add_error(str(exc))
        report.add_info(f"Output file not written: {relative(output_path)}")
        report.print()
        return 1

    pois = validate_pois(pois_raw, report)
    valid_categories = load_valid_categories(
        category_path,
        category_headers,
        category_rows,
        category_raw_rows,
        report,
    )
    validate_master(master_headers, master_rows, master_raw_rows, valid_categories, report)

    poi_ids = [clean_cell(poi.get("id")) for poi in pois if clean_cell(poi.get("id"))]
    master_ids = [row.get("id", "") for row in master_rows if row.get("id", "")]
    poi_id_set = set(poi_ids)
    master_id_set = set(master_ids)

    matched_ids = sorted(poi_id_set & master_id_set)
    missing_metadata_ids = sorted(poi_id_set - master_id_set)
    metadata_without_poi_ids = sorted(master_id_set - poi_id_set)

    if missing_metadata_ids:
        report.add_warning(f"pois.json id(s) missing metadata: {format_list(missing_metadata_ids)}")
    if metadata_without_poi_ids:
        report.add_warning(
            f"poi_master.csv id(s) not found in pois.json: {format_list(metadata_without_poi_ids)}"
        )

    report.add_info(f"POI geometry source: {relative(pois_path)}")
    report.add_info(f"POI metadata source: {relative(master_path)}")
    report.add_info(f"Category dictionary source: {relative(category_path)}")
    report.add_info(f"pois.json POI count: {len(pois)}")
    report.add_info(f"poi_master.csv row count: {len(master_rows)}")
    report.add_info(f"Successfully matched POI count: {len(matched_ids)}")
    report.add_info(f"pois.json id(s) without metadata count: {len(missing_metadata_ids)}")
    report.add_info(f"poi_master.csv id(s) without POI count: {len(metadata_without_poi_ids)}")
    report.add_info(f"Allowed category count: {len(valid_categories)}")

    if report.has_errors:
        report.add_info(f"Final output POI count: 0")
        report.add_info(f"Output file not written: {relative(output_path)}")
        report.print()
        print("\nAborted: validation errors must be fixed before writing enriched POI data.")
        return 1

    enriched = enrich_pois(pois, index_master_rows(master_rows))
    write_json(output_path, enriched)

    report.add_info(f"Final output POI count: {len(enriched)}")
    report.add_info(f"Output file written: {relative(output_path)}")
    report.print()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
