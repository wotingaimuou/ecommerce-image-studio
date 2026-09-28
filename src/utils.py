"""Bounded UTF-8 IO and exclusive output writes."""
import json
from pathlib import Path
from typing import Any


class BriefError(ValueError):
    """A user-correctable contract failure."""


def load_json(path: Path, max_bytes: int) -> Any:
    with path.open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise BriefError(f"输入超过 {max_bytes} bytes")
    return json.loads(raw.decode("utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def text_field(value: Any, field: str, limit: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise BriefError(f"{field} 必须为{'可空' if empty else '非空'}字符串")
    if len(value) > limit or "\x00" in value:
        raise BriefError(f"{field} 过长或含 NUL")
    return value.strip()


def keys(value: Any, allowed: set[str], field: str) -> dict:
    if not isinstance(value, dict):
        raise BriefError(f"{field} 必须为对象")
    unknown = set(value) - allowed
    if unknown:
        raise BriefError(f"{field} 未知字段: {sorted(unknown)}")
    return value
