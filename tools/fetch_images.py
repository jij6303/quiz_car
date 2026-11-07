"""
Wikimedia Commons에서 자동차 사진을 내려받는 스크립트

사용법:
    # 검색어로 후보 사진 받기 (data/candidates/<slug>/ 에 저장 + meta.json)
    python tools/fetch_images.py search --slug avante_cn7 --query "Hyundai Avante CN7" --limit 6

    # 특정 파일 하나 받기 (data/images/<slug>.jpg 로 저장, 메타정보 출력)
    python tools/fetch_images.py get --slug avante_cn7 --file "File:2021 Hyundai Elantra.jpg"
"""
import argparse
import json
import re
import time
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "quiz_car/1.0 (educational car quiz project)"}
ROOT = Path(__file__).resolve().parent.parent
THUMB_WIDTH = 1280  # Wikimedia 표준 썸네일 크기
MIN_WIDTH = 1280   # 이보다 작은 사진은 후보에서 제외


def _get(url, **kwargs):
    """429(요청 과다)면 기다렸다가 재시도"""
    for attempt in range(4):
        res = requests.get(url, headers=HEADERS, timeout=60, **kwargs)
        if res.status_code != 429:
            res.raise_for_status()
            time.sleep(1)
            return res
        # Retry-After가 매우 길게 오는 경우가 있어 최대 30초로 제한
        wait = min(int(res.headers.get("Retry-After", 0)) or 5 * (attempt + 1), 30)
        print(f"  429 → {wait}초 대기 후 재시도", flush=True)
        time.sleep(wait)
    res.raise_for_status()


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _imageinfo(titles):
    res = _get(API, params={
        "action": "query",
        "format": "json",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": THUMB_WIDTH,
    })
    pages = res.json().get("query", {}).get("pages", {})
    out = []
    for page in pages.values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata", {})
        out.append({
            "title": page["title"],
            "url": info.get("thumburl") or info["url"],
            "page": info.get("descriptionurl"),
            "author": _strip_html(meta.get("Artist", {}).get("value")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "width": info.get("width", 0),
        })
    return out


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    res = _get(url)
    dest.write_bytes(res.content)


def search(slug, query, limit):
    folder = ROOT / "data" / "candidates" / slug
    if (folder / "meta.json").exists():
        print(f"[{slug}] 이미 받음, 건너뜀")
        return
    res = _get(API, params={
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f"{query} filetype:bitmap",
        "srnamespace": 6,
        "srlimit": limit,
    })
    titles = [r["title"] for r in res.json()["query"]["search"]]
    if not titles:
        print(f"[{slug}] 결과 없음")
        return
    # 저해상도 사진은 단서로 잘라 쓰기 어렵고, 원본 서버에서 429가 잦아 제외
    infos = [info for info in _imageinfo(titles) if info["width"] >= MIN_WIDTH]
    saved = []
    for info in infos:
        name = f"{len(saved)}.jpg"
        try:
            _download(info["url"], folder / name)
        except requests.RequestException as e:
            print(f"  [{slug}] 다운로드 실패, 건너뜀: {info['title']} ({e.__class__.__name__})", flush=True)
            continue
        info["local"] = name
        saved.append(info)
    if not saved:
        print(f"[{slug}] 받은 사진 없음")
        return
    (folder / "meta.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{slug}] {len(saved)}장 저장: {folder}", flush=True)


def get(slug, file_title):
    infos = _imageinfo([file_title])
    if not infos:
        raise SystemExit(f"파일을 찾을 수 없음: {file_title}")
    info = infos[0]
    _download(info["url"], ROOT / "data" / "images" / f"{slug}.jpg")
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wikimedia Commons 자동차 사진 수집")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--slug", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=6)
    g = sub.add_parser("get")
    g.add_argument("--slug", required=True)
    g.add_argument("--file", required=True)
    args = parser.parse_args()
    if args.cmd == "search":
        search(args.slug, args.query, args.limit)
    else:
        get(args.slug, args.file)
