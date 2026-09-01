#!/usr/bin/env python3
"""Test AI task creation end-to-end"""
import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:5000"

# Step 1: Register a user
unique_id = str(uuid.uuid4())[:8]
user_data = {
    "name": f"AITestUser{unique_id}",
    "email": f"aitest{unique_id}@example.com",
    "password": "testpass123"
}

print("1. Registering user...")
response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
if response.status_code == 201:
    user = response.json()
    token = user["access_token"]
    print(f"OK User registered: {user['user']['email']}")
else:
    print(f"FAIL Registration failed: {response.status_code}")
    print(response.text)
    exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# Step 2: Create a project
print("\n2. Creating project...")
project_data = {"name": "AI Test Project", "description": "Test project for AI tasks"}
response = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=headers)
if response.status_code == 201:
    project = response.json()
    project_id = project["id"]
    print(f"OK Project created: {project_id}")
else:
    print(f"FAIL Project creation failed: {response.status_code}")
    print(response.text)
    exit(1)

# Step 3: Create a board
print("\n3. Creating board...")
board_data = {"name": "AI Test Board", "description": "Test board for AI tasks"}
response = requests.post(f"{BASE_URL}/api/boards/project/{project_id}", json=board_data, headers=headers)
if response.status_code == 201:
    board = response.json()
    board_id = board["id"]
    print(f"OK Board created: {board_id}")
else:
    print(f"FAIL Board creation failed: {response.status_code}")
    print(response.text)
    exit(1)

# Step 4: Test AI task creation
print("\n4. Creating task via AI...")
ai_data = {"input": "Fix the login bug by Friday, high priority"}
response = requests.post(
    f"{BASE_URL}/api/projects/{project_id}/boards/{board_id}/ai-tasks",
    json=ai_data,
    headers=headers
)

if response.status_code == 201:
    result = response.json()
    print("OK AI Task created successfully!")
    print(json.dumps(result, indent=2))
else:
    print(f"FAIL AI Task creation failed: {response.status_code}")
    print(response.text)
