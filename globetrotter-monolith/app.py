"""
GlobeTrotter Travel Assistant -- Phase 1: Monolith
----------------------------------------------------
A single Flask application handling every concern: routing, auth,
business logic, and data access. Everything runs in one process and
reads/writes one JSON file. See README.md for why this is deliberate
and what it teaches.
"""

from flask import Flask, request, jsonify

from auth import hash_password, verify_password, generate_token, token_required
from data_access import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    get_itineraries_for_user,
    create_itinerary,
    get_destinations,
)
from business_logic import recommend_destinations, search_destinations

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")
    preferences = body.get("preferences", [])

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if get_user_by_email(email):
        return jsonify({"error": "A user with that email already exists"}), 409

    user = create_user(
        username=username,
        email=email,
        password_hash=hash_password(password),
        preferences=preferences,
    )
    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }), 201


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user["id"])
    return jsonify({"token": token}), 200


# ---------------------------------------------------------------------------
# Destinations (public)
# ---------------------------------------------------------------------------

@app.route("/destinations", methods=["GET"])
def destinations():
    query = request.args.get("q")
    tag = request.args.get("tag")
    region = request.args.get("region")
    results = search_destinations(query=query, tag=tag, region=region)
    return jsonify(results), 200


# ---------------------------------------------------------------------------
# Recommendations (protected)
# ---------------------------------------------------------------------------

@app.route("/recommendations", methods=["GET"])
@token_required
def recommendations():
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    limit = request.args.get("limit", default=5, type=int)
    results = recommend_destinations(user, limit=limit)
    return jsonify(results), 200


# ---------------------------------------------------------------------------
# Itineraries (protected)
# ---------------------------------------------------------------------------

@app.route("/itineraries", methods=["POST"])
@token_required
def create_itinerary_route():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    destination_id = body.get("destination_id")
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    if not name or destination_id is None or not start_date or not end_date:
        return jsonify({
            "error": "name, destination_id, start_date, and end_date are required"
        }), 400

    valid_ids = {d["id"] for d in get_destinations()}
    if destination_id not in valid_ids:
        return jsonify({"error": "Unknown destination_id"}), 400

    itinerary = create_itinerary(
        user_id=request.user_id,
        name=name,
        destination_id=destination_id,
        start_date=start_date,
        end_date=end_date,
    )
    return jsonify(itinerary), 201


@app.route("/itineraries", methods=["GET"])
@token_required
def get_itineraries_route():
    return jsonify(get_itineraries_for_user(request.user_id)), 200


# ---------------------------------------------------------------------------
# Health check -- useful for later phases (load balancers ping this)
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
