from __future__ import annotations

FIELD_LABELS = {
    "front": "Term",
    "back": "Definition",
    "forms": "Word Forms",
    "example": "Example",
    "image_path": "Image",
}


def label_for(key: str) -> str:
    return FIELD_LABELS.get(key, key.replace("_", " ").title())


def suggest_layout(available_keys: list[str]) -> tuple[list[str], list[str]]:
    """A reasonable default split of available field keys into (front, back)."""
    front = ["front"] if "front" in available_keys else available_keys[:1]
    back = [k for k in available_keys if k not in front]
    return front, back
