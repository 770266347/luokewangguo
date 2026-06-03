#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


API_URL = "https://wiki.biligame.com/rocom/api.php"
USER_AGENT = "Mozilla/5.0 roco-world-data-recorder/1.0"


def safe_name(value):
    value = (value or "").strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    return value[:120].rstrip(" .") or "unknown"


def skill_names(rows):
    names = set()
    for row in rows:
        for field in ("skills", "bloodline_skills", "skill_stone_skills"):
            for skill in row.get(field) or []:
                name = skill.get("name")
                if name:
                    names.add(name)
    return sorted(names)


def chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def fetch_json(url, timeout=60, retries=4):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt == retries:
                raise
            time.sleep(min(30, 3 * (attempt + 1)))


def query_image_urls(skill_batch):
    titles = [f"文件:技能图标 {name}.png" for name in skill_batch]
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    data = fetch_json(API_URL + "?" + urlencode(params), timeout=60)
    result = {}
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        title = page.get("title") or ""
        match = re.match(r"文件:技能图标 (.+)\.png$", title)
        if not match or "missing" in page:
            continue
        infos = page.get("imageinfo") or []
        if infos and infos[0].get("url"):
            result[match.group(1)] = {
                "image_url": infos[0]["url"],
                "description_url": infos[0].get("descriptionurl"),
            }
    return result


def query_image_urls_resilient(skill_batch):
    try:
        return query_image_urls(skill_batch)
    except Exception as exc:
        if len(skill_batch) <= 1:
            print(f"imageinfo failed for {skill_batch[0]}: {exc}", file=sys.stderr, flush=True)
            return {}
        mid = len(skill_batch) // 2
        result = {}
        result.update(query_image_urls_resilient(skill_batch[:mid]))
        time.sleep(0.5)
        result.update(query_image_urls_resilient(skill_batch[mid:]))
        return result


def download(url, path, timeout=60, retries=4):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return len(data)
        except Exception:
            if attempt == retries:
                raise
            time.sleep(min(30, 3 * (attempt + 1)))


def main():
    parser = argparse.ArgumentParser(description="Fast download skill icons via MediaWiki imageinfo API.")
    parser.add_argument("--data", default="data/roco_world_spirits.json")
    parser.add_argument("--out-dir", default="assets/skills")
    parser.add_argument("--manifest", default="assets/skills/skill_icons_manifest.csv")
    parser.add_argument("--report", default="assets/skills/skill_icons_report.json")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    rows = json.loads((root / args.data).read_text(encoding="utf-8"))
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    names = skill_names(rows)

    manifest = []
    failed = []
    existing = 0
    downloaded = 0

    for batch_index, batch in enumerate(chunks(names, args.batch_size), 1):
        print(f"[batch {batch_index}] {batch[0]} ... {batch[-1]}", flush=True)
        info_by_name = query_image_urls_resilient(batch)
        for name in batch:
            local = out_dir / f"{safe_name(name)}.png"
            if local.exists() and not args.force:
                existing += 1
                info = info_by_name.get(name) or {}
                manifest.append({
                    "skill_name": name,
                    "local_file": local.name,
                    "source_url": info.get("description_url") or f"https://wiki.biligame.com/rocom/文件:技能图标_{name}.png",
                    "image_url": info.get("image_url") or "",
                    "status": "existing",
                })
                continue

            info = info_by_name.get(name)
            if not info:
                failed.append({"skill_name": name, "error": "imageinfo missing"})
                manifest.append({
                    "skill_name": name,
                    "local_file": "",
                    "source_url": f"https://wiki.biligame.com/rocom/文件:技能图标_{name}.png",
                    "image_url": "",
                    "status": "failed",
                    "error": "imageinfo missing",
                })
                continue

            try:
                size = download(info["image_url"], local)
                downloaded += 1
                manifest.append({
                    "skill_name": name,
                    "local_file": local.name,
                    "source_url": info.get("description_url") or "",
                    "image_url": info["image_url"],
                    "status": "downloaded",
                    "bytes": size,
                })
            except Exception as exc:
                failed.append({"skill_name": name, "error": str(exc)})
                manifest.append({
                    "skill_name": name,
                    "local_file": "",
                    "source_url": info.get("description_url") or "",
                    "image_url": info.get("image_url") or "",
                    "status": "failed",
                    "error": str(exc),
                })
        time.sleep(args.sleep)

    manifest_path = root / args.manifest
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["skill_name", "local_file", "source_url", "image_url", "status", "bytes", "error"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in manifest:
            writer.writerow({field: row.get(field, "") for field in fields})

    report = {
        "total_skills": len(names),
        "existing": existing,
        "downloaded": downloaded,
        "available": existing + downloaded,
        "failed_count": len(failed),
        "failed": failed,
    }
    (root / args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
