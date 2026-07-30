"""
Data Access Layer
-----------------
Phase 1 deliberately uses a single JSON file instead of a database.
This module is the ONLY place in the codebase that touches the file,
so when Phase 3 swaps this for a real database, only this file changes.

Every read/write is guarded by a lock. This does NOT make it safe for
concurrent access the way a database transaction would -- it just
prevents the Python process from corrupting the file when two requests
land at the same instant. This limitation is intentional: you are meant
to feel it, and later phases will show you why databases exist.
"""

import json
import os
import threading

DATA_FILE = os.environ.get("DATA_FILE", os.path.join(os.path.dirname(__file__), "data", "data.json"))

_lock = threading.Lock()

_DEFAULT_STATE = {
    "users": [],
    "destinations": [],
    "itineraries": [],
    "next_user_id": 1,
    "next_itinerary_id": 1,
}


def _ensure_file_exists():
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(_DEFAULT_STATE, f, indent=2)


def load_data():
    """Reads the entire JSON file into memory. Called on every request that needs data."""
    _ensure_file_exists()
    with _lock:
        with open(DATA_FILE, "r") as f:
            return json.load(f)


def save_data(data):
    """Overwrites the entire JSON file. There is no partial-write or transaction support."""
    with _lock:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)


# --- Convenience helpers used by the API layer ---

def get_users():
    return load_data()["users"]


def get_user_by_email(email):
    return next((u for u in get_users() if u["email"] == email), None)


def get_user_by_id(user_id):
    return next((u for u in get_users() if u["id"] == user_id), None)


def create_user(username, email, password_hash, preferences=None):
    data = load_data()
    user = {
        "id": data["next_user_id"],
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "preferences": preferences or [],
    }
    data["users"].append(user)
    data["next_user_id"] += 1
    save_data(data)
    return user


def get_destinations():
    return load_data()["destinations"]


def get_itineraries_for_user(user_id):
    data = load_data()
    return [it for it in data["itineraries"] if it["user_id"] == user_id]


def create_itinerary(user_id, name, destination_id, start_date, end_date):
    data = load_data()
    itinerary = {
        "id": data["next_itinerary_id"],
        "user_id": user_id,
        "name": name,
        "destination_id": destination_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    data["itineraries"].append(itinerary)
    data["next_itinerary_id"] += 1
    save_data(data)
    return itinerary
