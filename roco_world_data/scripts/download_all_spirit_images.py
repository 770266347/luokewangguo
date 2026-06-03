#!/usr/bin/env python3
import argparse
import csv
import json
import mimetypes
import re
import shutil
import ssl
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def safe_name(text: str) -> str:
    text = INVALID_FILENAME.sub("_", str(text)).strip()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(". ")


def guess_ext(url: str, content_type: str = "") -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in IMAGE_EXTS:
        return ext
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip())
    if guessed and guessed.lower() in IMAGE_EXTS:
        return guessed.lower()
    return ".png"


def build_cache_index(asset_root: Path, output_dir: Path) -> list[Path]:
    if not asset_root.exists():
        return []
    paths = []
    for path in asset_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        try:
            if output_dir in path.parents:
                continue
        except RuntimeError:
            pass
        if path.stat().st_size > 1024:
            paths.append(path)
    return paths


def find_cached_image(cache_paths: list[Path], number: str, name: str) -> Path | None:
    number = str(number)
    name = str(name)
    patterns = [
        lambda p: f"_{number}_" in p.name and name in p.stem,
        lambda p: f"_{number}_" in p.name,
        lambda p: p.stem.startswith(f"{number}_") and name in p.stem,
        lambda p: p.stem.startswith(f"{number}_"),
        lambda p: name and name in p.stem,
    ]
    for matcher in patterns:
        for path in cache_paths:
            if matcher(path):
                return path
    return None


def download_image(url: str, output_path: Path) -> tuple[bool, str]:
    if not url:
        return False, "missing image_url"
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://wiki.biligame.com/rocom/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    context = ssl.create_default_context()
    with urlopen(req, timeout=60, context=context) as resp:
        content = resp.read()
        ext = guess_ext(url, resp.headers.get("Content-Type", ""))
    if len(content) <= 1024:
        return False, f"download too small: {len(content)}"
    final_path = output_path.with_suffix(ext)
    final_path.write_bytes(content)
    return True, str(final_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=r"E:\luokewangguo\roco_world_data\data\roco_world_spirits.json")
    parser.add_argument("--out", default=r"E:\luokewangguo\roco_world_data\data\spirit_images")
    parser.add_argument("--asset-root", default=r"E:\luokewangguo\roco_world_data\assets\spirits")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.08)
    args = parser.parse_args()

    data_path = Path(args.data)
    output_dir = Path(args.out)
    asset_root = Path(args.asset_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(data_path.read_text(encoding="utf-8"))
    cache_paths = build_cache_index(asset_root, output_dir)
    rows = []
    copied = 0
    downloaded = 0
    existing = 0
    failed = []

    for item in data:
        number = str(item.get("number") or "").zfill(3)
        name = item.get("display_name") or item.get("name") or "未命名"
        filename_stem = safe_name(f"{number}_{name}")
        existing_file = next((output_dir / f"{filename_stem}{ext}" for ext in IMAGE_EXTS if (output_dir / f"{filename_stem}{ext}").exists()), None)

        source = ""
        final_path = existing_file
        if final_path and final_path.stat().st_size > 1024 and not args.force:
            existing += 1
            source = "existing"
        else:
            if final_path and args.force:
                final_path.unlink()
            cached = find_cached_image(cache_paths, number, str(name))
            if cached:
                final_path = output_dir / f"{filename_stem}{cached.suffix.lower()}"
                shutil.copy2(cached, final_path)
                copied += 1
                source = f"cache:{cached.parent.name}"
            else:
                target = output_dir / f"{filename_stem}.png"
                try:
                    ok, result = download_image(item.get("image_url") or "", target)
                    if ok:
                        final_path = Path(result)
                        downloaded += 1
                        source = "download"
                        time.sleep(args.sleep)
                    else:
                        failed.append((number, name, result))
                except (URLError, OSError, TimeoutError, Exception) as exc:
                    failed.append((number, name, str(exc)))

        rows.append(
            {
                "number": number,
                "name": name,
                "file": str(final_path) if final_path else "",
                "source": source,
                "image_url": item.get("image_url") or "",
                "source_url": item.get("source_url") or "",
            }
        )

    index_path = output_dir / "_index.csv"
    with index_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["number", "name", "file", "source", "image_url", "source_url"])
        writer.writeheader()
        writer.writerows(rows)

    report_path = output_dir / "_download_report.json"
    report = {
        "total": len(data),
        "existing": existing,
        "copied_from_cache": copied,
        "downloaded": downloaded,
        "failed_count": len(failed),
        "failed": [{"number": n, "name": name, "error": err} for n, name, err in failed],
        "index": str(index_path),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
