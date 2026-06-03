#!/usr/bin/env python3
import argparse
import csv
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import scrape_bwiki_rocom as bwiki


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


USER_AGENT = "Mozilla/5.0 roco-world-data-recorder/1.0"


def safe_name(value):
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    return value[:120].rstrip(" .") or "unknown"


def original_image_url(url):
    if not url or "/thumb/" not in url:
        return url
    prefix, rest = url.split("/thumb/", 1)
    parts = rest.split("/")
    if len(parts) >= 4:
        return prefix + "/" + "/".join(parts[:3])
    return url


def abs_url(url):
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://wiki.biligame.com" + url
    return url


def skill_names(rows):
    names = set()
    for row in rows:
        for field in ("skills", "bloodline_skills", "skill_stone_skills"):
            for skill in row.get(field) or []:
                name = skill.get("name")
                if name:
                    names.add(name)
    return sorted(names)


def image_candidates(raw):
    for match in re.finditer(r"<img[^>]+>", raw):
        tag = match.group(0)
        alt_match = re.search(r'alt="([^"]*)"', tag)
        src_match = re.search(r'(?:src|data-src)="([^"]*)"', tag)
        if not src_match:
            continue
        alt = html.unescape(alt_match.group(1)) if alt_match else ""
        src = html.unescape(src_match.group(1))
        yield alt, original_image_url(abs_url(src))


def find_skill_icon(raw, skill_name):
    fallback = None
    for alt, src in image_candidates(raw):
        if "技能图标" in src:
            fallback = fallback or src
        if alt == skill_name:
            return src
        if skill_name in alt and ("技能图标" in alt or "技能图标" in src):
            return src
    return fallback


def download(url, path, timeout=60, retries=4):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return len(data)
        except (HTTPError, URLError) as exc:
            if attempt == retries:
                raise
            wait = min(60, 4 * (attempt + 1))
            print(f"download retry {attempt + 1}: {url} ({exc})", file=sys.stderr)
            time.sleep(wait)


def ext_from_url(url):
    name = Path(urlparse(url).path).name
    suffix = Path(name).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp"} else ".png"


def main():
    parser = argparse.ArgumentParser(description="Download all skill icons referenced by spirit skill data.")
    parser.add_argument("--data", default="data/roco_world_spirits.json")
    parser.add_argument("--out-dir", default="assets/skills")
    parser.add_argument("--manifest", default="assets/skills/skill_icons_manifest.csv")
    parser.add_argument("--report", default="assets/skills/skill_icons_report.json")
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / args.data).read_text(encoding="utf-8"))
    out_dir = root / args.out_dir
    manifest_path = root / args.manifest
    report_path = root / args.report
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    failed = []
    names = skill_names(rows)
    for index, name in enumerate(names, 1):
        page = f"https://wiki.biligame.com/rocom/{quote(name)}"
        base = safe_name(name)
        existing = next(out_dir.glob(base + ".*"), None)
        if existing and not args.force:
            manifest.append({
                "skill_name": name,
                "local_file": existing.name,
                "source_url": page,
                "image_url": "",
                "status": "existing",
            })
            continue

        print(f"[{index}/{len(names)}] {name}", flush=True)
        try:
            raw = bwiki.fetch(page, timeout=45, retries=3)
            image_url = find_skill_icon(raw, name)
            if not image_url:
                raise RuntimeError("skill icon not found")
            target = out_dir / (base + ext_from_url(image_url))
            size = download(image_url, target)
            manifest.append({
                "skill_name": name,
                "local_file": target.name,
                "source_url": page,
                "image_url": image_url,
                "status": "downloaded",
                "bytes": size,
            })
        except Exception as exc:
            failed.append({"skill_name": name, "source_url": page, "error": str(exc)})
            manifest.append({
                "skill_name": name,
                "local_file": "",
                "source_url": page,
                "image_url": "",
                "status": "failed",
                "error": str(exc),
            })
            print(f"FAILED {name}: {exc}", file=sys.stderr, flush=True)
        time.sleep(args.sleep)

    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["skill_name", "local_file", "source_url", "image_url", "status", "bytes", "error"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in manifest:
            writer.writerow({field: row.get(field, "") for field in fields})

    report = {
        "total_skills": len(names),
        "downloaded_or_existing": sum(1 for row in manifest if row.get("status") in {"downloaded", "existing"}),
        "failed_count": len(failed),
        "failed": failed,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
