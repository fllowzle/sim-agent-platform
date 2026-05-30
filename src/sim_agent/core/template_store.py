# -*- coding: utf-8 -*-
"""
Universal Template Store — Software-agnostic YAML template management.
通用模板库 — 软件无关的 YAML 模板管理系统。

Supports: CRUD, fuzzy matching, parameter extraction, prompt generation.
支持：增删改查、模糊匹配、参数提取、提示生成。
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class SimulationTemplate:
    """Single simulation template / 单个仿真模板."""
    name: str
    domain: str
    physics_type: str
    dimension: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "SimulationTemplate":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        meta = raw.get("meta", {})
        return cls(
            name=meta.get("name", path.stem),
            domain=meta.get("domain", "unknown"),
            physics_type=meta.get("physics_type", "unknown"),
            dimension=meta.get("dimension", "2D"),
            raw=raw,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "physics_type": self.physics_type,
            "dimension": self.dimension,
            "geometry": self._geo_summary(),
            "boundary_conditions": list(self.raw.get("boundary_conditions", {}).keys()),
            "study_type": self.raw.get("study", {}).get("type", "unknown"),
            "common_pitfalls": self.raw.get("meta", {}).get("common_pitfalls", []),
        }

    def _geo_summary(self) -> dict:
        geo = self.raw.get("geometry", {})
        return {
            "unit_cell_type": geo.get("unit_cell", geo.get("model", {})).get("type", "unknown"),
            "scatterer_type": geo.get("scatterer", {}).get("type", "unknown"),
        }

    def extract_parameters(self) -> dict[str, dict]:
        """Recursively extract all {symbol, default} params from geometry/physics/mesh/study."""
        params = {}
        for section in ["geometry", "physics", "mesh", "study"]:
            params.update(self._walk(self.raw.get(section, {})))
        return params

    def _walk(self, data: dict, prefix: str = "") -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                if "symbol" in value and "default" in value:
                    result[value["symbol"]] = {
                        "default": value["default"],
                        "description": value.get("description", ""),
                    }
                else:
                    result.update(self._walk(value, f"{prefix}.{key}".strip(".")))
        return result


class TemplateStore:
    """Manages simulation template loading, retrieval, matching, and saving.
    管理仿真模板的加载、检索、匹配和保存。"""

    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.templates_dir = Path(templates_dir)
        self._templates: dict[str, SimulationTemplate] = {}
        self._by_domain: dict[str, list[str]] = {}
        self._loaded = False

    def load_all(self) -> int:
        self._templates.clear()
        self._by_domain.clear()
        count = 0
        if self.templates_dir.exists():
            for yf in self.templates_dir.rglob("*.yaml"):
                try:
                    t = SimulationTemplate.from_yaml(yf)
                    self._templates[t.name] = t
                    self._by_domain.setdefault(t.domain, []).append(t.name)
                    count += 1
                except Exception as e:
                    print(f"[TemplateStore] skip {yf}: {e}")
        self._loaded = True
        return count

    def list_all(self) -> list[dict]:
        if not self._loaded: self.load_all()
        return [t.to_dict() for t in self._templates.values()]

    def list_domains(self) -> list[str]:
        if not self._loaded: self.load_all()
        return list(self._by_domain.keys())

    def get(self, name: str) -> Optional[SimulationTemplate]:
        if not self._loaded: self.load_all()
        return self._templates.get(name)

    def find_by_domain(self, domain: str) -> list[SimulationTemplate]:
        if not self._loaded: self.load_all()
        return [self._templates[n] for n in self._by_domain.get(domain, []) if n in self._templates]

    def match(self, query: dict) -> Optional[SimulationTemplate]:
        """Scoring-based fuzzy matching / 计分制模糊匹配."""
        if not self._loaded: self.load_all()
        d, p, dim = query.get("domain", ""), query.get("physics", "").lower(), query.get("dimension", "")
        scores = []
        for t in self._templates.values():
            s = 0
            if d and d in t.domain: s += 3
            if p and p in t.physics_type.lower(): s += 2
            if dim and dim == t.dimension: s += 1
            if s > 0: scores.append((s, t))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1] if scores else None

    def get_prompt_context(self, name: str) -> str:
        t = self.get(name)
        if t is None: return f"[error] template not found: {name}"
        pitfalls = "\n".join(f"  - {p}" for p in t.to_dict().get("common_pitfalls", []))
        params = t.extract_parameters()
        pl = "\n".join(f"  - {k}: {v['default']}  # {v['description']}" for k, v in params.items())
        return f"""
## Template: {t.name}
- Domain: {t.domain}
- Physics: {t.physics_type}
- Dimension: {t.dimension}
- Study: {t.to_dict()['study_type']}

### Parameters
{pl}

### Common Pitfalls
{pitfalls}
""".strip()

    def save(self, template: SimulationTemplate, filename: Optional[str] = None) -> Path:
        domain_dir = self.templates_dir / template.domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"{template.name.replace(' ', '_').lower()}.yaml"
        path = domain_dir / fname
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(template.raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self._templates[template.name] = template
        self._by_domain.setdefault(template.domain, []).append(template.name)
        return path


_template_store: Optional[TemplateStore] = None


def get_template_store() -> TemplateStore:
    global _template_store
    if _template_store is None:
        _template_store = TemplateStore()
        _template_store.load_all()
    return _template_store
