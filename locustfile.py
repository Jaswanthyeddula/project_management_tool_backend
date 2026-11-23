"""
Locust load test for the PM Tool backend.

Run against your deployed Render URL:
    locust -f locustfile.py --host https://project-management-tool-backend-i5vi.onrender.com

Then open http://localhost:8089 in your browser to start a test
(pick number of users + spawn rate from the UI).

Start SMALL (5-10 users) against the free-tier Render instance and
free-tier TiDB — this is meant to explore route behavior, not to
stress-test infra you don't want to overload.
"""

import random
import string

from locust import HttpUser, task, between


def random_string(n=8):
    return "".join(random.choices(string.ascii_lowercase, k=n))


class PMToolUser(HttpUser):
    # Each simulated user waits 1-3s between tasks, like a real person
    wait_time = between(1, 3)

    def on_start(self):
        """Runs once per simulated user: register, login, and set up
        a project/board/task to operate on for the rest of the test."""
        email = f"loadtest_{random_string()}@example.com"
        password = "LoadTest123!"

        # Register a fresh user (avoids clashing with your real test account)
        self.client.post(
            "/api/auth/register",
            json={"name": "Load Test", "email": email, "password": password},
            name="/api/auth/register",
        )

        # Login to get tokens
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login",
        )
        if resp.status_code != 200:
            self.environment.runner.quit()
            return

        data = resp.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create a project to work inside for the rest of this user's session
        resp = self.client.post(
            "/api/projects",
            json={"name": f"Load Test Project {random_string(4)}", "description": "locust test"},
            headers=self.headers,
            name="/api/projects [create]",
        )
        self.project_id = resp.json().get("id") if resp.status_code in (200, 201) else None

        # Create a board inside that project
        self.board_id = None
        if self.project_id:
            resp = self.client.post(
                f"/api/boards/project/{self.project_id}",
                json={"name": f"Board {random_string(4)}"},
                headers=self.headers,
                name="/api/boards/project/[id] [create]",
            )
            self.board_id = resp.json().get("id") if resp.status_code in (200, 201) else None

        # Create a task inside that board
        self.task_id = None
        if self.board_id:
            resp = self.client.post(
                f"/api/boards/{self.board_id}/tasks",
                json={"title": f"Task {random_string(4)}", "description": "locust task"},
                headers=self.headers,
                name="/api/boards/[id]/tasks [create]",
            )
            self.task_id = resp.json().get("id") if resp.status_code in (200, 201) else None

    # ---- Read-heavy tasks (weighted higher — most real traffic is reads) ----

    @task(5)
    def get_me(self):
        self.client.get("/api/auth/me", headers=self.headers, name="/api/auth/me")

    @task(5)
    def get_projects(self):
        self.client.get("/api/projects", headers=self.headers, name="/api/projects [list]")

    @task(4)
    def get_project_detail(self):
        if self.project_id:
            self.client.get(
                f"/api/projects/{self.project_id}",
                headers=self.headers,
                name="/api/projects/[id]",
            )

    @task(4)
    def get_boards(self):
        if self.project_id:
            self.client.get(
                f"/api/boards/project/{self.project_id}",
                headers=self.headers,
                name="/api/boards/project/[id] [list]",
            )

    @task(4)
    def get_board_tasks(self):
        if self.board_id:
            self.client.get(
                f"/api/boards/{self.board_id}/tasks",
                headers=self.headers,
                name="/api/boards/[id]/tasks [list]",
            )

    @task(3)
    def get_task_detail(self):
        if self.task_id:
            self.client.get(
                f"/api/tasks/{self.task_id}",
                headers=self.headers,
                name="/api/tasks/[id]",
            )

    @task(2)
    def get_notifications(self):
        self.client.get("/api/notifications", headers=self.headers, name="/api/notifications")

    # ---- Write tasks (lower weight — writes are rarer than reads) ----

    @task(2)
    def add_comment(self):
        if self.task_id:
            self.client.post(
                f"/api/tasks/{self.task_id}/comments",
                json={"content": f"Load test comment {random_string(6)}"},
                headers=self.headers,
                name="/api/tasks/[id]/comments [create]",
            )

    @task(1)
    def update_task(self):
        if self.task_id:
            self.client.patch(
                f"/api/tasks/{self.task_id}",
                json={"title": f"Updated {random_string(4)}"},
                headers=self.headers,
                name="/api/tasks/[id] [update]",
            )

    @task(1)
    def create_label(self):
        if self.project_id:
            self.client.post(
                f"/api/projects/{self.project_id}/labels",
                json={"name": random_string(5), "color": "#3498db"},
                headers=self.headers,
                name="/api/projects/[id]/labels [create]",
            )


class HealthCheckUser(HttpUser):
    """A lightweight user that just hits /health repeatedly — useful to
    see baseline latency separate from DB-touching endpoints."""
    wait_time = between(1, 2)
    weight = 1  # spawn far fewer of these relative to PMToolUser

    @task
    def health(self):
        self.client.get("/health", name="/health")
