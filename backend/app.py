"""
Bastos Explorer — backend API
==============================
Design pattern: FACTORY
----------------------------------
create_app() builds and configures the Flask app in one place instead of
using a bare module-level `app = Flask(__name__)`. This keeps configuration
(CORS, blueprints, secret key) explicit and makes the app easy to spin up
multiple times for tests.

See services/store.py, services/repositories.py, services/auth_service.py
and services/place_service.py for the other patterns used (Singleton,
Repository, Decorator, Strategy).
"""
from flask import Flask, request, jsonify, g

from services.repositories import UserRepository, ReviewRepository
from services.auth_service import hash_password, verify_password, issue_token, login_required
from services import place_service

user_repo = UserRepository()
review_repo = ReviewRepository()


def _add_cors_headers(response):
    """Minimal manual CORS so the app has no third-party dependency for it."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


def create_app():
    app = Flask(__name__)
    app.after_request(_add_cors_headers)

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return _add_cors_headers(app.make_default_options_response())

    register_routes(app)
    return app


def register_routes(app):

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "bastos-explorer-api"})

    # ---------------- AUTH ----------------

    @app.post("/api/register")
    def register():
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""

        if not username or not email or not password:
            return jsonify({"error": "Nom d'utilisateur, email et mot de passe sont requis."}), 400
        if len(password) < 6:
            return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères."}), 400
        if user_repo.find_by_email(email):
            return jsonify({"error": "Un compte existe déjà avec cet email."}), 409

        user = user_repo.add({
            "username": username,
            "email": email,
            "password_hash": hash_password(password),
        })
        token = issue_token(user)
        return jsonify({
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
        }), 201

    @app.post("/api/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""

        user = user_repo.find_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        token = issue_token(user)
        return jsonify({
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
        })

    @app.get("/api/me")
    @login_required
    def me():
        return jsonify(g.current_user)

    # ---------------- PLACES (gated: must be logged in) ----------------

    @app.get("/api/places")
    @login_required
    def list_places():
        category = request.args.get("category")
        query = request.args.get("q")
        sort = request.args.get("sort", "name")
        user_lat = request.args.get("lat", type=float)
        user_lon = request.args.get("lon", type=float)
        places = place_service.list_places(
            category=category, query=query, sort=sort,
            user_lat=user_lat, user_lon=user_lon,
        )
        return jsonify(places)

    @app.get("/api/places/<int:place_id>")
    @login_required
    def get_place(place_id):
        place = place_service.get_place(place_id)
        if not place:
            return jsonify({"error": "Lieu introuvable."}), 404
        place = dict(place)
        place["reviews"] = review_repo.find_by_place(place_id)
        return jsonify(place)

    @app.get("/api/categories")
    @login_required
    def categories():
        places = place_service.place_repo.find_all()
        cats = sorted({p["category"] for p in places})
        return jsonify(cats)

    # ---------------- REVIEWS (gated: must be logged in) ----------------

    @app.post("/api/places/<int:place_id>/reviews")
    @login_required
    def add_review(place_id):
        place = place_service.place_repo.find_by_id(place_id)
        if not place:
            return jsonify({"error": "Lieu introuvable."}), 404
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


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
