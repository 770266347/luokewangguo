#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from pathlib import Path

import scrape_bwiki_rocom as bwiki


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def safe_name(value):
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    return value[:120].rstrip(" .") or "unknown"


def rebuild_spirit_files(rows, spirits_dir):
    spirits_dir.mkdir(parents=True, exist_ok=True)
    for old in spirits_dir.glob("*.json"):
        old.unlink()

    used = {}
    for row in rows:
        number = row.get("number") or "000"
        display_name = row.get("display_name") or row.get("name") or "unknown"
        base = safe_name(f"{number}_{display_name}")
        count = used.get(base, 0)
        used[base] = count + 1
        filename = f"{base}.json" if count == 0 else f"{base}_{count + 1}.json"
        (spirits_dir / filename).write_text(
            json.dumps(bwiki.order_record(row), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def key_for(row):
    return (str(row.get("number") or ""), row.get("display_name") or row.get("name") or "")


def main():
    parser = argparse.ArgumentParser(description="Incrementally update spirit details from a fresh BWiki index.")
    parser.add_argument("--index", default="data/roco_world_index.json")
    parser.add_argument("--old", default="data/roco_world_spirits.json")
    parser.add_argument("--out", default="data/roco_world_spirits.json")
    parser.add_argument("--index-out", default="data/roco_world_index.json")
    parser.add_argument("--csv-out", default="data/roco_world_spirits.csv")
    parser.add_argument("--report", default="data/s2_update_report.json")
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--refresh-incomplete", action="store_true", help="Refetch rows whose detail_status is not detail.")
    parser.add_argument("--drop-missing-old", action="store_true", help="Drop old rows that are missing from the fresh index.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    index_path = root / args.index
    old_path = root / args.old

    index_rows = json.loads(index_path.read_text(encoding="utf-8"))
    old_rows = json.loads(old_path.read_text(encoding="utf-8"))
    old_by_key = {key_for(row): row for row in old_rows}

    rows = []
    added = []
    kept = 0
    failed = []
    seen_keys = set()

    for idx, item in enumerate(index_rows, 1):
        key = key_for(item)
        seen_keys.add(key)
        old = old_by_key.get(key)
        if old:
            if args.refresh_incomplete and old.get("detail_status") != "detail":
                print(f"[refresh] [{idx}/{len(index_rows)}] {item.get('number')} {item.get('display_name')}", file=sys.stderr)
                try:
                    row = bwiki.extract_detail(item["name"], url=item.get("url"), index_item=item)
                    rows.append(bwiki.order_record(row))
                    added.append({
                        "number": row.get("number"),
                        "display_name": row.get("display_name"),
                        "source_url": row.get("source_url"),
                        "refreshed": True,
                    })
                except Exception as exc:
                    fallback = dict(old)
                    fallback["error"] = str(exc)
                    rows.append(bwiki.order_record(fallback))
                    failed.append({
                        "number": item.get("number"),
                        "display_name": item.get("display_name"),
                        "source_url": item.get("url"),
                        "error": str(exc),
                    })
                time.sleep(args.sleep)
                continue
            row = dict(old)
            row.setdefault("image_url", item.get("image_url"))
            row.setdefault("source_url", item.get("url"))
            rows.append(bwiki.order_record(row))
            kept += 1
            continue

        print(f"[new {len(added) + 1}] [{idx}/{len(index_rows)}] {item.get('number')} {item.get('display_name')}", file=sys.stderr)
        try:
            row = bwiki.extract_detail(item["name"], url=item.get("url"), index_item=item)
            rows.append(bwiki.order_record(row))
            added.append({
                "number": row.get("number"),
                "display_name": row.get("display_name"),
                "source_url": row.get("source_url"),
            })
        except Exception as exc:
            fallback = bwiki.index_only_detail(item)
            fallback["detail_status"] = "index_only_error"
            fallback["error"] = str(exc)
            rows.append(bwiki.order_record(fallback))
            failed.append({
                "number": item.get("number"),
                "display_name": item.get("display_name"),
                "source_url": item.get("url"),
                "error": str(exc),
            })
        time.sleep(args.sleep)

    preserved_missing_old = []
    if not args.drop_missing_old:
        for key, old in old_by_key.items():
            if key in seen_keys:
                continue
            rows.append(bwiki.order_record(dict(old)))
            preserved_missing_old.append({
                "number": old.get("number"),
                "display_name": old.get("display_name") or old.get("name"),
                "source_url": old.get("source_url"),
            })
            index_rows.append({
                "number": old.get("number"),
                "name": old.get("name"),
                "variant": old.get("variant"),
                "display_name": old.get("display_name") or old.get("name"),
                "attributes": old.get("attributes") or [],
                "image_url": old.get("image_url"),
                "url": old.get("source_url"),
            })

    out_path = root / args.out
    index_out_path = root / args.index_out
    csv_out_path = root / args.csv_out
    report_path = root / args.report

    index_out_path.write_text(json.dumps(index_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    bwiki.write_csv(csv_out_path, rows)
    rebuild_spirit_files(rows, root / "data" / "spirits")

    report = {
        "old_count": len(old_rows),
        "index_count": len(index_rows),
        "new_detail_count": len(added),
        "kept_count": kept,
        "preserved_missing_old_count": len(preserved_missing_old),
        "failed_count": len(failed),
        "added": added,
        "preserved_missing_old": preserved_missing_old,
        "failed": failed,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
