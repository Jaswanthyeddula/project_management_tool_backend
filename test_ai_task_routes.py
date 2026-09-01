import unittest
from unittest.mock import patch, MagicMock

from app import create_app
from app.extensions import db


class AiTaskRouteTests(unittest.TestCase):
    """Exercises the AI task parsing endpoint with a mocked Gemini call."""

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

        owner = self.call(
            "POST",
            "/api/auth/register",
            expected_status=201,
            json={
                "name": "AI Test Owner",
                "email": "ai.test.owner@example.com",
                "password": "ai-test-password",
            },
        )
        self.token = owner["access_token"]

        project = self.call(
            "POST", "/api/projects", self.token, 201,
            json={"name": "AI Test Project", "description": "Test"}
        )
        self.project_id = project["id"]

        board = self.call(
            "POST", f"/api/boards/project/{self.project_id}", self.token, 201,
            json={"name": "AI Test Board"}
        )
        self.board_id = board["id"]

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

    def add_project_member(self, name, email):
        """Registers a new user and adds them as a member of self.project_id.
        Returns the new user's id."""
        registered = self.call(
            "POST",
            "/api/auth/register",
            expected_status=201,
            json={"name": name, "email": email, "password": "ai-test-password"},
        )
        user_id = registered["user"]["id"]

        self.call(
            "POST",
            f"/api/projects/{self.project_id}/members",
            self.token,
            201,
            json={"user_id": user_id, "role": "member"},
        )
        return user_id

    @patch("app.blueprints.ai.routes.parse_task_from_text")
    def test_ai_task_creation_success(self, mock_parse):
        mock_parse.return_value = (
            MagicMock(),  # fake raw_llm_response
            {
                "title": "Fix the login bug",
                "description": "",
                "due_date": "2026-09-04",
                "priority": "high",
                "assignee_name": ""
            }
        )

        result = self.call(
            "POST",
            f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
            self.token,
            201,
            json={"input": "Fix the login bug by Friday, high priority"}
        )

        self.assertEqual(result["task"]["title"], "Fix the login bug")
        self.assertEqual(result["task"]["priority"], "high")
        self.assertEqual(result["ai_task_request"]["status"], "success")
        self.assertIsNotNone(result["ai_task_request"]["created_task_id"])

    @patch("app.blueprints.ai.routes.parse_task_from_text")
    def test_ai_task_missing_title_fails_validation(self, mock_parse):
        mock_parse.return_value = (
            MagicMock(),
            {"title": "", "description": "", "due_date": "", "priority": "", "assignee_name": ""}
        )

        result = self.call(
            "POST",
            f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
            self.token,
            422,
            json={"input": "some vague garbled input"}
        )

        self.assertEqual(result["error"], "AI_VALIDATION_FAILED")
        self.assertEqual(result["ai_task_request"]["status"], "validation_failed")

    @patch("app.blueprints.ai.routes.parse_task_from_text")
    def test_ai_task_assignee_not_found(self, mock_parse):
        mock_parse.return_value = (
            MagicMock(),
            {
                "title": "Fix the bug",
                "description": "",
                "due_date": "",
                "priority": "high",
                "assignee_name": "NonexistentPerson"
            }
        )

        result = self.call(
            "POST",
            f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
            self.token,
            422,
            json={"input": "Fix the bug, assign to NonexistentPerson"}
        )

        self.assertEqual(result["error"], "ASSIGNEE_NOT_FOUND")
        self.assertEqual(result["ai_task_request"]["status"], "assignee_not_found")

    def test_ai_task_llm_failure(self):
        with patch("app.blueprints.ai.routes.parse_task_from_text") as mock_parse:
            from app.services.ai_task_parser import GeminiLLMError
            mock_parse.side_effect = GeminiLLMError("simulated network failure")

            result = self.call(
                "POST",
                f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
                self.token,
                503,
                json={"input": "Fix the bug"}
            )

            self.assertEqual(result["error"], "AI_SERVICE_UNAVAILABLE")

    def test_ai_task_parse_failed(self):
        with patch("app.blueprints.ai.routes.parse_task_from_text") as mock_parse:
            from app.services.ai_task_parser import GeminiParseError
            mock_parse.side_effect = GeminiParseError("no function_call returned")

            result = self.call(
                "POST",
                f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
                self.token,
                422,
                json={"input": "some ambiguous unparseable text"}
            )

            self.assertEqual(result["error"], "AI_PARSE_FAILED")
            # Note: the route's GeminiParseError handler doesn't include
            # ai_task_request in its response body, so we only check the
            # top-level error code here.

    @patch("app.blueprints.ai.routes.parse_task_from_text")
    def test_ai_task_assignee_ambiguous(self, mock_parse):
        # Two project members whose names both match "Priya"
        self.add_project_member("Priya Sharma", "priya.sharma@example.com")
        self.add_project_member("Priya Nair", "priya.nair@example.com")

        mock_parse.return_value = (
            MagicMock(),
            {
                "title": "Fix the bug",
                "description": "",
                "due_date": "",
                "priority": "high",
                "assignee_name": "Priya"
            }
        )

        result = self.call(
            "POST",
            f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
            self.token,
            422,
            json={"input": "Fix the bug, assign to Priya"}
        )

        self.assertEqual(result["error"], "ASSIGNEE_AMBIGUOUS")
        self.assertEqual(result["ai_task_request"]["status"], "assignee_ambiguous")
        self.assertEqual(len(result["assignee_options"]), 2)

    @patch("app.blueprints.ai.routes.db.session.flush")
    @patch("app.blueprints.ai.routes.parse_task_from_text")
    def test_ai_task_creation_failed(self, mock_parse, mock_flush):
        mock_parse.return_value = (
            MagicMock(),
            {
                "title": "Fix the bug",
                "description": "",
                "due_date": "",
                "priority": "high",
                "assignee_name": ""
            }
        )
        mock_flush.side_effect = Exception("simulated database flush failure")

        result = self.call(
            "POST",
            f"/api/projects/{self.project_id}/boards/{self.board_id}/ai-tasks",
            self.token,
            500,
            json={"input": "Fix the bug"}
        )

        self.assertEqual(result["error"], "TASK_CREATION_FAILED")
        self.assertIn("request_id", result)
        self.assertEqual(result["request_id"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)