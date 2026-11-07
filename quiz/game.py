"""퀴즈 데이터 로딩, 보기 생성, 채점"""
import datetime
import json
import random
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cars.json"

MODEL_POINTS = 100
YEAR_POINTS = 50
HINT_PENALTY = 0.3  # 단서를 하나 더 볼 때마다 30%씩 감점


def load_cars(path=DATA_PATH):
    cars = json.loads(Path(path).read_text(encoding="utf-8"))
    return {car["id"]: car for car in cars}


def year_label(years):
    start, end = years
    return f"{start}–{end}" if end else f"{start}–현재"


def model_choices(cars, car, rng, n=4):
    others = sorted({c["model"] for c in cars.values()} - {car["model"]})
    picks = rng.sample(others, min(n - 1, len(others))) + [car["model"]]
    rng.shuffle(picks)
    return picks


def year_choices(cars, car, rng, n=4):
    correct = year_label(car["years"])
    this_year = datetime.date.today().year
    start, end = car["years"]
    length = (end or this_year) - start

    # 같은 모델의 다른 세대가 있으면 가장 헷갈리는 보기로 우선 사용
    pool = [year_label(c["years"]) for c in cars.values()
            if c["model"] == car["model"] and c["id"] != car["id"]]
    shifts = [-3, 3, -6, 6, -9, -12]
    rng.shuffle(shifts)
    for d in shifts:
        s = start + d
        e = s + length
        if e > this_year or s < 1950:
            continue
        pool.append(year_label([s, None if e == this_year else e]))

    distractors = []
    for label in pool:
        if label != correct and label not in distractors:
            distractors.append(label)
    picks = distractors[:n - 1] + [correct]
    # 연도순으로 정렬해서 보여준다
    return sorted(picks, key=lambda label: int(label[:4]))


def score(model_ok, year_ok, clues_used):
    factor = max(0.1, 1 - HINT_PENALTY * (clues_used - 1))
    return round((MODEL_POINTS * model_ok + YEAR_POINTS * year_ok) * factor)


def new_question(cars, seen, rng=random):
    """아직 안 본 문제 중 하나를 랜덤으로 고른다. 다 봤으면 처음부터."""
    remaining = [cid for cid in cars if cid not in seen]
    if not remaining:
        seen = []
        remaining = list(cars)
    cid = rng.choice(remaining)
    car = cars[cid]
    return {
        "id": cid,
        "models": model_choices(cars, car, rng),
        "years": year_choices(cars, car, rng),
    }, seen + [cid]


def grade(car, model, year, clues_used):
    model_ok = model == car["model"]
    year_ok = year == year_label(car["years"])
    return {
        "model_ok": model_ok,
        "year_ok": year_ok,
        "answer_model": car["model"],
        "answer_year": year_label(car["years"]),
        "points": score(model_ok, year_ok, clues_used),
        "credits": [img["source"] for img in car["images"]],
    }
