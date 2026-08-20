"""
Review Service — Bastos Explorer (Phase 2)
==========================================
Owns ONLY reviews.json. Demonstrates synchronous inter-service REST
communication (the slide's "Synchronous: REST APIs for request-response"):
before accepting a new review it calls place-service's internal endpoint to
confirm the place actually exists, rather than trusting the client's place_id.

Design patterns: Singleton (store.py), Repository (ReviewRepository),
Decorator (login_required), Factory (create_app()).
"""
import os
from functools import wraps

import jwt
import requests
from flask import Flask, request, jsonify, g

from store import JSONStore

SECRET_KEY = os.environ.get("BASTOS_SECRET_KEY", "dev-secret-change-me")
PLACE_SERVICE_URL = os.environ.get("PLACE_SERVICE_URL", "http://127.0.0.1:5002")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class ReviewRepository:
    def __init__(self):
        self.store = JSONStore.instance(os.path.join(DATA_DIR, "reviews.json"))

    def find_all(self):
        return self.store.read()

    def find_by_place(self, place_id):
        return [r for r in self.find_all() if r.get("place_id") == place_id]

    def find_by_places(self, place_ids):
        ids = set(place_ids)
        return [r for r in self.find_all() if r.get("place_id") in ids]

    def add(self, row):
        data = self.find_all()
        row["id"] = self.store.next_id(data)
        data.append(row)
        self.store.write(data)
        return row


review_repo = ReviewRepository()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentification requise."}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expirée."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Jeton invalide."}), 401
        g.current_user = {"id": payload["sub"], "username": payload["username"]}
        return view_func(*args, **kwargs)
    return wrapper


def place_exists(place_id):
    """Synchronous call to place-service — real inter-service communication."""
    try:
        res = requests.get(f"{PLACE_SERVICE_URL}/internal/places/{place_id}/exists", timeout=3)
        return res.ok and res.json().get("exists", False)
    except requests.RequestException:
        # place-service unreachable — fail safe rather than silently accepting
        # a review for a place we can't confirm exists.
        return False


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def create_app():
    app = Flask(__name__)
    app.after_request(_cors)

    @app.before_request
    def preflight():
        if request.method == "OPTIONS":
            return _cors(app.make_default_options_response())

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "review-service"})

    @app.get("/places/<int:place_id>/reviews")
    @login_required
    def list_reviews(place_id):
        return jsonify(review_repo.find_by_place(place_id))

    @app.post("/places/<int:place_id>/reviews")
    @login_required
    def add_review(place_id):
        if not place_exists(place_id):
            return jsonify({"error": "Lieu introuvable (service des lieux injoignable ou id invalide)."}), 404

        body = request.get_json(silent=True) or {}
        rating = body.get("rating")
        comment = (body.get("comment") or "").strip()
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            return jsonify({"error": "La note doit être comprise entre 1 et 5."}), 400
        if not comment:
            return jsonify({"error": "Le commentaire ne peut pas être vide."}), 400

        review = review_repo.add({
            "place_id": place_id,
            "username": g.current_user["username"],
            "rating": rating,
            "comment": comment,
        })
        return jsonify(review), 201

    # Batch summary endpoint — lets the gateway attach {rating, review_count}
    # to a whole page of listings in ONE call instead of one call per place.
    @app.get("/reviews/summary")
    @login_required
    def reviews_summary():
        raw_ids = request.args.get("place_ids", "")
        try:
            ids = [int(x) for x in raw_ids.split(",") if x.strip()]
        except ValueError:
            return jsonify({"error": "place_ids invalide."}), 400
        reviews = review_repo.find_by_places(ids)
        summary = {}
        for pid in ids:
            place_reviews = [r for r in reviews if r["place_id"] == pid]
            if place_reviews:
                avg = sum(r["rating"] for r in place_reviews) / len(place_reviews)
                summary[pid] = {"rating": round(avg, 1), "review_count": len(place_reviews)}
            else:
                summary[pid] = {"rating": None, "review_count": 0}
        return jsonify(summary)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
