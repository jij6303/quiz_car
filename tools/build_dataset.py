"""
cars.json의 "from": "<후보폴더>/<번호>" 항목을 실제 이미지로 확정하는 스크립트

- data/candidates/<폴더>/<번호>.jpg → data/images/<문제id>_<n>.jpg 로 복사
- candidates/meta.json의 출처·작성자·라이선스를 cars.json에 기록
- "from" 키는 제거

사용법:
    python tools/build_dataset.py
    python tools/build_dataset.py --preview out_dir   # 단서 크롭 미리보기 저장
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quiz.imaging import IMAGE_DIR, render_clue  # noqa: E402

DATA = ROOT / "data" / "cars.json"
CANDIDATES = ROOT / "data" / "candidates"


def build():
    cars = json.loads(DATA.read_text(encoding="utf-8"))
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for car in cars:
        for n, image in enumerate(car["images"]):
            src = image.pop("from", None)
            if not src:
                continue
            folder, idx = src.split("/")
            meta = json.loads((CANDIDATES / folder / "meta.json").read_text(encoding="utf-8"))
            info = next(m for m in meta if m["local"] == f"{idx}.jpg")
            file = f"{car['id']}_{n}.jpg"
            shutil.copy(CANDIDATES / folder / info["local"], IMAGE_DIR / file)
            image["file"] = file
            image["source"] = {
                "title": info["title"],
                "page": info["page"],
                "author": info["author"],
                "license": info["license"],
            }
            image.setdefault("blur", [])
    DATA.write_text(json.dumps(cars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cars)}개 문제 확정")


def preview(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for car in json.loads(DATA.read_text(encoding="utf-8")):
        for i, clue in enumerate(car["clues"]):
            render_clue(car["images"][clue["img"]], clue["box"]).save(out / f"{car['id']}_{i}.jpg")
    print(f"미리보기 저장: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", metavar="OUT_DIR")
    args = parser.parse_args()
    if args.preview:
        preview(args.preview)
    else:
        build()
