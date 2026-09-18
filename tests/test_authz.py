import os
import tempfile
import unittest

from src.db import Database
from src.auth import ROUTE_METHOD_PERMISSIONS, _route_permission
from src.domains.authz.service import ensure_schema, has_permission, public_user, create_user, update_user


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "data", "app.db"))
        ensure_schema(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_viewer_is_read_only_by_default(self):
        user = self.db.get_user(1)
        self.assertIsNotNone(user)
        self.assertTrue(has_permission(self.db, 1, "viewer", "channels", "view"))
        self.assertTrue(has_permission(self.db, 1, "viewer", "playlists", "view"))
        self.assertFalse(has_permission(self.db, 1, "viewer", "channels", "edit"))
        self.assertFalse(has_permission(self.db, 1, "viewer", "users", "view"))
        self.assertFalse(has_permission(self.db, 1, "viewer", "logs", "view"))

    def test_editor_gets_operational_permissions_without_user_admin(self):
        self.assertTrue(has_permission(self.db, 1, "editor", "channels", "edit"))
        self.assertTrue(has_permission(self.db, 1, "editor", "sync", "execute"))
        self.assertFalse(has_permission(self.db, 1, "editor", "users", "view"))
        self.assertFalse(has_permission(self.db, 1, "editor", "settings", "admin"))

    def test_admin_has_full_permissions(self):
        for resource in ("users", "settings", "maintenance", "system"):
            for action in ("view", "create", "edit", "delete", "execute", "admin"):
                self.assertTrue(has_permission(self.db, 1, "admin", resource, action))

    def test_user_profile_and_permissions_are_returned_without_password_hash(self):
        created = create_user(self.db, {
            "username": "demo2", "password": "password123", "role": "viewer",
            "display_name": "Demo Dois", "email": "demo2@example.test", "active": True,
            "permissions": {"health": ["view"]},
        })
        self.assertIsNotNone(created)
        self.assertEqual(created["display_name"], "Demo Dois")
        self.assertEqual(created["email"], "demo2@example.test")
        self.assertNotIn("password_hash", created)
        self.assertTrue(has_permission(self.db, created["id"], "viewer", "health", "view"))

    def test_update_user_can_disable_and_change_profile(self):
        created = create_user(self.db, {"username": "demo3", "password": "password123", "role": "viewer"})
        updated = update_user(self.db, created["id"], {"display_name": "Conta desativada", "active": False})
        self.assertEqual(updated["display_name"], "Conta desativada")
        self.assertFalse(updated["active"])

    def test_user_management_uses_create_permission_for_post(self):
        self.assertEqual(ROUTE_METHOD_PERMISSIONS["api_users"]["GET"], ("users", "view"))
        self.assertEqual(ROUTE_METHOD_PERMISSIONS["api_users"]["POST"], ("users", "create"))

    def test_critical_channel_routes_use_granular_actions(self):
        self.assertEqual(_route_permission("create_channel"), ("channels", "create"))
        self.assertEqual(_route_permission("delete_channel"), ("channels", "delete"))
        self.assertEqual(_route_permission("api_update_channel"), ("channels", "edit"))
        self.assertEqual(_route_permission("api_generate_custom_playlist"), ("playlists", "create"))

    def test_route_permission_fails_closed_for_unknown_method(self):
        # A chamada fora da matriz explícita não deve herdar a permissão de GET.
        self.assertIsNone(ROUTE_METHOD_PERMISSIONS["api_users"].get("DELETE"))


if __name__ == "__main__":
    unittest.main()
