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

from quiz.game import grade, load_cars, new_question
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


@app.post("/api/new")
def api_new():
    question, seen = new_question(CARS, session.get("seen", []))
    session.update(qid=question["id"], seen=seen, revealed=1, answered=False, round=session.get("round", 0) + 1)
    car = CARS[question["id"]]
    return jsonify({
        "round": session["round"],
        "total": len(CARS),
        "clues": _clue_info(car, 1),
        "clue_count": len(car["clues"]),
        "models": question["models"],
        "years": question["years"],
    })


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
    result = grade(car, body.get("model"), body.get("year"), session.get("revealed", 1))
    session["answered"] = True
    session["score"] = session.get("score", 0) + result["points"]
    result["score"] = session["score"]
    result["clues"] = _clue_info(car, len(car["clues"]))
    result["photos"] = _photo_info(car)
    return jsonify(result)


@app.post("/api/reset")
def api_reset():
    session.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
