"""API 흐름 검증: 단서/원본 사진 접근 제한

실행: python -m pytest tests
"""
import pytest

from main import CARS, app
from quiz.game import GAME_LENGTH, MAX_POINTS, rank, summary

JPEG = b"\xff\xd8"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_locked_clues_and_photos_before_answer(client):
    client.post("/api/new")
    assert client.get("/api/clue/0").status_code == 200
    assert client.get("/api/clue/1").status_code == 403
    # 정답 확인 전에는 원본(로고 포함)을 받을 수 없다
    assert client.get("/api/photo/0").status_code == 403


def test_hint_unlocks_next_clue(client):
    client.post("/api/new")
    assert len(client.post("/api/hint").get_json()["clues"]) == 2
    assert client.get("/api/clue/1").status_code == 200


def test_answer_reveals_photos(client):
    q = client.post("/api/new").get_json()
    r = client.post("/api/answer", json={"model": q["models"][0], "year": q["years"][0]}).get_json()

    photos = r["photos"]
    assert photos
    assert sum(len(p["clues"]) for p in photos) == q["clue_count"]
    for p in photos:
        assert p["source"]["license"]
        res = client.get(f"/api/photo/{p['index']}")
        assert res.status_code == 200 and res.data[:2] == JPEG
    assert client.get(f"/api/photo/{len(photos)}").status_code == 404
    # 정답 공개 후에는 모든 단서도 볼 수 있다
    assert client.get(f"/api/clue/{q['clue_count'] - 1}").status_code == 200


def test_cannot_answer_twice(client):
    client.post("/api/new")
    client.post("/api/answer", json={})
    assert client.post("/api/answer", json={}).status_code == 409


def test_new_question_relocks_photos(client):
    client.post("/api/new")
    client.post("/api/answer", json={})
    client.post("/api/new")
    assert client.get("/api/photo/0").status_code == 403


def test_every_car_photo_renders(client):
    """모든 문제를 돌면서 원본 사진이 실제로 나오는지"""
    for i in range(len(CARS)):
        if i % GAME_LENGTH == 0:
            client.post("/api/game")
        client.post("/api/new")
        r = client.post("/api/answer", json={}).get_json()
        for p in r["photos"]:
            assert client.get(f"/api/photo/{p['index']}").data[:2] == JPEG


# ── 한 판(10문제) ─────────────────────────────────────────
def _play_game(client):
    """한 판을 끝까지 푼다 (항상 첫 번째 보기를 고름)"""
    client.post("/api/game")
    last = None
    for _ in range(GAME_LENGTH):
        q = client.post("/api/new").get_json()
        last = client.post("/api/answer", json={"model": q["models"][0], "year": q["years"][0]}).get_json()
    return last


def test_game_has_ten_questions_without_repeats(client):
    client.post("/api/game")
    ids = set()
    for n in range(1, GAME_LENGTH + 1):
        q = client.post("/api/new").get_json()
        assert q["round"] == n and q["total"] == GAME_LENGTH
        r = client.post("/api/answer", json={}).get_json()
        ids.add(r["answer_model"] + r["answer_year"])
        assert r["game_over"] == (n == GAME_LENGTH)
        assert len(r["marks"]) == n
    assert len(ids) == GAME_LENGTH
    # 10문제가 끝나면 새 문제를 받을 수 없다
    assert client.post("/api/new").status_code == 409


def test_summary_after_game(client):
    _play_game(client)
    s = client.get("/api/summary").get_json()
    assert s["played"] == GAME_LENGTH
    assert s["max_score"] == MAX_POINTS * GAME_LENGTH
    assert s["score"] == sum(r["points"] for r in s["rows"])
    assert len(s["marks"]) == GAME_LENGTH
    assert s["share"].startswith(f"이 차는 뭘까? {s['score']}점")


def test_new_game_resets(client):
    _play_game(client)
    client.post("/api/game")
    q = client.post("/api/new").get_json()
    assert q["round"] == 1 and q["score"] == 0 and q["marks"] == []
    assert client.get("/api/summary").status_code == 404


def test_refresh_keeps_same_question(client):
    """답하기 전에 /api/new를 다시 불러도 문제가 바뀌지 않는다"""
    client.post("/api/game")
    a = client.post("/api/new").get_json()
    client.post("/api/hint")
    b = client.post("/api/new").get_json()
    assert a["models"] == b["models"] and a["years"] == b["years"]
    assert b["round"] == 1 and len(b["clues"]) == 2


@pytest.mark.parametrize("score,name", [
    (1500, "카 마스터"), (1300, "카 마스터"), (1299, "자동차 박사"), (1000, "자동차 박사"),
    (700, "좀 아는 사람"), (400, "초보 운전"), (399, "뚜벅이"), (0, "뚜벅이"),
])
def test_rank_boundaries(score, name):
    assert rank(score)["name"] == name


def test_summary_marks():
    rows = [
        {"model_ok": True, "year_ok": True, "points": 150, "clues": 1},
        {"model_ok": True, "year_ok": False, "points": 70, "clues": 2},
        {"model_ok": False, "year_ok": False, "points": 0, "clues": 3},
    ]
    s = summary(rows)
    assert s["marks"] == "🟩🟨⬛"
    assert s["score"] == 220 and s["model_correct"] == 2 and s["year_correct"] == 1 and s["perfect"] == 1
    assert s["avg_clues"] == 2.0
