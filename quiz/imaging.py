"""문제 이미지 처리: 로고 영역 블러 → 단서 영역 크롭"""
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter

IMAGE_DIR = Path(__file__).resolve().parent.parent / "data" / "images"
MAX_SIDE = 900  # 클라이언트로 보내는 단서 이미지 최대 변 길이


def _to_px(box, size):
    w, h = size
    x0, y0, x1, y1 = box
    return int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)


def blur_regions(img, regions):
    """정규화 좌표(0~1) 영역들을 강하게 블러 처리 (휠 센터캡 로고 등)"""
    for box in regions:
        px = _to_px(box, img.size)
        patch = img.crop(px)
        radius = max(patch.size) / 4
        img.paste(patch.filter(ImageFilter.GaussianBlur(radius)), px)
    return img


def render_clue(image_meta, box):
    """원본 → 블러 → 크롭 → 리사이즈한 PIL 이미지 반환"""
    img = Image.open(IMAGE_DIR / image_meta["file"]).convert("RGB")
    blur_regions(img, image_meta.get("blur", []))
    clue = img.crop(_to_px(box, img.size))
    clue.thumbnail((MAX_SIDE, MAX_SIDE))
    if max(clue.size) < 480:  # 너무 작은 크롭은 보기 좋게 확대
        scale = 480 / max(clue.size)
        clue = clue.resize((int(clue.width * scale), int(clue.height * scale)), Image.LANCZOS)
    return clue


@lru_cache(maxsize=128)
def clue_jpeg(file, blur, box):
    """캐시 가능한 형태(튜플)로 받아 JPEG 바이트 반환"""
    meta = {"file": file, "blur": [list(b) for b in blur]}
    buf = io.BytesIO()
    render_clue(meta, list(box)).save(buf, "JPEG", quality=88)
    return buf.getvalue()
