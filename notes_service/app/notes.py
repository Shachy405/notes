"""Модуль заметок: просмотр, поиск, создание, изменение, удаление + JSON API."""
from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db

bp = Blueprint("notes", __name__)
MAX_TITLE = 100
MAX_CONTENT = 5000


def _get_own_note(note_id):
    """Заметка нужна только ее владельцу; чужая заметка = 404."""
    note = get_db().execute("SELECT * FROM notes WHERE id = ? AND user_id = ?",
                            (note_id, g.user["id"])).fetchone()
    if note is None:
        abort(404)
    return note


def _validate(title, content):
    if not title:
        return "Введите заголовок."
    if len(title) > MAX_TITLE:
        return "Заголовок не длиннее %d символов." % MAX_TITLE
    if len(content) > MAX_CONTENT:
        return "Текст не длиннее %d символов." % MAX_CONTENT
    return None


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    rows = get_db().execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (g.user["id"],)
    ).fetchall()
    if q:  # поиск без учета регистра (в том числе для кириллицы)
        rows = [r for r in rows if q.casefold() in (r["title"] + " " + r["content"]).casefold()]
    return render_template("notes/index.html", notes=rows, q=q)


@bp.route("/notes/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        error = _validate(title, content)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                       (g.user["id"], title, content))
            db.commit()
            flash("Заметка создана.", "success")
            return redirect(url_for("notes.index"))
    return render_template("notes/form.html", note=None, title_text="Новая заметка")


@bp.route("/notes/<int:note_id>/edit", methods=("GET", "POST"))
@login_required
def edit(note_id):
    note = _get_own_note(note_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        error = _validate(title, content)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute("UPDATE notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP "
                       "WHERE id = ? AND user_id = ?", (title, content, note_id, g.user["id"]))
            db.commit()
            flash("Изменения сохранены.", "success")
            return redirect(url_for("notes.index"))
    return render_template("notes/form.html", note=note, title_text="Редактирование заметки")


@bp.route("/notes/<int:note_id>/delete", methods=("POST",))
@login_required
def delete(note_id):
    _get_own_note(note_id)
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, g.user["id"]))
    db.commit()
    flash("Заметка удалена.", "info")
    return redirect(url_for("notes.index"))


@bp.route("/api/notes")
def api_notes():
    """JSON-интерфейс: пример интеграции frontend/клиент <-> backend <-> БД."""
    if g.user is None:
        return jsonify(error="Требуется вход"), 401
    rows = get_db().execute(
        "SELECT id, title, content, created_at, updated_at FROM notes WHERE user_id = ? "
        "ORDER BY updated_at DESC, id DESC", (g.user["id"],)).fetchall()
    return jsonify([dict(r) for r in rows])
