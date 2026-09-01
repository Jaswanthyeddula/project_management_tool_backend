import unittest
from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.models import Board, Project
from app.services.notification_service import create_notification


class ApiRouteAuditTests(unittest.TestCase):
    """Exercises every non-static application route against an in-memory DB."""

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def call(self, method, path, token=None, expected_status=200, **kwargs):
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = self.client.open(path, method=method, headers=headers, **kwargs)
        self.assertEqual(
            response.status_code,
            expected_status,
            f"{method} {path} returned {response.status_code}: {response.get_data(as_text=True)}",
        )
        return response.get_json()

    def assert_iso_datetime(self, value):
        self.assertIsInstance(value, str)
        self.assertEqual(datetime.fromisoformat(value).tzinfo, timezone.utc)

    def assert_utc_datetime(self, value):
        self.assertEqual(value.tzinfo, timezone.utc)

    def test_every_application_route(self):
        self.call("GET", "/health")

        owner = self.call(
            "POST",
            "/api/auth/register",
            expected_status=201,
            json={
                "name": "jaswanth",
                "email": "jaswanth.route-test@example.com",
                "password": "route-test-password",
            },
        )
        member = self.call(
            "POST",
            "/api/auth/register",
            expected_status=201,
            json={
                "name": "Route Member",
                "email": "route-member@example.com",
                "password": "route-test-password",
            },
        )
        token = owner["access_token"]
        refresh_token = owner["refresh_token"]
        owner_id = owner["user"]["id"]
        member_id = member["user"]["id"]

        self.call(
            "POST",
            "/api/auth/login",
            json={"email": "jaswanth.route-test@example.com", "password": "route-test-password"},
        )
        self.call("POST", "/api/auth/refresh", refresh_token)
        self.call("GET", "/api/auth/me", token)

        project = self.call(
            "POST", "/api/projects", token, 201, json={"name": "Route audit", "description": "Test"}
        )
        project_id = project["id"]
        self.assert_iso_datetime(project["created_at"])
        self.assert_iso_datetime(project["updated_at"])
        self.assertIsNone(project["deleted_at"])
        with self.app.app_context():
            db.session.expire_all()
            self.assert_utc_datetime(db.session.get(Project, project_id).created_at)
        self.call("GET", "/api/projects", token)
        self.call("GET", f"/api/projects/{project_id}", token)
        self.call("PATCH", f"/api/projects/{project_id}", token, json={"name": "Route audit updated"})
        self.call("GET", f"/api/projects/{project_id}/stats", token)
        self.call("GET", f"/api/projects/{project_id}/members", token)
        self.call(
            "POST",
            f"/api/projects/{project_id}/members",
            token,
            201,
            json={"user_id": member_id, "role": "member"},
        )
        self.call(
            "PATCH", f"/api/projects/{project_id}/members/{member_id}", token, json={"role": "admin"}
        )

        board = self.call("POST", f"/api/boards/project/{project_id}", token, 201, json={"name": "Backlog"})
        board_id = board["id"]
        self.assert_iso_datetime(board["created_at"])
        self.assert_iso_datetime(board["updated_at"])
        self.assertIsNone(board["deleted_at"])
        with self.app.app_context():
            db.session.expire_all()
            self.assert_utc_datetime(db.session.get(Board, board_id).created_at)
        self.call("GET", f"/api/boards/project/{project_id}", token)
        self.call("GET", f"/api/boards/{board_id}", token)
        self.call("PATCH", f"/api/boards/{board_id}", token, json={"name": "Active"})
        self.call("PATCH", f"/api/boards/{board_id}/reorder", token, json={"new_order": 100})
        duplicate_board = self.call("POST", f"/api/boards/{board_id}/duplicate", token, 201)
        duplicate_board_id = duplicate_board["id"]
        self.call("DELETE", f"/api/boards/{duplicate_board_id}", token)
        deleted_boards = self.call("GET", f"/api/boards/project/{project_id}/deleted", token)["boards"]
        deleted_board = next(board for board in deleted_boards if board["id"] == duplicate_board_id)
        self.assert_iso_datetime(deleted_board["deleted_at"])
        self.call("PATCH", f"/api/boards/{duplicate_board_id}/restore", token)

        task = self.call(
            "POST",
            f"/api/boards/{board_id}/tasks",
            token,
            201,
            json={"title": "Route task", "priority": "high", "due_date": "2026-09-01"},
        )
        task_id = task["id"]
        self.call("GET", f"/api/boards/{board_id}/tasks?status=todo", token)
        self.call("GET", f"/api/tasks/{task_id}", token)
        self.call(
            "PATCH",
            f"/api/tasks/{task_id}",
            token,
            json={"title": "Updated task", "priority": "urgent", "due_date": "2026-09-02"},
        )
        self.call("PATCH", f"/api/tasks/{task_id}/move", token, json={"status": "in_progress", "position": 200})
        self.call("PATCH", f"/api/tasks/{task_id}/assign", token, json={"assignee_id": member_id})
        self.call("DELETE", f"/api/tasks/{task_id}", token)
        self.call("PATCH", f"/api/tasks/{task_id}/restore", token)

        label = self.call(
            "POST",
            f"/api/projects/{project_id}/labels",
            token,
            201,
            json={"name": "Urgent", "color": "#ff0000"},
        )["label"]
        label_id = label["id"]
        self.call("GET", f"/api/projects/{project_id}/labels", token)
        self.call(
            "PATCH", f"/api/labels/{label_id}", token, 201, json={"name": "Critical", "color": "#cc0000"}
        )
        self.call("POST", f"/api/tasks/{task_id}/labels", token, json={"label_ids": [label_id]})
        self.call("GET", f"/api/tasks/{task_id}/labels", token)
        self.call("GET", f"/api/projects/{project_id}/tasks/filter?label_ids={label_id}", token)
        self.call("DELETE", f"/api/tasks/{task_id}/labels/{label_id}", token)

        comment = self.call(
            "POST", f"/api/tasks/{task_id}/comments", token, 201, json={"content": "Ready for review"}
        )
        self.call("GET", f"/api/tasks/{task_id}/comments", token)
        self.call("DELETE", f"/api/comments/{comment['comment']['id']}", token)
        self.call("DELETE", f"/api/labels/{label_id}", token)

        with self.app.app_context():
            notification_id = create_notification(owner_id, "task_assigned", "A task was assigned", task_id).id
        self.call("GET", "/notifications", token)
        self.call("GET", "/notifications?unread_only=true", token)
        self.call("GET", "/notifications/unread-count", token)
        self.call("PATCH", f"/notifications/{notification_id}/read", token)
        self.call("PATCH", "/notifications/read-all", token)

        self.call("DELETE", f"/api/projects/{project_id}/members/{member_id}", token)
        self.call("DELETE", f"/api/projects/{project_id}", token)
        self.call("PATCH", f"/api/projects/{project_id}/restore", token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
