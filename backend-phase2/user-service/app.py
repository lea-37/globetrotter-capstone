"""
User Service — Bastos Explorer (Phase 2)
==========================================
Owns ONLY users.json. Issues and can locally verify JWTs (HS256, shared
secret via BASTOS_SECRET_KEY env var — every service verifies the same
signature independently rather than trusting the gateway blindly; this
zero-trust-between-services habit is deliberate, in keeping with the
project's cybersecurity angle).

Design patterns: Singleton (store.py), Repository (UserRepository below),
Decorator (login_required), Factory (create_app()).
"""
import os
import datetime
from functools import wraps

import jwt
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from store import JSONStore

SECRET_KEY = os.environ.get("BASTOS_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_HOURS = 12
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class UserRepository:
    def __init__(self):
        self.store = JSONStore.instance(os.path.join(DATA_DIR, "users.json"))

    def find_all(self):
        return self.store.read()

    def find_by_email(self, email):
        email = (email or "").strip().lower()
        return next((u for u in self.find_all() if u.get("email", "").lower() == email), None)

    def add(self, row):
        data = self.find_all()
        row["id"] = self.store.next_id(data)
        data.append(row)
        self.store.write(data)
        return row


user_repo = UserRepository()


def issue_token(user):
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


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
        return jsonify({"status": "ok", "service": "user-service"})

    @app.post("/register")
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
            "password_hash": generate_password_hash(password),
        })
        token = issue_token(user)
        return jsonify({
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
        }), 201

    @app.post("/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""

        user = user_repo.find_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        token = issue_token(user)
        return jsonify({
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
        })

    @app.get("/me")
    @login_required
    def me():
        return jsonify(g.current_user)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
