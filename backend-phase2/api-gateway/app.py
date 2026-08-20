"""
API Gateway — Bastos Explorer (Phase 2)
==========================================
The single entry point the frontend talks to. Authenticates requests,
forwards them to user-service / place-service / review-service, and
composes results that span more than one service (e.g. a place's detail
page needs place-service's data AND review-service's reviews).

Design patterns: Decorator (login_required — checked here too, in addition
to each downstream service, on purpose: defense in depth rather than a
single trust boundary), Factory (create_app()).
"""
import os
from functools import wraps

import jwt
import requests
from flask import Flask, request, jsonify, g

SECRET_KEY = os.environ.get("BASTOS_SECRET_KEY", "dev-secret-change-me")
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://127.0.0.1:5001")
PLACE_SERVICE_URL = os.environ.get("PLACE_SERVICE_URL", "http://127.0.0.1:5002")
REVIEW_SERVICE_URL = os.environ.get("REVIEW_SERVICE_URL", "http://127.0.0.1:5003")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentification requise. Veuillez vous connecter."}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expirée, reconnectez-vous."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Jeton invalide."}), 401
        g.current_user = {"id": payload["sub"], "username": payload["username"]}
        return view_func(*args, **kwargs)
    return wrapper


def _auth_headers():
    return {"Authorization": request.headers.get("Authorization", "")}


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def _upstream_error(service_name):
    return jsonify({"error": f"Le service « {service_name} » est indisponible pour le moment."}), 503


def create_app():
    app = Flask(__name__)
    app.after_request(_cors)

    @app.before_request
    def preflight():
        if request.method == "OPTIONS":
            return _cors(app.make_default_options_response())

    @app.get("/health")
    def health():
        statuses = {}
        for name, url in [("user-service", USER_SERVICE_URL), ("place-service", PLACE_SERVICE_URL), ("review-service", REVIEW_SERVICE_URL)]:
            try:
                r = requests.get(url + "/health", timeout=2)
                statuses[name] = "ok" if r.ok else "error"
            except requests.RequestException:
                statuses[name] = "unreachable"
        return jsonify({"status": "ok", "service": "api-gateway", "upstreams": statuses})

    # ---------------- AUTH (forwarded to user-service) ----------------

    @app.post("/api/register")
    def register():
        try:
            r = requests.post(f"{USER_SERVICE_URL}/register", json=request.get_json(silent=True) or {}, timeout=5)
        except requests.RequestException:
            return _upstream_error("user-service")
        return jsonify(r.json()), r.status_code

    @app.post("/api/login")
    def login():
        try:
            r = requests.post(f"{USER_SERVICE_URL}/login", json=request.get_json(silent=True) or {}, timeout=5)
        except requests.RequestException:
            return _upstream_error("user-service")
        return jsonify(r.json()), r.status_code

    @app.get("/api/me")
    @login_required
    def me():
        try:
            r = requests.get(f"{USER_SERVICE_URL}/me", headers=_auth_headers(), timeout=5)
        except requests.RequestException:
            return _upstream_error("user-service")
        return jsonify(r.json()), r.status_code

    # ---------------- PLACES (place-service, enriched with review-service ratings) ----------------

    @app.get("/api/places")
    @login_required
    def list_places():
        try:
            r = requests.get(f"{PLACE_SERVICE_URL}/places", params=request.args, headers=_auth_headers(), timeout=5)
        except requests.RequestException:
            return _upstream_error("place-service")
        if not r.ok:
            return jsonify(r.json()), r.status_code
        places = r.json()

        ids = ",".join(str(p["id"]) for p in places)
        summary = {}
        if ids:
            try:
                rs = requests.get(f"{REVIEW_SERVICE_URL}/reviews/summary", params={"place_ids": ids}, headers=_auth_headers(), timeout=5)
                if rs.ok:
                    summary = {int(k): v for k, v in rs.json().items()}
            except requests.RequestException:
                pass  # ratings are enrichment, not critical — degrade gracefully

        for p in places:
            info = summary.get(p["id"], {"rating": None, "review_count": 0})
            p["rating"] = info["rating"]
            p["review_count"] = info["review_count"]

        if request.args.get("sort") == "rating":
            places = sorted(places, key=lambda p: (p["rating"] is None, -(p["rating"] or 0)))

        return jsonify(places)

    @app.get("/api/places/<int:place_id>")
    @login_required
    def get_place(place_id):
        try:
            r = requests.get(f"{PLACE_SERVICE_URL}/places/{place_id}", headers=_auth_headers(), timeout=5)
        except requests.RequestException:
            return _upstream_error("place-service")
        if not r.ok:
            return jsonify(r.json()), r.status_code
        place = r.json()

        try:
            rr = requests.get(f"{REVIEW_SERVICE_URL}/places/{place_id}/reviews", headers=_auth_headers(), timeout=5)
            reviews = rr.json() if rr.ok else []
        except requests.RequestException:
            reviews = []

        place["reviews"] = reviews
        if reviews:
            place["rating"] = round(sum(rv["rating"] for rv in reviews) / len(reviews), 1)
        else:
            place["rating"] = None
        place["review_count"] = len(reviews)
        return jsonify(place)

    @app.get("/api/categories")
    @login_required
    def categories():
        try:
            r = requests.get(f"{PLACE_SERVICE_URL}/categories", headers=_auth_headers(), timeout=5)
        except requests.RequestException:
            return _upstream_error("place-service")
        return jsonify(r.json()), r.status_code

    # ---------------- REVIEWS (forwarded to review-service) ----------------

    @app.post("/api/places/<int:place_id>/reviews")
    @login_required
    def add_review(place_id):
        try:
            r = requests.post(
                f"{REVIEW_SERVICE_URL}/places/{place_id}/reviews",
                json=request.get_json(silent=True) or {},
                headers=_auth_headers(),
                timeout=5,
            )
        except requests.RequestException:
            return _upstream_error("review-service")
        return jsonify(r.json()), r.status_code

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
