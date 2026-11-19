from src.webhook.events import MergeRequestEvent, MREventAction


def test_parse_open_event():
    payload = {
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
    event = MergeRequestEvent.from_payload(payload)
    assert event.project_id == 100
    assert event.mr_iid == 42
    assert event.action == MREventAction.OPEN
    assert event.target_branch == "main"
    assert event.source_branch == "feature-1"
    assert event.title == "Add user auth"


def test_parse_update_event():
    payload = {
        "object_kind": "merge_request",
        "object_attributes": {
            "iid": 42,
            "action": "update",
            "target_branch": "main",
            "source_branch": "feature-1",
            "title": "Add user auth",
            "state": "opened",
        },
        "project": {"id": 100},
    }
    event = MergeRequestEvent.from_payload(payload)
    assert event.action == MREventAction.UPDATE


def test_parse_unsupported_action():
    payload = {
        "object_kind": "merge_request",
        "object_attributes": {
            "iid": 42,
            "action": "merge",
            "target_branch": "main",
            "source_branch": "feature-1",
            "title": "Add user auth",
            "state": "merged",
        },
        "project": {"id": 100},
    }
    event = MergeRequestEvent.from_payload(payload)
    assert event is None  # merge/close actions are ignored


def test_parse_non_mr_event():
    payload = {"object_kind": "push"}
    event = MergeRequestEvent.from_payload(payload)
    assert event is None
