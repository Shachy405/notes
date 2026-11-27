"""Фабрика приложения: собирает все модули (БД, авторизация, заметки) вместе."""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template

from . import auth, db, notes
from .security import check_csrf, get_csrf_token


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=os.path.join(app.instance_path, "notes.sqlite"),
        MAX_CONTENT_LENGTH=1024 * 1024,  # не больше 1 МБ в запросе
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    _setup_logging(app)

    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(notes.bp)

    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = get_csrf_token

    with app.app_context():
        db.init_db()  # создаст таблицы, если их еще нет

    _register_error_handlers(app)
    return app


def _setup_logging(app):
    if app.config.get("TESTING"):
        return
    handler = RotatingFileHandler(
        os.path.join(app.instance_path, "app.log"), maxBytes=200_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, text="Страница или заметка не найдена."), 404

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, text="Некорректный запрос (возможно, истекла форма). Обновите страницу."), 400

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Внутренняя ошибка сервера")
        return render_template("error.html", code=500, text="Внутренняя ошибка сервера."), 500
