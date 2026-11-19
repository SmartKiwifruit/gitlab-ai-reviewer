import pytest


@pytest.fixture
def sample_mr_payload():
    return {
        "object_kind": "merge_request",
        "object_attributes": {
            "iid": 42,
            "action": "open",
            "target_branch": "main",
            "source_branch": "feature-1",
            "title": "Add user auth",
            "state": "opened",
        },
        "project": {"id": 100},
    }


@pytest.fixture
def sample_mr_diff():
    return {
        "base_commit_sha": "base123",
        "head_commit_sha": "head456",
        "start_commit_sha": "start789",
        "changes": [
            {
                "old_path": "src/user.py",
                "new_path": "src/user.py",
                "new_file": False,
                "renamed_file": False,
                "deleted_file": False,
                "diff": "@@ -10,6 +10,15 @@\n import os\n+def insecure_query(username):\n+    return f\"SELECT * FROM users WHERE name='{username}'\"\n",
            },
            {
                "old_path": "src/handler.py",
                "new_path": "src/handler.py",
                "new_file": False,
                "renamed_file": False,
                "deleted_file": False,
                "diff": "@@ -5,7 +5,8 @@\n def handle_request(req):\n-    process(req)\n+    validate(req)\n+    process(req)\n",
            },
        ],
    }
