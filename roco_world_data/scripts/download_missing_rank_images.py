#!/usr/bin/env python3
import argparse
import csv
import json
import re
import ssl
import time
from pathlib import Path
from urllib.request import Request, urlopen


INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(text: str) -> str:
    return INVALID.sub("_", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--cache", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    url_by_key = {}
    for item in data:
        name = item.get("display_name") or item.get("name") or ""
        key = (str(item.get("number") or ""), name)
        url_by_key[key] = item.get("image_url") or ""

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context()
    done = 0
    failed = []

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rank = int(row["rank"])
            number = str(row["number"])
            name = row["name"]
            out = cache / safe_name(f"{rank:02d}_{number}_{name}.png")
            if out.exists() and out.stat().st_size > 1024:
                continue

            url = url_by_key.get((number, name)) or row.get("image_url") or ""
            if not url:
                failed.append(name)
                continue

            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://wiki.biligame.com/rocom/",
                },
            )
            try:
                with urlopen(req, timeout=60, context=context) as resp:
                    content = resp.read()
                if len(content) <= 1024:
                    raise RuntimeError(f"too small: {len(content)}")
                out.write_bytes(content)
                done += 1
                time.sleep(0.08)
            except Exception as exc:
                failed.append(f"{name}: {exc}")

    print(f"downloaded={done}")
    if failed:
        print(f"failed={len(failed)}")
        for item in failed[:50]:
            print(item)
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
