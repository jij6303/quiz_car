"""
자동차 부분 사진 퀴즈 — Flask 서버

실행:
    pip install -r requirements.txt
    python main.py
    → http://127.0.0.1:5000

정답(차 id)은 브라우저로 보내지 않고 서버 세션에만 둔다.
단서 이미지도 서버에서 잘라 보내므로 원본 사진(로고 포함)은 노출되지 않는다.
원본 사진은 정답 확인 후에만 /api/photo/<n> 으로 받을 수 있다.
"""
import os

from flask import Flask, abort, jsonify, render_template, request, session

from quiz.game import GAME_LENGTH, grade, history_entry, load_cars, mark, new_question, summary
from quiz.imaging import clue_jpeg, photo_jpeg

app = Flask(__name__)
app.secret_key = os.environ.get("QUIZ_SECRET_KEY") or os.urandom(24)

CARS = load_cars()


def _current():
    cid = session.get("qid")
    if not cid or cid not in CARS:
        abort(400, "진행 중인 문제가 없습니다")
    return CARS[cid]


def _clue_info(car, upto):
    return [{"index": i, "label": c["label"]} for i, c in enumerate(car["clues"][:upto])]


@app.get("/")
def index():
    return render_template("index.html")


def _question_payload(car, question):
    history = session.get("history", [])
    return {
        "round": len(history) + 1,
        "total": GAME_LENGTH,
        "score": sum(h["points"] for h in history),
        "marks": [mark(h) for h in history],
        "clues": _clue_info(car, session.get("revealed", 1)),
        "clue_count": len(car["clues"]),
        "models": question["models"],
        "years": question["years"],
    }


@app.post("/api/game")
def api_game():
    """새 판 시작 (이전 판들에서 본 차는 seen에 남겨 되도록 겹치지 않게)"""
    session.update(history=[], qid=None, question=None, answered=False)
    return jsonify({"ok": True, "total": GAME_LENGTH})


@app.post("/api/new")
def api_new():
    history = session.get("history", [])
    if len(history) >= GAME_LENGTH:
        return jsonify({"error": "game_over"}), 409

    # 답하지 않은 문제가 있으면 그대로 이어서 (새로고침으로 문제 바꾸기 방지)
    if session.get("qid") in CARS and not session.get("answered") and session.get("question"):
        return jsonify(_question_payload(CARS[session["qid"]], session["question"]))

    # 이번 판에서 나온 차는 다시 나오지 않게
    played = {h["id"] for h in history}
    seen = [cid for cid in session.get("seen", []) if cid not in played] + list(played)
    question, seen = new_question(CARS, [cid for cid in seen if cid in CARS])
    while question["id"] in played:  # seen이 한 바퀴 돌아 초기화된 경우
        question, seen = new_question(CARS, seen)

    session.update(qid=question["id"], question=question, seen=seen, revealed=1, answered=False)
    return jsonify(_question_payload(CARS[question["id"]], question))


@app.get("/api/summary")
def api_summary():
    history = session.get("history", [])
    if not history:
        abort(404)
    return jsonify(summary(history))


@app.post("/api/hint")
def api_hint():
    car = _current()
    if not session.get("answered"):
        session["revealed"] = min(session.get("revealed", 1) + 1, len(car["clues"]))
    return jsonify({"clues": _clue_info(car, session["revealed"])})


@app.get("/api/clue/<int:n>")
def api_clue(n):
    car = _current()
    # 정답 공개 후에는 모든 단서를 볼 수 있다
    limit = len(car["clues"]) if session.get("answered") else session.get("revealed", 1)
    if not 0 <= n < limit:
        abort(403)
    clue = car["clues"][n]
    image = car["images"][clue["img"]]
    data = clue_jpeg(image["file"], tuple(map(tuple, image.get("blur", []))), tuple(clue["box"]))
    return data, 200, {"Content-Type": "image/jpeg", "Cache-Control": "no-store"}


@app.get("/api/photo/<int:n>")
def api_photo(n):
    """원본 전체 사진 — 정답 확인 후에만 볼 수 있다"""
    car = _current()
    if not session.get("answered"):
        abort(403)
    if not 0 <= n < len(car["images"]):
        abort(404)
    data = photo_jpeg(car["images"][n]["file"])
    return data, 200, {"Content-Type": "image/jpeg", "Cache-Control": "no-store"}


def _photo_info(car):
    """원본 사진마다 출처와, 그 사진에서 잘라낸 단서 영역 목록"""
    photos = []
    for i, image in enumerate(car["images"]):
        photos.append({
            "index": i,
            "source": image["source"],
            "clues": [{"number": n + 1, "label": c["label"], "box": c["box"]}
                      for n, c in enumerate(car["clues"]) if c["img"] == i],
        })
    return photos


@app.post("/api/answer")
def api_answer():
    car = _current()
    if session.get("answered"):
        abort(409, "이미 답한 문제입니다")
    body = request.get_json(silent=True) or {}
    clues_used = session.get("revealed", 1)
    result = grade(car, body.get("model"), body.get("year"), clues_used)

    history = session.get("history", []) + [history_entry(car, result, body.get("model"), body.get("year"), clues_used)]
    session.update(answered=True, history=history)

    result["round"] = len(history)
    result["total"] = GAME_LENGTH
    result["score"] = sum(h["points"] for h in history)
    result["marks"] = [mark(h) for h in history]
    result["game_over"] = len(history) >= GAME_LENGTH
    result["clues"] = _clue_info(car, len(car["clues"]))
    result["photos"] = _photo_info(car)
    return jsonify(result)


@app.post("/api/reset")
def api_reset():
    session.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
