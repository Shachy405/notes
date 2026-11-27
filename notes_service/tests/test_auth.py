"""Тесты модуля авторизации."""
import sqlite3

from tests.helpers import BaseTestCase


class AuthTests(BaseTestCase):
    def test_pages_open(self):
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/register").status_code, 200)

    def test_register_success_redirects_to_login(self):
        r = self.register()
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_register_duplicate_username(self):
        self.register("bob")
        r = self.register("bob")
        self.assertEqual(r.status_code, 200)
        self.assertIn("уже существует", r.get_data(as_text=True))

    def test_register_bad_username(self):
        r = self.register("a b!")
        self.assertIn("Логин: 3", r.get_data(as_text=True))

    def test_register_short_password(self):
        r = self.register("carol", "123")
        self.assertIn("не короче 6", r.get_data(as_text=True))

    def test_register_password_mismatch(self):
        r = self.post("/register", {"username": "dave", "password": "secret123", "password2": "other123"},
                      token_url="/register")
        self.assertIn("не совпадают", r.get_data(as_text=True))

    def test_password_is_hashed(self):
        self.register("erin", "secret123")
        row = sqlite3.connect(self.db_path).execute("SELECT password_hash FROM users WHERE username='erin'").fetchone()
        self.assertNotEqual(row[0], "secret123")
        self.assertTrue(row[0].startswith(("scrypt:", "pbkdf2:")))

    def test_login_success(self):
        self.register()
        r = self.login()
        self.assertEqual(r.status_code, 302)
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("alice", page)

    def test_login_wrong_password(self):
        self.register()
        r = self.login(password="wrongpass")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Неверный логин или пароль", r.get_data(as_text=True))

    def test_login_unknown_user(self):
        r = self.login("nobody", "whatever1")
        self.assertIn("Неверный логин или пароль", r.get_data(as_text=True))

    def test_protected_page_redirects_to_login(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_logout(self):
        self.register_and_login()
        r = self.post("/logout", token_url="/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)  # снова нужен вход

    def test_post_without_csrf_token_is_rejected(self):
        r = self.client.post("/login", data={"username": "a", "password": "b"})
        self.assertEqual(r.status_code, 400)

    def test_open_redirect_is_blocked(self):
        self.register()
        r = self.post("/login?next=//evil.example", {"username": "alice", "password": "secret123"})
        self.assertNotIn("evil.example", r.headers["Location"])
