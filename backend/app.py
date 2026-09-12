import json
import os
import random
from pathlib import Path

from flask import Flask, jsonify, request, session, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
QUESTIONS_PATH = BASE_DIR / "questions.json"
STATS_PATH = BASE_DIR / "wrong_stats.json"

# ---- CONFIG ----------------------------------------------------------
# Change this to your own access code before deploying.
# Rule of thumb enforced by the frontend: 8+ chars, includes a special char.
ACCESS_CODE = os.environ.get("FCP_QUIZ_ACCESS_CODE", "Sushi2026!Auckland")
SECRET_KEY = os.environ.get("FCP_QUIZ_SECRET_KEY", "dev-secret-change-me")
# ------------------------------------------------------------------------

app = Flask(__name__, static_folder=None)
app.secret_key = SECRET_KEY


def load_questions():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_stats():
    if STATS_PATH.exists():
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(stats):
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def require_auth():
    return session.get("authed") is True


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    if code == ACCESS_CODE:
        session["authed"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "코드가 올바르지 않습니다 / Incorrect code"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/categories", methods=["GET"])
def categories():
    if not require_auth():
        return jsonify({"error": "unauthorized"}), 401
    questions = load_questions()
    cats = sorted(set(q["category"] for q in questions))
    return jsonify({"categories": cats})


def build_option_set(question):
    """Pick 3 random distractors + the correct answer, shuffle order."""
    lang_pairs = list(zip(question["distractor_pool_en"], question["distractor_pool_ko"]))
    chosen = random.sample(lang_pairs, k=min(3, len(lang_pairs)))
    options = [
        {"text_en": en, "text_ko": ko, "correct": False} for en, ko in chosen
    ]
    options.append(
        {"text_en": question["correct_en"], "text_ko": question["correct_ko"], "correct": True}
    )
    random.shuffle(options)
    return options


@app.route("/api/quiz", methods=["GET"])
def quiz():
    if not require_auth():
        return jsonify({"error": "unauthorized"}), 401

    category = request.args.get("category")
    count = int(request.args.get("count", 10))

    questions = load_questions()
    if category and category != "all":
        questions = [q for q in questions if q["category"] == category]

    stats = load_stats()

    # Weighted random: questions answered wrong more often get picked more often.
    weights = []
    for q in questions:
        wrong = stats.get(q["id"], {}).get("wrong", 0)
        weights.append(1 + wrong * 2)

    count = min(count, len(questions))
    if count == 0:
        return jsonify({"questions": []})

    # weighted sample without replacement
    pool = list(zip(questions, weights))
    selected = []
    for _ in range(count):
        total = sum(w for _, w in pool)
        r = random.uniform(0, total)
        upto = 0
        for i, (q, w) in enumerate(pool):
            upto += w
            if upto >= r:
                selected.append(q)
                pool.pop(i)
                break

    payload = []
    for q in selected:
        payload.append(
            {
                "id": q["id"],
                "category": q["category"],
                "text_en": q["text_en"],
                "text_ko": q["text_ko"],
                "options": build_option_set(q),
                "explanation_en": q["explanation_en"],
                "explanation_ko": q["explanation_ko"],
                "fcp_reference": q["fcp_reference"],
            }
        )

    return jsonify({"questions": payload})


@app.route("/api/report", methods=["POST"])
def report():
    if not require_auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    qid = data.get("question_id")
    correct = data.get("correct", True)
    if not qid:
        return jsonify({"ok": False}), 400

    stats = load_stats()
    entry = stats.setdefault(qid, {"wrong": 0, "seen": 0})
    entry["seen"] += 1
    if not correct:
        entry["wrong"] += 1
    save_stats(stats)
    return jsonify({"ok": True})


# ---- Serve frontend ------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
