"""문제 데이터(cars.json)와 보기 생성 검증

실행: python -m pytest tests
"""
import random

import pytest

from quiz.game import load_cars, model_choices, new_question, year_choices, year_label
from quiz.imaging import IMAGE_DIR

CARS = load_cars()


def test_enough_questions():
    assert len(CARS) >= 40


@pytest.mark.parametrize("cid", sorted(CARS))
def test_car_entry(cid):
    car = CARS[cid]
    assert car["model"].strip()

    start, end = car["years"]
    assert 1950 <= start <= 2026
    assert end is None or start < end

    assert car["images"], "이미지가 없음"
    for image in car["images"]:
        assert "from" not in image, "build_dataset.py를 실행하지 않음"
        assert (IMAGE_DIR / image["file"]).exists()
        source = image["source"]
        assert source["page"].startswith("https://commons.wikimedia.org/")
        assert source["license"]
        for box in image.get("blur", []):
            _check_box(box)

    assert len(car["clues"]) == 3
    for clue in car["clues"]:
        assert 0 <= clue["img"] < len(car["images"])
        assert clue["label"].strip()
        _check_box(clue["box"])


def _check_box(box):
    x0, y0, x1, y1 = box
    assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, box
    assert (x1 - x0) >= 0.05 and (y1 - y0) >= 0.05, f"영역이 너무 작음: {box}"


def test_unique_answers():
    """모델명+연식 조합이 겹치면 정답이 두 개가 된다"""
    keys = [(c["model"], year_label(c["years"])) for c in CARS.values()]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("cid", sorted(CARS))
def test_choices(cid):
    car = CARS[cid]
    rng = random.Random(cid)
    models = model_choices(CARS, car, rng)
    years = year_choices(CARS, car, rng)
    assert len(models) == len(set(models)) == 4 and car["model"] in models
    assert len(years) == len(set(years)) == 4 and year_label(car["years"]) in years


def test_new_question_cycles_without_repeats():
    seen, ids = [], []
    for _ in range(len(CARS)):
        q, seen = new_question(CARS, seen)
        ids.append(q["id"])
    assert sorted(ids) == sorted(CARS)
