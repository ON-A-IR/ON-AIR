import os
import tempfile
import unittest
from unittest.mock import patch

import httpx
from backend.main import app
from backend.auth_routes import attempts
from backend.services import auth_service


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"ONAIR_AUTH_DB": os.path.join(self.directory.name, "test.sqlite3")})
        self.environment.start()
        attempts.clear()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.environment.stop()
        self.directory.cleanup()

    async def test_registration_session_and_logout(self):
        credentials = {"username": "test_account", "password": "test-password-123"}
        self.assertIsNone((await self.client.get("/api/auth/me")).json()["user"])
        self.assertEqual((await self.client.post("/api/sources/search", json={"query": "test"})).status_code, 401)
        self.assertEqual((await self.client.post("/api/auth/register", json=credentials)).status_code, 200)
        self.assertEqual((await self.client.post("/api/auth/register", json=credentials)).status_code, 409)
        self.assertEqual((await self.client.post("/api/auth/login", json={**credentials, "password": "wrong-password"})).status_code, 401)
        login = await self.client.post("/api/auth/login", json=credentials)
        self.assertEqual(login.status_code, 200)
        self.assertIn("HttpOnly", login.headers["set-cookie"])
        self.assertIn("SameSite=strict", login.headers["set-cookie"])
        token = self.client.cookies.get("onair_session")
        self.assertEqual((await self.client.get("/api/auth/me")).json()["user"]["username"], "test_account")
        self.assertEqual((await self.client.post("/api/auth/logout", headers={"Origin": "https://untrusted.example"})).status_code, 403)
        self.assertEqual((await self.client.post("/api/auth/logout")).status_code, 200)
        self.assertIsNone(auth_service.current_user(token))
        self.assertIsNone((await self.client.get("/api/auth/me")).json()["user"])

    async def test_validation_and_rate_limit(self):
        self.assertEqual((await self.client.post("/api/auth/register", json={"username": "bad name", "password": "password123"})).status_code, 422)
        self.assertEqual((await self.client.post("/api/auth/register", json={"username": "abc", "password": "short"})).status_code, 422)
        for _ in range(9):
            await self.client.post("/api/auth/login", json={"username": "missing", "password": "password123"})
        self.assertEqual((await self.client.post("/api/auth/login", json={"username": "missing", "password": "password123"})).status_code, 429)


if __name__ == "__main__":
    unittest.main()
