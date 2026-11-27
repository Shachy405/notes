"""Тесты модуля заметок и интеграции frontend <-> backend <-> БД."""
import sqlite3

from tests.helpers import BaseTestCase


class NotesTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.register_and_login("alice")

    def test_empty_list(self):
        self.assertIn("Заметок пока нет", self.client.get("/").get_data(as_text=True))

    def test_create_note_and_see_it_in_list_and_db(self):
        r = self.create_note("Покупки", "Молоко, хлеб")
        self.assertEqual(r.status_code, 302)
        self.assertIn("Покупки", self.client.get("/").get_data(as_text=True))
        row = sqlite3.connect(self.db_path).execute("SELECT title, content FROM notes").fetchone()
        self.assertEqual(row, ("Покупки", "Молоко, хлеб"))

    def test_create_note_empty_title(self):
        r = self.create_note("", "текст")
        self.assertIn("Введите заголовок", r.get_data(as_text=True))

    def test_create_note_too_long_title(self):
        r = self.create_note("a" * 101, "текст")
        self.assertIn("не длиннее 100", r.get_data(as_text=True))

    def test_edit_note(self):
        self.create_note("Старое", "текст")
        r = self.post("/notes/1/edit", {"title": "Новое", "content": "другой текст"}, token_url="/notes/1/edit")
        self.assertEqual(r.status_code, 302)
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Новое", page)
        self.assertNotIn("Старое", page)

    def test_delete_note(self):
        self.create_note("Удалить меня", "x")
        r = self.post("/notes/1/delete", token_url="/")
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("Удалить меня", self.client.get("/").get_data(as_text=True))

    def test_search_is_case_insensitive_for_cyrillic(self):
        self.create_note("Рецепт борща", "свёкла, капуста")
        self.create_note("Список дел", "позвонить маме")
        page = self.client.get("/?q=БОРЩ").get_data(as_text=True)
        self.assertIn("Рецепт борща", page)
        self.assertNotIn("Список дел", page)

    def test_search_nothing_found(self):
        self.create_note("Заметка", "текст")
        self.assertIn("Ничего не найдено", self.client.get("/?q=zzz").get_data(as_text=True))

    def test_user_cannot_see_or_change_foreign_notes(self):
        self.create_note("Секрет Alice", "пароль от сейфа")
        self.post("/logout", token_url="/")
        self.register_and_login("bob")
        self.assertNotIn("Секрет Alice", self.client.get("/").get_data(as_text=True))
        self.assertEqual(self.client.get("/notes/1/edit").status_code, 404)
        self.assertEqual(self.post("/notes/1/delete", token_url="/").status_code, 404)
        # у Alice заметка осталась
        count = sqlite3.connect(self.db_path).execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        self.assertEqual(count, 1)

    def test_unknown_note_gives_404_page(self):
        r = self.client.get("/notes/999/edit")
        self.assertEqual(r.status_code, 404)
        self.assertIn("не найдена", r.get_data(as_text=True))

    def test_api_returns_only_own_notes_as_json(self):
        self.create_note("Моя", "текст")
        r = self.client.get("/api/notes")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Моя")

    def test_api_requires_login(self):
        self.post("/logout", token_url="/")
        r = self.client.get("/api/notes")
        self.assertEqual(r.status_code, 401)

    def test_html_in_note_is_escaped(self):
        self.create_note("<script>alert(1)</script>", "x")
        page = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
