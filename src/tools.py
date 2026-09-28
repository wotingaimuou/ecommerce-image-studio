"""Image integrity, auditable QA receipts, and host error classification."""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from .config import Config
from .utils import BriefError, keys, text_field, write_json

LOG = logging.getLogger(__name__)


def inspect_image(path: Path, cfg: Config) -> dict:
    if path.stat().st_size > cfg.max_image_bytes:
        raise BriefError("图片文件过大")
    try:
        with Image.open(path) as im:
            width, height = im.size
            if width * height > cfg.max_image_pixels:
                raise BriefError("图片像素总量超过配置限制")
            im.verify()
        with Image.open(path) as im:
            im.load()
            has_alpha = "A" in im.getbands() or "transparency" in im.info
            alpha_range = im.convert("RGBA").getchannel("A").getextrema() if has_alpha else (255, 255)
            return {"width": width, "height": height, "format": im.format, "mode": im.mode,
                    "has_transparency": alpha_range[0] < 255,
                    "has_visible_pixels": alpha_range[1] > 0,
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise BriefError(f"无法解码图片: {path.name}") from exc


def validate_references(manifest: dict, cfg: Config) -> None:
    seen = set()
    for asset in manifest["assets"]:
        for path in asset["tool_args"].get("referenced_image_paths", []):
            if path not in seen:
                inspect_image(Path(path), cfg)
                seen.add(path)


def error_action(kind: str, attempt: int, cfg: Config) -> dict:
    """No API call is made here. Unknown outcomes never trigger blind retries."""
    if type(attempt) is not int or attempt < 0:
        raise BriefError("attempt 须为非负整数")
    if kind in {"timeout", "network", "unknown"}:
        return {"retry": False, "action": "inspect_existing_result_then_decide", "reason": "请求结果不明，避免重复生成"}
    if kind in {"rate_limit", "unavailable"}:
        retry = attempt < cfg.max_transient_retries
        return {"retry": retry, "action": "retry_after_service_delay" if retry else "report_failure"}
    if kind in {"permission", "rejected", "bad_input"}:
        return {"retry": False, "action": "report_blocker"}
    raise BriefError("未知错误类型")


def record_image(manifest: dict, asset_id: str, source: Path, qa: Any, out: Path, cfg: Config) -> dict:
    """Save a PNG and receipt only after integrity checks. Human QA is explicit."""
    matches = [a for a in manifest["assets"] if a["id"] == asset_id]
    if len(matches) != 1:
        raise BriefError("asset_id 不存在或重复")
    asset = matches[0]
    if not asset_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in asset_id):
        raise BriefError("非法 asset_id")
    keys(qa, {"reviewer", "appearance", "text", "count", "scene", "people", "notes"}, "qa")
    reviewer = text_field(qa.get("reviewer"), "qa.reviewer", 200)
    notes = text_field(qa.get("notes"), "qa.notes", cfg.max_text_chars)
    for field in ("appearance", "text", "count", "scene", "people"):
        if qa.get(field) not in ("pass", "fail", "not_applicable", "unverified"):
            raise BriefError(f"qa.{field} 状态无效")
    info = inspect_image(source, cfg)
    w, h = map(int, asset["ratio"].split(":"))
    aspect_ok = abs((info["width"] / info["height"]) / (w / h) - 1) <= cfg.aspect_tolerance
    alpha_ok = not asset["tool_args"]["transparent_background"] or info["has_transparency"]
    checks = {"aspect": aspect_ok, "transparency": alpha_ok, "visible_pixels": info["has_visible_pixels"]}
    visual_ok = all(qa[f] in ("pass", "not_applicable") for f in ("appearance", "text", "count", "scene", "people"))
    # SKU count and product identity cannot be waived when they are required.
    if asset["mode"] == "sku-bundle" and qa["count"] != "pass":
        visual_ok = False
    if qa["appearance"] != "pass":
        visual_ok = False
    if asset.get("copy") and qa["text"] != "pass":
        visual_ok = False
    if qa["people"] != "pass":
        visual_ok = False
    state = "accepted" if all(checks.values()) and visual_ok else "needs_review"
    out.mkdir(parents=True, exist_ok=True)
    dest, receipt_path = out / (asset_id + ".png"), out / (asset_id + ".receipt.json")
    if dest.exists() or receipt_path.exists():
        raise FileExistsError("输出已存在，请使用新的版本目录")
    with Image.open(source) as im, dest.open("xb") as stream:
        im.save(stream, format="PNG")
    receipt = {"asset_id": asset_id, "status": state, "source": str(source.resolve()), "output": str(dest.resolve()),
               "source_image": info, "saved_image": inspect_image(dest, cfg), "machine_checks": checks,
               "visual_qa": {**qa, "reviewer": reviewer, "notes": notes}, "platform_rules_verified": False}
    write_json(receipt_path, receipt)
    LOG.info("recorded asset=%s status=%s", asset_id, state)
    return receipt
