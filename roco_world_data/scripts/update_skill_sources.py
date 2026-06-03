#!/usr/bin/env python3
import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 roco-world-data-recorder/1.0"
SECTION_FIELDS = {
    "精灵技能": "skills",
    "血脉技能": "bloodline_skills",
    "可学技能石": "skill_stone_skills",
}
RECORD_FIELDS = [
    "number", "name", "variant", "display_name", "detail_status", "attributes",
    "stats_total", "hp", "physical_attack", "magic_attack", "physical_defense",
    "magic_defense", "speed", "skills", "bloodline_skills", "skill_stone_skills",
    "evolution_chain", "obtain_method", "trait_name", "trait_description",
    "image_url", "source_url", "source_updated_at",
]
ATTRIBUTE_NAMES = {
    "普通", "草", "火", "水", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        value = html.unescape(data).strip().replace("\xa0", "")
        if value:
            self.parts.append(value)


def fragment_text(value):
    parser = TextParser()
    parser.feed(value or "")
    return "".join(parser.parts).strip()


def fetch(url, timeout=60, retries=4):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404 or attempt == retries:
                raise
            wait = min(90, 10 * (attempt + 1))
            print(f"HTTP {exc.code} for {url}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
        except URLError as exc:
            if attempt == retries:
                raise
            wait = min(60, 6 * (attempt + 1))
            print(f"network error for {url}: {exc}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)


def parse_int(value):
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def first_div_text(chunk, class_name):
    match = re.search(
        r'<div class="[^"]*\b' + re.escape(class_name) + r'\b[^"]*"[^>]*>(.*?)</div>',
        chunk,
        flags=re.S,
    )
    return fragment_text(match.group(1)) if match else None


def parse_skill_box(chunk):
    level = first_div_text(chunk, "rocom_sprite_skill_level")
    name = first_div_text(chunk, "rocom_sprite_skillName")
    cost = first_div_text(chunk, "rocom_sprite_skillDamage")
    category = first_div_text(chunk, "rocom_sprite_skillType")
    power = first_div_text(chunk, "rocom_sprite_skill_power")
    description = first_div_text(chunk, "rocom_sprite_skillContent")

    attributes = []
    for attr in re.findall(r'alt="图标 宠物 属性 ([^".]+)\.png"', chunk):
        attr = html.unescape(attr)
        if attr in ATTRIBUTE_NAMES and attr not in attributes:
            attributes.append(attr)

    if not name:
        return None

    if level and level.startswith("LV"):
        level = level.replace("LV", "")
    else:
        level = level or None

    return {
        "level": level,
        "name": name,
        "attributes": attributes,
        "cost": parse_int(cost),
        "category": category,
        "power": parse_int(power),
        "description": description,
    }


def dedupe_skills(skills):
    result = []
    seen = set()
    for skill in skills:
        key = json.dumps(skill, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(skill)
    return result


def skill_sort_key(skill):
    level = skill.get("level")
    try:
        level_value = int(level)
    except (TypeError, ValueError):
        level_value = 9999
    return (
        level_value,
        skill.get("name") or "",
        ",".join(skill.get("attributes") or []),
        skill.get("category") or "",
        skill.get("cost") if skill.get("cost") is not None else 9999,
        skill.get("power") if skill.get("power") is not None else 9999,
    )


def sort_skills(row):
    row["skills"] = sorted(row.get("skills") or [], key=skill_sort_key)
    row["bloodline_skills"] = sorted(row.get("bloodline_skills") or [], key=skill_sort_key)
    row["skill_stone_skills"] = sorted(row.get("skill_stone_skills") or [], key=skill_sort_key)


def order_record(row):
    ordered = {}
    for field in RECORD_FIELDS:
        if field in row:
            ordered[field] = row[field]
    for field, value in row.items():
        if field not in ordered:
            ordered[field] = value
    return ordered


def parse_bwiki_skill_sections(raw_html):
    sections = {field: [] for field in SECTION_FIELDS.values()}
    tabs = list(re.finditer(r'<div class="tabbertab" title="([^"]+)">', raw_html))

    for index, tab in enumerate(tabs):
        title = html.unescape(tab.group(1))
        field = SECTION_FIELDS.get(title)
        if not field:
            continue

        start = tab.end()
        end = tabs[index + 1].start() if index + 1 < len(tabs) else len(raw_html)
        block = raw_html[start:end]
        chunks = block.split('<div class="rocom_sprite_skill_box">')[1:]
        for chunk in chunks:
            skill = parse_skill_box(chunk)
            if skill:
                sections[field].append(skill)

    for field, skills in sections.items():
        sections[field] = sorted(dedupe_skills(skills), key=skill_sort_key)
    return sections


def safe_name(value):
    value = value.strip()
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
        (spirits_dir / filename).write_text(json.dumps(order_record(row), ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    data_path = root / "data" / "roco_world_spirits.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))

    updated = 0
    failed = []
    for index, row in enumerate(rows, 1):
        if row.get("detail_status") != "detail":
            row.setdefault("bloodline_skills", [])
            row.setdefault("skill_stone_skills", [])
            continue

        url = row.get("source_url")
        print(f"[{index}/{len(rows)}] {row.get('number')} {row.get('display_name')}", file=sys.stderr)
        try:
            sections = parse_bwiki_skill_sections(fetch(url))
        except Exception as exc:
            failed.append({
                "number": row.get("number"),
                "display_name": row.get("display_name"),
                "source_url": url,
                "error": str(exc),
            })
            row.setdefault("bloodline_skills", [])
            row.setdefault("skill_stone_skills", [])
            continue

        row["skills"] = sections["skills"]
        row["bloodline_skills"] = sections["bloodline_skills"]
        row["skill_stone_skills"] = sections["skill_stone_skills"]
        sort_skills(row)
        updated += 1
        time.sleep(0.35)

    rows = [order_record(row) for row in rows]
    data_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    rebuild_spirit_files(rows, root / "data" / "spirits")

    report_path = root / "data" / "skill_source_update_report.json"
    report_path.write_text(json.dumps({"updated": updated, "failed": failed}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated={updated} failed={len(failed)} report={report_path}")


if __name__ == "__main__":
    main()
