"""Load bounded local configuration; no credentials are needed."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    max_input_bytes: int = 1048576
    max_text_chars: int = 12000
    max_assets: int = 64
    max_references_per_asset: int = 5
    max_image_bytes: int = 52428800
    max_image_pixels: int = 40000000
    aspect_tolerance: float = 0.035
    max_transient_retries: int = 2

    @classmethod
    def load(cls, path: Path) -> "Config":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError("配置含未知字段或格式错误")
        cfg = cls(**data)
        for key, value in vars(cfg).items():
            if key == "aspect_tolerance":
                if type(value) not in (int, float) or not 0 <= value <= 0.2:
                    raise ValueError("aspect_tolerance 应在 0 到 0.2")
            elif type(value) is not int or value < (0 if key == "max_transient_retries" else 1):
                raise ValueError(f"配置 {key} 必须为有效整数")
        return cfg
