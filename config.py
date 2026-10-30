"""Load config.yaml. Paths are resolved relative to FULL_CODE/."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path_of(cfg: dict, key: str) -> Path:
    return (ROOT / cfg["paths"][key]).resolve()
