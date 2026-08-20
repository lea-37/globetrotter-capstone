"""
Place Service — Bastos Explorer (Phase 2)
==========================================
Owns ONLY places.json — restaurants, hotels, clinics, schools, supermarkets,
markets and filling stations of Bastos. Independently verifies JWTs (zero
trust: it does not assume a request reaching it has already been checked by
the gateway).

Design patterns: Singleton (store.py), Repository (PlaceRepository),
Strategy (sort strategies), Decorator (login_required), Factory (create_app()).
"""
import os
import math
from functools import wraps

import jwt
from flask import Flask, request, jsonify

from store import JSONStore

SECRET_KEY = os.environ.get("BASTOS_SECRET_KEY", "dev-secret-change-me")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class PlaceRepository:
    def __init__(self):
        self.store = JSONStore.instance(os.path.join(DATA_DIR, "places.json"))

    def find_all(self):
        return self.store.read()

    def find_by_id(self, place_id):
        return next((p for p in self.find_all() if p.get("id") == place_id), None)

    def find_by_category(self, category):
        if not category:
            return self.find_all()
        category = category.lower()
        return [p for p in self.find_all() if p.get("category", "").lower() == category]


place_repo = PlaceRepository()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentification requise."}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expirée."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Jeton invalide."}), 401
        return view_func(*args, **kwargs)
    return wrapper


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _sort_by_name(places, **kw):
    return sorted(places, key=lambda p: p.get("name", ""))


def _sort_by_distance(places, user_lat=None, user_lon=None, **kw):
    if user_lat is None or user_lon is None:
        return places
    return sorted(places, key=lambda p: _haversine_km(user_lat, user_lon, p["lat"], p["lon"]))


SORT_STRATEGIES = {"name": _sort_by_name, "distance": _sort_by_distance}


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
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
        return jsonify({"status": "ok", "service": "place-service"})

    @app.get("/places")
    @login_required
    def list_places():
        category = request.args.get("category")
        query = request.args.get("q")
        sort = request.args.get("sort", "name")
        user_lat = request.args.get("lat", type=float)
        user_lon = request.args.get("lon", type=float)

        places = place_repo.find_by_category(category)
        if query:
            q = query.lower()
            places = [p for p in places if q in p.get("name", "").lower() or q in p.get("description", "").lower()]
        strategy = SORT_STRATEGIES.get(sort, _sort_by_name)
        places = strategy(places, user_lat=user_lat, user_lon=user_lon)
        return jsonify(places)

    @app.get("/places/<int:place_id>")
    @login_required
    def get_place(place_id):
        place = place_repo.find_by_id(place_id)
        if not place:
            return jsonify({"error": "Lieu introuvable."}), 404
        return jsonify(place)

    # Internal endpoint (no auth) — lets other services (review-service) cheaply
    # check a place exists without forcing them to also hold a user's token.
    @app.get("/internal/places/<int:place_id>/exists")
    def place_exists(place_id):
        place = place_repo.find_by_id(place_id)
        return jsonify({"exists": place is not None})

    @app.get("/categories")
    @login_required
    def categories():
        places = place_repo.find_all()
        return jsonify(sorted({p["category"] for p in places}))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
