"""
Design pattern: DECORATOR
----------------------------------
@login_required wraps a Flask view function and adds a behaviour (checking
and decoding the JWT) without changing the view's own code. Any route that
needs "you must be logged in" just adds the decorator.
"""
import os
import datetime
from functools import wraps

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

SECRET_KEY = os.environ.get("BASTOS_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_HOURS = 12


def hash_password(raw_password):
    return generate_password_hash(raw_password)


def verify_password(raw_password, password_hash):
    return check_password_hash(password_hash, raw_password)


def issue_token(user):
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentification requise. Veuillez vous connecter."}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expirée, reconnectez-vous."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Jeton invalide."}), 401
        g.current_user = {"id": payload["sub"], "username": payload["username"]}
        return view_func(*args, **kwargs)
    return wrapper
