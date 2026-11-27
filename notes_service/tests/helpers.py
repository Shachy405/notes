"""Общие вспомогательные функции для тестов."""
import os
import re
import tempfile
import unittest

from app import create_app


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".sqlite")
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # --- помощники ---
    def token(self, url="/login"):
        """Получить CSRF-токен со страницы с формой."""
        html = self.client.get(url).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def post(self, url, data=None, token_url="/login", **kw):
        data = dict(data or {})
        data["csrf_token"] = self.token(token_url)
        return self.client.post(url, data=data, **kw)

    def register(self, username="alice", password="secret123"):
        return self.post("/register", {"username": username, "password": password, "password2": password},
                         token_url="/register")

    def login(self, username="alice", password="secret123"):
        return self.post("/login", {"username": username, "password": password})

    def register_and_login(self, username="alice", password="secret123"):
        self.register(username, password)
        return self.login(username, password)

    def create_note(self, title="Заголовок", content="Текст", **kw):
        return self.post("/notes/create", {"title": title, "content": content}, token_url="/notes/create", **kw)
