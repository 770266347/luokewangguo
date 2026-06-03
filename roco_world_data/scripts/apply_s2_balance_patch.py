#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path


FIELDS = [
    "number", "name", "variant", "display_name", "detail_status", "attributes",
    "stats_total", "hp", "physical_attack", "magic_attack", "physical_defense",
    "magic_defense", "speed", "skills", "bloodline_skills", "skill_stone_skills",
    "evolution_chain", "obtain_method",
    "trait_name", "trait_description", "image_url", "source_url", "source_updated_at",
]


PATCH_SOURCE = "2026-05-18-s2-balance-followup"
SOURCE_URLS = [
    "https://www.vgover.com/news/215636",
    "https://www.youxiabc.com/p/45197.html",
]
PATCHES = {
    "皇家狮鹫（高山地的样子）": {
        "hp": 109,
        "magic_attack": 59,
        "physical_defense": 123,
        "magic_defense": 70,
    },
    "皇家狮鹫（崖间地的样子）": {
        "hp": 107,
        "magic_attack": 69,
        "physical_defense": 127,
        "magic_defense": 65,
    },
    "高脚鹬": {
        "hp": 96,
        "physical_attack": 98,
        "magic_attack": 98,
    },
    "锤头鹳": {
        "hp": 128,
        "physical_attack": 77,
        "magic_attack": 75,
        "physical_defense": 101,
        "magic_defense": 81,
    },
    "遁地鼠（枯水期的样子）": {
        "physical_defense": 121,
        "magic_defense": 85,
    },
    "遁地鼠（储水期的样子）": {
        "hp": 112,
        "magic_attack": 23,
        "physical_defense": 85,
        "magic_defense": 131,
    },
    "梦悠悠（穿旧睡衣的样子）": {
        "hp": 105,
        "physical_attack": 60,
        "magic_attack": 110,
        "physical_defense": 85,
        "magic_defense": 116,
    },
    "叮叮恶魔": {
        "hp": 125,
        "magic_attack": 70,
        "physical_defense": 89,
        "magic_defense": 69,
    },
    "彩蝶鲨": {
        "hp": 115,
        "physical_attack": 101,
        "magic_attack": 101,
        "physical_defense": 125,
        "magic_defense": 125,
    },
    "神谕鲨": {
        "hp": 115,
        "physical_attack": 101,
        "magic_attack": 101,
        "physical_defense": 125,
        "magic_defense": 125,
    },
    "黑猫巫师": {
        "hp": 149,
        "physical_attack": 53,
        "magic_attack": 124,
        "physical_defense": 90,
        "magic_defense": 129,
    },
    "黑猫密探": {
        "hp": 149,
        "physical_attack": 65,
        "magic_attack": 118,
        "physical_defense": 90,
        "magic_defense": 129,
    },
    "寒音蛇（本来的样子）": {
        "hp": 141,
        "physical_attack": 89,
        "magic_attack": 89,
        "physical_defense": 90,
    },
    "九幽菇": {
        "hp": 131,
        "physical_attack": 72,
        "magic_attack": 65,
        "physical_defense": 107,
        "magic_defense": 103,
    },
    "窃光蚊": {
        "physical_attack": 113,
        "magic_attack": 113,
        "physical_defense": 71,
        "magic_defense": 125,
    },
    "圆号鱼": {
        "hp": 113,
        "physical_attack": 31,
    },
    "武者鸡": {
        "hp": 105,
        "physical_attack": 132,
        "magic_attack": 98,
        "magic_defense": 88,
    },
    "绅士鸡": {
        "hp": 100,
        "physical_attack": 122,
        "magic_attack": 122,
        "physical_defense": 100,
        "magic_defense": 99,
    },
    "仪式巨像": {
        "hp": 113,
        "physical_attack": 83,
        "magic_attack": 88,
        "physical_defense": 93,
        "magic_defense": 91,
    },
    "祭礼巨像": {
        "hp": 115,
        "physical_attack": 98,
        "magic_attack": 102,
        "physical_defense": 100,
        "magic_defense": 99,
    },
    "古啦多": {
        "hp": 98,
        "physical_attack": 65,
        "magic_attack": 65,
        "physical_defense": 142,
        "magic_defense": 138,
    },
    "龙鱼": {
        "hp": 77,
        "physical_attack": 131,
        "magic_attack": 113,
        "physical_defense": 122,
        "magic_defense": 106,
    },
    "爵士鹿": {
        "physical_attack": 77,
        "magic_attack": 20,
    },
    "波普鹿": {
        "physical_attack": 79,
        "magic_attack": 21,
    },
    "幻影荆棘": {
        "hp": 121,
        "physical_attack": 74,
        "magic_attack": 74,
        "magic_defense": 138,
    },
}

TRAIT_PATCHES = {
    "寂灭骨龙": "力竭4回合后复活。",
    "落陨星兔": "在场时，双方回合结束时触发的效果触发次数-1；不影响天气效果。",
}


def safe_name(value):
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    return value[:120].rstrip(" .") or "unknown"


def to_int(value, fallback=0):
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def recompute_total(row):
    stat_fields = [
        "hp", "physical_attack", "magic_attack",
        "physical_defense", "magic_defense", "speed",
    ]
    row["stats_total"] = sum(to_int(row.get(field)) for field in stat_fields)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["attributes"] = json.dumps(item.get("attributes") or [], ensure_ascii=False)
            item["skills"] = json.dumps(item.get("skills") or [], ensure_ascii=False)
            item["bloodline_skills"] = json.dumps(item.get("bloodline_skills") or [], ensure_ascii=False)
            item["skill_stone_skills"] = json.dumps(item.get("skill_stone_skills") or [], ensure_ascii=False)
            writer.writerow({field: item.get(field) for field in FIELDS})


def rebuild_spirit_files(rows, spirits_dir):
    used = {}
    for row in rows:
        number = row.get("number") or "000"
        display_name = row.get("display_name") or row.get("name") or "unknown"
        base = safe_name(f"{number}_{display_name}")
        count = used.get(base, 0)
        used[base] = count + 1
        filename = f"{base}.json" if count == 0 else f"{base}_{count + 1}.json"
        (spirits_dir / filename).write_text(
            json.dumps(row, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def main():
    root = Path(__file__).resolve().parents[1]
    json_path = root / "data" / "roco_world_spirits.json"
    csv_path = root / "data" / "roco_world_spirits.csv"
    spirits_dir = root / "data" / "spirits"
    report_path = root / "data" / "s2_balance_patch_report.json"

    rows = json.loads(json_path.read_text(encoding="utf-8"))
    by_display = {
        row.get("display_name") or row.get("name"): row
        for row in rows
    }

    changed = []
    missing = []

    for display_name, patch in PATCHES.items():
        row = by_display.get(display_name)
        if not row:
            missing.append(display_name)
            continue
        before = {field: row.get(field) for field in patch}
        before["stats_total"] = row.get("stats_total")
        for field, value in patch.items():
            row[field] = value
        recompute_total(row)
        row["source_updated_at"] = PATCH_SOURCE
        changed.append({
            "display_name": display_name,
            "before": before,
            "after": {
                **{field: row.get(field) for field in patch},
                "stats_total": row.get("stats_total"),
            },
        })

    trait_changed = []
    for display_name, description in TRAIT_PATCHES.items():
        row = by_display.get(display_name)
        if not row:
            missing.append(display_name)
            continue
        before = row.get("trait_description")
        row["trait_description"] = description
        row["source_updated_at"] = PATCH_SOURCE
        trait_changed.append({
            "display_name": display_name,
            "before": before,
            "after": description,
        })

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    rebuild_spirit_files(rows, spirits_dir)

    report = {
        "source": PATCH_SOURCE,
        "source_urls": SOURCE_URLS,
        "stat_patch_count": len(changed),
        "trait_patch_count": len(trait_changed),
        "missing": missing,
        "changed": changed,
        "trait_changed": trait_changed,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
