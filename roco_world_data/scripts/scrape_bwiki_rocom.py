#!/usr/bin/env python3
import argparse
import csv
import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://wiki.biligame.com"
WIKI_ROOT = "https://wiki.biligame.com/rocom"
INDEX_URL = f"{WIKI_ROOT}/{quote('精灵图鉴')}"
USER_AGENT = "Mozilla/5.0 roco-world-data-recorder/1.0"
STAT_LABELS = {
    "生命": "hp",
    "物攻": "physical_attack",
    "魔攻": "magic_attack",
    "物防": "physical_defense",
    "魔防": "magic_defense",
    "速度": "speed",
}
ATTRIBUTE_NAMES = {
    "普通", "草", "火", "水", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"
}
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


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.links = []
        self.images = []
        self._link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self._link = {"href": attrs.get("href"), "title": attrs.get("title"), "text": ""}
        elif tag == "img":
            self.images.append({
                "src": attrs.get("src") or attrs.get("data-src"),
                "alt": attrs.get("alt"),
            })

    def handle_endtag(self, tag):
        if tag == "a" and self._link:
            if self._link.get("href"):
                self.links.append(self._link)
            self._link = None

    def handle_data(self, data):
        value = html.unescape(data).strip()
        if not value:
            return
        self.text.append(value)
        if self._link is not None:
            self._link["text"] += value


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        value = html.unescape(data).strip().replace("\xa0", "")
        if value:
            self.parts.append(value)


def fetch(url, timeout=60, retries=5):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                raise
            if exc.code not in {429, 500, 502, 503, 504, 567} or attempt == retries:
                raise
            wait = min(90, 8 * (attempt + 1))
            print(f"HTTP {exc.code} for {url}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
        except URLError:
            if attempt == retries:
                raise
            wait = min(60, 5 * (attempt + 1))
            print(f"network error for {url}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)


def parse_page(raw_html):
    parser = PageParser()
    parser.feed(raw_html)
    lines = [x.strip() for x in parser.text if x.strip()]
    return parser, lines


def fragment_text(value):
    parser = TextParser()
    parser.feed(value or "")
    return "".join(parser.parts).strip()


def abs_url(url):
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    return urljoin(BASE_URL, url)


def page_url(name):
    return f"{WIKI_ROOT}/{quote(name)}"


def extract_index():
    raw = fetch(INDEX_URL)
    cards = re.findall(r'<div class="divsort"[^>]*>.*?(?=<div class="divsort"|<noscript>|$)', raw, flags=re.S)
    items = []
    seen = set()

    for card in cards:
        number_match = re.search(r"NO\.(\d{3,})", card)
        link_match = re.search(r'<a href="([^"]+)" title="([^"]+)"', card)
        image_match = re.search(r'<img(?=[^>]*class="[^"]*\brocom_prop_icon\b)[^>]*>', card)
        if not number_match or not link_match:
            continue

        title = html.unescape(link_match.group(2))
        name, variant = split_title(title)
        attributes = sorted(set(re.findall(r"图标_宠物_属性_([^./_]+)\.png", unquote(card))))
        item = {
            "number": number_match.group(1),
            "name": name,
            "variant": variant,
            "display_name": f"{name}（{variant}）" if variant else name,
            "attributes": attributes,
            "image_url": extract_image_url(image_match.group(0)) if image_match else None,
            "url": abs_url(html.unescape(link_match.group(1))),
        }
        key = (item["number"], item["display_name"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    if items:
        return items

    parser, _ = parse_page(raw)
    fallback = []
    current_number = None
    for link in parser.links:
        text = (link.get("text") or "").strip()
        href = link.get("href") or ""
        if re.fullmatch(r"NO\.\d{3,}", text):
            current_number = text.replace("NO.", "")
            continue
        if current_number and href.startswith("/rocom/") and text and not text.startswith("NO."):
            fallback.append({
                "number": current_number,
                "name": text,
                "variant": None,
                "display_name": text,
                "attributes": [],
                "image_url": None,
                "url": abs_url(href),
            })
            current_number = None
    return fallback


def split_title(title):
    match = re.fullmatch(r"(.+?)（(.+?)）", title)
    if not match:
        return title, None
    return match.group(1), match.group(2)


def extract_image_url(img_tag):
    srcset_match = re.search(r'\ssrcset="([^"]+)"', img_tag)
    if srcset_match:
        candidates = [part.strip().split(" ")[0] for part in html.unescape(srcset_match.group(1)).split(",")]
        if candidates:
            return original_image_url(abs_url(candidates[-1]))

    src_match = re.search(r'\ssrc="([^"]+)"', img_tag)
    if src_match:
        return original_image_url(abs_url(html.unescape(src_match.group(1))))
    return None


def original_image_url(url):
    if not url or "/thumb/" not in url:
        return url
    prefix, rest = url.split("/thumb/", 1)
    parts = rest.split("/")
    if len(parts) >= 4:
        return prefix + "/" + "/".join(parts[:3])
    return url


def first_meta_image(raw):
    match = re.search(r'<meta\s+itemprop="image"\s+content="([^"]+)"', raw)
    return html.unescape(match.group(1)) if match else None


def first_detail_image(raw):
    match = re.search(r'<img(?=[^>]*class="[^"]*\brocom_prop_icon\b)[^>]*>', raw)
    return extract_image_url(match.group(0)) if match else None


def find_updated_at(lines):
    for i, line in enumerate(lines):
        if line == "更新日期：" and i + 1 < len(lines):
            return lines[i + 1]
        match = re.search(r"(\d{4}-\d{2}-\d{2})\s*更新", line)
        if match:
            return match.group(1)
    return None


def find_identity(lines, fallback_name):
    for line in lines:
        match = re.fullmatch(r"(\d{3,})\s+(.+)", line)
        if match:
            return match.group(1), match.group(2).strip()
    return None, fallback_name


def parse_int(value):
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def extract_stats(lines):
    stats = {
        "stats_total": None,
        "hp": None,
        "physical_attack": None,
        "magic_attack": None,
        "physical_defense": None,
        "magic_defense": None,
        "speed": None,
    }
    try:
        start = lines.index("种族值")
    except ValueError:
        return stats

    window = lines[start:start + 80]
    if len(window) > 1:
        stats["stats_total"] = parse_int(window[1])

    for i, line in enumerate(window):
        field = STAT_LABELS.get(line)
        if field and i + 1 < len(window):
            stats[field] = parse_int(window[i + 1])
    return stats


def extract_attributes(lines):
    number_index = next((i for i, x in enumerate(lines) if re.fullmatch(r"\d{3,}\s+.+", x)), None)
    if number_index is None:
        return []
    attrs = []
    for line in lines[number_index + 1:number_index + 12]:
        if line in ATTRIBUTE_NAMES and line not in attrs:
            attrs.append(line)
    return attrs


def extract_obtain(lines):
    for line in lines:
        if line.startswith("精灵分布:"):
            return line.split(":", 1)[1].strip()
    return None


def extract_trait(lines):
    try:
        start = lines.index("特性")
    except ValueError:
        return None, None

    try:
        end = lines.index("精灵属性", start)
    except ValueError:
        end = min(start + 8, len(lines))

    values = [x for x in lines[start + 1:end] if x not in {"无"}]
    if not values:
        return None, None
    return values[0], " ".join(values[1:]).strip() or None


def extract_evolution(lines):
    try:
        start = lines.index("进化链")
    except ValueError:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i] in {"克制表", "LV1"}), len(lines))
    block = [x for x in lines[start + 1:end] if x not in {"进化条件:"}]
    return " / ".join(block).strip() or None


def extract_skills(lines):
    skills = []
    skill_level_positions = [(i, line) for i, line in enumerate(lines) if re.fullmatch(r"LV\d+", line)]
    for pos, level in skill_level_positions:
        chunk = lines[pos + 1:pos + 12]
        if len(chunk) < 5:
            continue
        attrs = [x for x in chunk[:3] if x in ATTRIBUTE_NAMES]
        name = next((x for x in chunk if x not in ATTRIBUTE_NAMES and not x.isdigit() and x not in {"物攻", "魔攻", "状态"}), None)
        category = next((x for x in chunk if x in {"物攻", "魔攻", "状态"}), None)
        numbers = [parse_int(x) for x in chunk if re.fullmatch(r"\d+", x)]
        description = next((x for x in chunk if x.startswith("✦")), None)
        if not name:
            continue
        skills.append({
            "level": level.replace("LV", ""),
            "name": name,
            "attributes": attrs,
            "cost": numbers[0] if numbers else None,
            "category": category,
            "power": numbers[1] if len(numbers) > 1 else None,
            "description": description,
        })
    return skills


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


def extract_detail(name, url=None, index_item=None):
    url = url or page_url(name)
    try:
        raw = fetch(url)
    except HTTPError as exc:
        if exc.code == 404 and index_item:
            return index_only_detail(index_item)
        raise
    _, lines = parse_page(raw)
    number, page_name = find_identity(lines, name)
    trait_name, trait_description = extract_trait(lines)
    skill_sections = parse_bwiki_skill_sections(raw)
    index_attrs = (index_item or {}).get("attributes") or []
    index_image = (index_item or {}).get("image_url")
    detail = {
        "number": number or (index_item or {}).get("number"),
        "name": page_name,
        "variant": (index_item or {}).get("variant"),
        "display_name": (index_item or {}).get("display_name") or page_name,
        "detail_status": "detail",
        "attributes": extract_attributes(lines) or index_attrs,
        **extract_stats(lines),
        "skills": skill_sections["skills"] or extract_skills(lines),
        "bloodline_skills": skill_sections["bloodline_skills"],
        "skill_stone_skills": skill_sections["skill_stone_skills"],
        "evolution_chain": extract_evolution(lines),
        "obtain_method": extract_obtain(lines),
        "trait_name": trait_name,
        "trait_description": trait_description,
        "image_url": first_detail_image(raw) or index_image or first_meta_image(raw),
        "source_url": url,
        "source_updated_at": find_updated_at(lines),
    }
    return order_record(detail)


def index_only_detail(index_item):
    return order_record({
        "number": index_item.get("number"),
        "name": index_item.get("name"),
        "variant": index_item.get("variant"),
        "display_name": index_item.get("display_name") or index_item.get("name"),
        "detail_status": "index_only",
        "attributes": index_item.get("attributes") or [],
        "stats_total": None,
        "hp": None,
        "physical_attack": None,
        "magic_attack": None,
        "physical_defense": None,
        "magic_defense": None,
        "speed": None,
        "skills": [],
        "bloodline_skills": [],
        "skill_stone_skills": [],
        "evolution_chain": None,
        "obtain_method": None,
        "trait_name": None,
        "trait_description": None,
        "image_url": index_item.get("image_url"),
        "source_url": index_item.get("url"),
        "source_updated_at": None,
    })


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, list):
        data = [order_record(row) for row in data]
    elif isinstance(data, dict):
        data = order_record(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "number", "name", "variant", "display_name", "detail_status", "attributes", "stats_total", "hp", "physical_attack", "magic_attack",
        "physical_defense", "magic_defense", "speed", "skills", "bloodline_skills", "skill_stone_skills", "evolution_chain", "obtain_method",
        "trait_name", "trait_description", "image_url", "source_url", "source_updated_at"
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["attributes"] = json.dumps(item.get("attributes") or [], ensure_ascii=False)
            item["skills"] = json.dumps(item.get("skills") or [], ensure_ascii=False)
            item["bloodline_skills"] = json.dumps(item.get("bloodline_skills") or [], ensure_ascii=False)
            item["skill_stone_skills"] = json.dumps(item.get("skill_stone_skills") or [], ensure_ascii=False)
            writer.writerow({field: item.get(field) for field in fields})


def cmd_index(args):
    data = extract_index()
    write_json(args.out, data)
    print(f"saved {len(data)} index rows: {args.out}")


def cmd_detail(args):
    data = extract_detail(args.name)
    write_json(args.out, data)
    print(f"saved detail: {args.out}")


def cmd_all(args):
    items = extract_index()
    if args.limit:
        items = items[:args.limit]

    rows = []
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['number']} {item['name']}", file=sys.stderr)
        try:
            rows.append(extract_detail(item["name"], url=item.get("url"), index_item=item))
        except Exception as exc:
            rows.append({
                "number": item.get("number"),
                "name": item.get("name"),
                "source_url": item.get("url"),
                "error": str(exc),
            })
        time.sleep(args.sleep)

    if args.format == "csv":
        write_csv(args.out, rows)
    else:
        write_json(args.out, rows)
    print(f"saved {len(rows)} detail rows: {args.out}")


def build_parser():
    parser = argparse.ArgumentParser(description="Scrape Roco Kingdom World spirit data from BWiki.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index")
    p_index.add_argument("--out", default="data/roco_world_index.json")
    p_index.set_defaults(func=cmd_index)

    p_detail = sub.add_parser("detail")
    p_detail.add_argument("name")
    p_detail.add_argument("--out", default="data/spirit_detail.json")
    p_detail.set_defaults(func=cmd_detail)

    p_all = sub.add_parser("all")
    p_all.add_argument("--out", default="data/roco_world_spirits.json")
    p_all.add_argument("--format", choices=("json", "csv"), default="json")
    p_all.add_argument("--limit", type=int)
    p_all.add_argument("--sleep", type=float, default=0.5)
    p_all.set_defaults(func=cmd_all)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
