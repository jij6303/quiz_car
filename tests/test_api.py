"""API 흐름 검증: 단서/원본 사진 접근 제한

실행: python -m pytest tests
"""
import pytest

from main import CARS, app

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
    for _ in range(len(CARS)):
        client.post("/api/new")
        r = client.post("/api/answer", json={}).get_json()
        for p in r["photos"]:
            assert client.get(f"/api/photo/{p['index']}").data[:2] == JPEG
