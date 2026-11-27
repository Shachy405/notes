"""Защита форм от CSRF: в каждую форму вставляется секретный токен."""
import secrets

from flask import abort, request, session


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        saved = session.get("csrf_token", "")
        if not sent or not saved or not secrets.compare_digest(sent, saved):
            abort(400)
