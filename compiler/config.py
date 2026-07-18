"""Compiler configuration system.

Deterministic by default. Configuration is merged from (in increasing priority):
  1. built-in defaults
  2. YAML file (--config)
  3. environment variables (K8S_CC_*)
  4. explicit keyword overrides (CLI)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class CompilerConfig:
    # Corpus
    version: str = "main"
    docs_root: Optional[str] = None          # local path to content/en/docs
    swagger_path: Optional[str] = None       # local path or URL to swagger.json
    include_sections: List[str] = field(default_factory=lambda: ["all"])
    exclude_sections: List[str] = field(default_factory=lambda: ["contribute"])

    # Output
    out_dir: str = "out"
    cache_dir: str = ".k8s_cc_cache"
    emit_json: bool = True
    emit_sqlite: bool = True
    emit_gexf: bool = True
    emit_web: bool = True
    trim_bodies: bool = True
    body_max_chars: int = 4000

    # Behavior
    deterministic: bool = True
    parallelism: int = 4
    incremental: bool = True                 # skip unchanged docs via content hash

    # Optional AI-assisted pass (OFF by default; deterministic always wins)
    enable_ai: bool = False
    ai_passes: Optional[str] = None       # comma list: synthesis,prerequisites,clusters
    ai_url: str = "http://localhost:11434"   # Ollama default (reliable local JSON)
    ai_model: str = "llama3.1:8b"
    ai_timeout_s: float = 60.0

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def as_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        overrides: Optional[Dict] = None,
    ) -> "CompilerConfig":
        data: Dict = {}
        if config_path and os.path.exists(config_path):
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                data.update(yaml.safe_load(f) or {})
        # env overrides
        for k in cls.__dataclass_fields__:  # type: ignore[attr-defined]
            env = os.environ.get("K8S_CC_" + k.upper())
            if env is not None:
                data[k] = _coerce(env)
        if overrides:
            data.update({k: v for k, v in overrides.items() if v is not None})
        # filter to known fields
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**known)


def _coerce(val: str):
    low = val.lower()
    if low in ("true", "1", "yes"):
        return True
    if low in ("false", "0", "no"):
        return False
    try:
        return int(val)
    except ValueError:
        pass
    return val
