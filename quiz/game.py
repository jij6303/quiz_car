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


# ── 한 판(10문제) ─────────────────────────────────────────
GAME_LENGTH = 10
MAX_POINTS = MODEL_POINTS + YEAR_POINTS

RANKS = [  # (최소 점수, 등급, 한 줄 평)
    (1300, "카 마스터", "로고 없이도 차가 보이는 경지"),
    (1000, "자동차 박사", "램프 하나로 세대까지 구분하는 눈"),
    (700, "좀 아는 사람", "주차장에서 차 이름 맞히기 가능"),
    (400, "초보 운전", "익숙한 차는 알아보는 정도"),
    (0, "뚜벅이", "다음 판엔 단서를 아껴 보세요"),
]

MARKS = {2: "🟩", 1: "🟨", 0: "⬛"}  # 모델·연식 둘 다 / 하나 / 둘 다 틀림


def rank(score):
    for minimum, name, comment in RANKS:
        if score >= minimum:
            return {"name": name, "comment": comment}
    raise ValueError(score)


def history_entry(car, result, picked_model, picked_year, clues_used):
    return {
        "id": car["id"],
        "model": result["answer_model"],
        "year": result["answer_year"],
        "picked_model": picked_model,
        "picked_year": picked_year,
        "model_ok": result["model_ok"],
        "year_ok": result["year_ok"],
        "clues": clues_used,
        "points": result["points"],
    }


def mark(entry):
    return MARKS[entry["model_ok"] + entry["year_ok"]]


def summary(history):
    total = sum(h["points"] for h in history)
    marks = "".join(mark(h) for h in history)
    r = rank(total)
    return {
        "score": total,
        "max_score": MAX_POINTS * GAME_LENGTH,
        "played": len(history),
        "model_correct": sum(h["model_ok"] for h in history),
        "year_correct": sum(h["year_ok"] for h in history),
        "perfect": sum(h["model_ok"] and h["year_ok"] for h in history),
        "avg_clues": round(sum(h["clues"] for h in history) / len(history), 1) if history else 0,
        "rank": r,
        "marks": marks,
        "share": f"이 차는 뭘까? {total}점 · {r['name']}\n{marks}",
        "rows": history,
    }
