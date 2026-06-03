#!/usr/bin/env python3
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


ATTRIBUTE_NAMES = {
    "普通", "草", "火", "水", "光", "地", "冰", "龙", "电", "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"
}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []

    def handle_data(self, data):
        value = html.unescape(data).strip()
        if value:
            self.text.append(value)


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_text(raw):
    parser = TextParser()
    parser.feed(raw)
    return parser.text


def meta_image(raw):
    match = re.search(r'<meta property="og:image" content="([^"]+)"', raw)
    return html.unescape(match.group(1)) if match else None


def rocodex_detail(rocodex_id, source_url):
    url = f"https://rocodex.org/zh/pokedex/{rocodex_id}/"
    raw = fetch(url)
    lines = parse_text(raw)

    no_idx = next(i for i, x in enumerate(lines) if re.fullmatch(r"No\.\d{3,}", x))
    number = lines[no_idx].replace("No.", "")
    name = lines[no_idx + 1]
    attributes = []
    for value in lines[no_idx + 3:no_idx + 12]:
        if value in ATTRIBUTE_NAMES and value not in attributes:
            attributes.append(value)
    stats_total = None
    if "总计:" in lines:
        i = lines.index("总计:")
        if i + 1 < len(lines) and lines[i + 1].isdigit():
            stats_total = int(lines[i + 1])

    trait_name = trait_description = None
    if "特性" in lines:
        i = lines.index("特性")
        if i + 2 < len(lines):
            trait_name = lines[i + 1]
            trait_description = lines[i + 2]

    evolution_chain = None
    if "进化链" in lines and "属性克制" in lines:
        start = lines.index("进化链") + 1
        end = lines.index("属性克制")
        evolution_chain = " / ".join(lines[start:end])

    skills = []
    if "技能名称" in lines:
        start = lines.index("技能名称") + 5
        end = lines.index("精灵简介") if "精灵简介" in lines else len(lines)
        i = start
        while i + 5 < end:
            name_value = lines[i]
            attr = lines[i + 1]
            category = lines[i + 2]
            cost = lines[i + 3]
            power = lines[i + 4]
            desc = lines[i + 5]
            if attr not in ATTRIBUTE_NAMES or category not in {"物攻", "魔攻", "状态", "防御"}:
                i += 1
                continue
            skills.append({
                "level": None,
                "name": name_value,
                "attributes": [attr],
                "cost": None if cost == "-" else int(cost) if cost.isdigit() else cost,
                "category": category,
                "power": None if power == "-" else int(power) if power.isdigit() else power,
                "description": desc,
                "source": "RocoDex",
            })
            i += 6

    return {
        "number": number,
        "name": name,
        "variant": None,
        "display_name": name,
        "detail_status": "rocodex_fallback",
        "attributes": attributes,
        "stats_total": stats_total,
        "hp": None,
        "physical_attack": None,
        "magic_attack": None,
        "physical_defense": None,
        "magic_defense": None,
        "speed": None,
        "skills": skills,
        "evolution_chain": evolution_chain,
        "obtain_method": None,
        "trait_name": trait_name,
        "trait_description": trait_description,
        "image_url": meta_image(raw),
        "source_url": source_url,
        "fallback_source_url": url,
        "source_updated_at": None,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    data_path = root / "data" / "roco_world_spirits.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))

    patch_names = ["喵呜", "魔力猫", "火花", "焰火", "波波拉"]
    patches = {}
    for name in patch_names:
        path = root / "data" / f"patch_{name}.json"
        if path.exists():
            item = json.loads(path.read_text(encoding="utf-8"))
            patches[(item["number"], item["name"])] = item

    fallback = {
        ("007", "火神"): rocodex_detail(9, "https://wiki.biligame.com/rocom/%E7%81%AB%E7%A5%9E"),
        ("008", "水蓝蓝"): rocodex_detail(11, "https://wiki.biligame.com/rocom/%E6%B0%B4%E8%93%9D%E8%93%9D"),
        ("147", "灵狐"): rocodex_detail(233, "https://wiki.biligame.com/rocom/%E7%81%B5%E7%8B%90"),
    }

    replaced = 0
    for index, row in enumerate(rows):
        key = (row.get("number"), row.get("name"))
        if row.get("error") and key in patches:
            rows[index] = patches[key]
            replaced += 1
        elif row.get("error") and key in fallback:
            rows[index] = fallback[key]
            replaced += 1

    data_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"merged {replaced} patches into {data_path}")


if __name__ == "__main__":
    main()
