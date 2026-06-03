#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

import scrape_bwiki_rocom as bwiki


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def key_for(row):
    return (str(row.get("number") or ""), row.get("display_name") or row.get("name") or "")


def main():
    parser = argparse.ArgumentParser(description="Refresh incomplete spirit details in-place.")
    parser.add_argument("--data", default="data/roco_world_spirits.json")
    parser.add_argument("--index", default="data/roco_world_index.json")
    parser.add_argument("--csv-out", default="data/roco_world_spirits.csv")
    parser.add_argument("--min-number", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.25)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    data_path = root / args.data
    index_path = root / args.index
    csv_path = root / args.csv_out
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    index_rows = json.loads(index_path.read_text(encoding="utf-8"))
    index_by_key = {key_for(row): row for row in index_rows}

    updated = []
    failed = []
    for pos, row in enumerate(rows):
        try:
            number = int(row.get("number") or 0)
        except ValueError:
            number = 0
        if number < args.min_number or row.get("detail_status") == "detail":
            continue

        key = key_for(row)
        item = index_by_key.get(key)
        if not item:
            continue

        print(f"[refresh] {row.get('number')} {row.get('display_name')}", flush=True)
        try:
            detail = bwiki.extract_detail(item["name"], url=item.get("url"), index_item=item)
            rows[pos] = bwiki.order_record(detail)
            updated.append({
                "number": detail.get("number"),
                "display_name": detail.get("display_name"),
                "source_url": detail.get("source_url"),
            })
            data_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            failed.append({
                "number": row.get("number"),
                "display_name": row.get("display_name"),
                "source_url": item.get("url"),
                "error": str(exc),
            })
            print(f"FAILED {row.get('number')} {row.get('display_name')}: {exc}", file=sys.stderr, flush=True)
        time.sleep(args.sleep)

    bwiki.write_csv(csv_path, rows)
    report_path = root / "data" / "refresh_incomplete_details_report.json"
    report_path.write_text(json.dumps({"updated": updated, "failed": failed}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated={len(updated)} failed={len(failed)}")


if __name__ == "__main__":
    main()
