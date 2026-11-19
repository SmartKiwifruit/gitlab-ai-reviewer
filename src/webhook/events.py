from dataclasses import dataclass
from enum import Enum


class MREventAction(str, Enum):
    OPEN = "open"
    UPDATE = "update"
    REOPEN = "reopen"
    APPROVE = "approved"
    UNAPPROVE = "unapproved"


@dataclass
class MergeRequestEvent:
    project_id: int
    mr_iid: int
    action: MREventAction
    target_branch: str
    source_branch: str
    title: str

    @classmethod
    def from_payload(cls, payload: dict) -> "MergeRequestEvent | None":
        if payload.get("object_kind") != "merge_request":
            return None

        attrs = payload.get("object_attributes", {})
        action_str = attrs.get("action", "")

        try:
            action = MREventAction(action_str)
        except ValueError:
            return None

        return cls(
            project_id=payload["project"]["id"],
            mr_iid=attrs["iid"],
            action=action,
            target_branch=attrs["target_branch"],
            source_branch=attrs["source_branch"],
            title=attrs.get("title", ""),
        )
