import hashlib

import httpx


class GitLabClient:
    """Wrapper around GitLab REST API v4."""

    def __init__(self, url: str, token: str, httpx_client: httpx.Client | None = None):
        self.base_url = url.rstrip("/")
        self.token = token
        self._http = httpx_client or httpx.Client()
        self._http.headers.update({
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json",
        })

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}/api/v4/{path}"

    def get_mr_info(self, project_id: int, mr_iid: int) -> dict:
        """Get MR metadata."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}")
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_mr_diff(self, project_id: int, mr_iid: int) -> dict:
        """Get MR diff changes with commit SHAs."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/changes")
        resp = self._http.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_file_content(self, project_id: int, file_path: str, ref: str) -> str | None:
        """Get file content from a specific branch/ref."""
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe="")
        url = self._api_url(f"projects/{project_id}/repository/files/{encoded_path}")
        resp = self._http.get(url, params={"ref": ref})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        import base64
        data = resp.json()
        return base64.b64decode(data["content"]).decode("utf-8")

    def list_tree(self, project_id: int, prefix: str, ref: str) -> list[dict]:
        """List repository tree items."""
        url = self._api_url(f"projects/{project_id}/repository/tree")
        resp = self._http.get(url, params={"path": prefix, "ref": ref, "recursive": True})
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()

    def get_mr_labels(self, project_id: int, mr_iid: int) -> list[str]:
        """Get current labels on an MR."""
        info = self.get_mr_info(project_id, mr_iid)
        return info.get("labels", [])

    def add_label(self, project_id: int, mr_iid: int, label: str):
        """Add a label to an MR."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}")
        existing = self.get_mr_labels(project_id, mr_iid)
        if label not in existing:
            existing.append(label)
        self._http.put(url, json={"labels": ",".join(existing)})

    def remove_label(self, project_id: int, mr_iid: int, label: str):
        """Remove a label from an MR."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}")
        existing = self.get_mr_labels(project_id, mr_iid)
        if label in existing:
            existing.remove(label)
        self._http.put(url, json={"labels": ",".join(existing)})

    def has_manual_override(self, project_id: int, mr_iid: int) -> bool:
        """Check if MR has manual override label."""
        labels = self.get_mr_labels(project_id, mr_iid)
        return "AI-Review: Manual Override" in labels

    def post_line_comment(self, project_id: int, mr_iid: int, file_path: str, line: int, body: str,
                          base_sha: str = "", head_sha: str = "", start_sha: str = "",
                          old_line: int | str | None = None, is_modified: bool = False):
        """Post a line comment on MR diff.

        old_line types:
        - int: context line (use with line_code)
        - '' (empty str): modified line (use with line_code)
        - None: pure addition (no old_line, no line_code)
        """
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/discussions")
        position = {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "start_sha": start_sha,
            "position_type": "text",
            "new_path": file_path,
            "new_line": line,
        }
        if old_line is not None:
            position["old_line"] = old_line
            # GitLab requires line_code when old_line is present
            line_code = hashlib.sha1(f"{file_path}_{old_line}_{line}".encode()).hexdigest()
            position["line_code"] = line_code
        resp = self._http.post(url, json={"body": body, "position": position})
        resp.raise_for_status()

    def post_mr_comment(self, project_id: int, mr_iid: int, body: str) -> int:
        """Post a top-level comment on the MR. Returns the note ID."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/discussions")
        resp = self._http.post(url, json={"body": body})
        resp.raise_for_status()
        notes = resp.json().get("notes", [])
        return notes[0]["id"] if notes else 0

    def update_mr_comment(self, project_id: int, mr_iid: int, note_id: int, body: str):
        """Update an existing MR comment by note ID."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/notes/{note_id}")
        self._http.put(url, json={"body": body})

    def accept_mr(self, project_id: int, mr_iid: int, sha: str) -> dict:
        """Accept (merge) an MR. Returns the merged MR info."""
        url = self._api_url(f"projects/{project_id}/merge_requests/{mr_iid}/merge")
        resp = self._http.put(url, json={"sha": sha})
        resp.raise_for_status()
        return resp.json()
