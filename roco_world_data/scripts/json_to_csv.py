#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


FIELDS = [
    "number", "name", "variant", "display_name", "detail_status", "attributes",
    "stats_total", "hp", "physical_attack", "magic_attack", "physical_defense",
    "magic_defense", "speed", "skills", "bloodline_skills", "skill_stone_skills",
    "evolution_chain", "obtain_method",
    "trait_name", "trait_description", "image_url", "source_url", "source_updated_at",
]


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: py -3 json_to_csv.py input.json output.csv")

    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    rows = json.loads(source.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["attributes"] = json.dumps(item.get("attributes") or [], ensure_ascii=False)
            item["skills"] = json.dumps(item.get("skills") or [], ensure_ascii=False)
            item["bloodline_skills"] = json.dumps(item.get("bloodline_skills") or [], ensure_ascii=False)
            item["skill_stone_skills"] = json.dumps(item.get("skill_stone_skills") or [], ensure_ascii=False)
            writer.writerow({field: item.get(field) for field in FIELDS})

    print(f"saved {len(rows)} rows: {target}")


if __name__ == "__main__":
    main()
