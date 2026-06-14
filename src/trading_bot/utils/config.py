from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]


def load_config(path: str | Path = None) -> dict:
    cfg_path = Path(path) if path else ROOT / 'config' / 'universe.yml'
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
