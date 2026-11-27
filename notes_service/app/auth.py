"""Модуль авторизации: регистрация, вход, выход."""
import functools
import re
import sqlite3

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Войдите в аккаунт, чтобы продолжить.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        error = None
        if not USERNAME_RE.match(username):
            error = "Логин: 3–30 символов, только латинские буквы, цифры и _."
        elif len(password) < 6:
            error = "Пароль должен быть не короче 6 символов."
        elif password != password2:
            error = "Пароли не совпадают."

        if error is None:
            try:
                db = get_db()
                db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                           (username, generate_password_hash(password)))
                db.commit()
            except sqlite3.IntegrityError:
                error = "Пользователь с таким логином уже существует."
            else:
                current_app.logger.info("Зарегистрирован пользователь %s", username)
                flash("Регистрация прошла успешно. Теперь войдите.", "success")
                return redirect(url_for("auth.login"))
        flash(error, "danger")
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            current_app.logger.warning("Неудачная попытка входа: %s", username)
            flash("Неверный логин или пароль.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            current_app.logger.info("Вход выполнен: %s", username)
            nxt = request.args.get("next", "")
            # разрешаем только внутренние ссылки (защита от открытого редиректа)
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("notes.index"))
    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("auth.login"))
