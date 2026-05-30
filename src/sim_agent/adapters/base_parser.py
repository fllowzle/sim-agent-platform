# -*- coding: utf-8 -*-
"""
Base Paper Parser — Software-agnostic PDF-to-parameters extractor.
论文解析器基类 — 软件无关的 PDF → 参数提取器。

To customize for a specific software, override:
要为特定软件定制，覆盖：
  - DOMAIN_KEYWORDS : dict of domain -> [keywords...]
  - PHYSICS_KEYWORDS : dict of physics -> [keywords...]
  - STUDY_KEYWORDS   : dict of study type -> [keywords...]
  - NUMERIC_PATTERNS : list of (regex, param_name, unit_type)
  - BC_KEYWORDS      : dict of BC type -> [keywords...]
"""

from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PaperInfo:
    """Universal paper analysis result / 通用论文分析结果."""
    title: str = ""
    domain: str = ""
    physics_type: str = ""
    dimension: str = ""
    geometry_params: dict[str, str] = field(default_factory=dict)
    material_params: dict[str, str] = field(default_factory=dict)
    boundary_conditions: list[dict] = field(default_factory=list)
    study_type: str = ""
    solver_hints: dict = field(default_factory=dict)
    confidence: str = "low"
    missing_info: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title, "domain": self.domain,
            "physics_type": self.physics_type, "dimension": self.dimension,
            "geometry_params": self.geometry_params,
            "material_params": self.material_params,
            "boundary_conditions": self.boundary_conditions,
            "study_type": self.study_type, "solver_hints": self.solver_hints,
            "confidence": self.confidence, "missing_info": self.missing_info,
        }


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract plain text from PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF required: pip install pymupdf")
    doc = fitz.open(str(pdf_path))
    full_text = []
    for page in doc:
        full_text.append(page.get_text())
    doc.close()
    return "\n".join(full_text)


class BasePaperParser:
    """Base class for paper parsers. Override class attributes for customization.
    论文解析器基类。覆盖类属性即可定制。"""

    # === Override these for each software / 为每个软件覆盖以下内容 ===

    DOMAIN_KEYWORDS: dict[str, list[str]] = {
        "generic": ["simulation", "numerical", "FEM", "finite element"],
    }

    PHYSICS_KEYWORDS: dict[str, list[str]] = {
        "generic": [],
    }

    STUDY_KEYWORDS: dict[str, list[str]] = {
        "stationary": ["stationary", "steady state", "static"],
        "eigenfrequency": ["eigenfrequency", "modal", "natural frequency"],
        "transient": ["transient", "time dependent", "time domain"],
    }

    NUMERIC_PATTERNS: list[tuple] = [
        (r"(?:length|size)\s*(?:\w*\s*[=＝]\s*)?(\d+\.?\d*)\s*(nm|um|mm|cm|m)", "length", "length"),
    ]

    BC_KEYWORDS: dict[str, list[str]] = {
        "fixed": ["fixed", "clamped", "constrained"],
        "free": ["free", "unconstrained"],
    }

    DIMENSION_2D_KW = ["2D", "two-dimensional"]
    DIMENSION_3D_KW = ["3D", "three-dimensional"]

    # === Methods / 方法 ===

    def scan_domain(self, text: str) -> dict:
        """Scan text to identify physics domain. / 扫描文本识别物理领域."""
        text_lower = text.lower()
        result = {"domain": "unknown", "physics": "unknown", "study": "unknown", "confidence": "low"}

        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                domain_scores[domain] = score
        if domain_scores:
            best = max(domain_scores, key=domain_scores.get)
            result["domain"] = best
            result["confidence"] = "medium" if domain_scores[best] >= 3 else "low"

        phys_scores = {}
        for phys, keywords in self.PHYSICS_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                phys_scores[phys] = score
        if phys_scores:
            result["physics"] = max(phys_scores, key=phys_scores.get)

        study_scores = {}
        for study, keywords in self.STUDY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                study_scores[study] = score
        if study_scores:
            result["study"] = max(study_scores, key=study_scores.get)

        return result

    def extract_params(self, text: str) -> dict[str, str]:
        """Extract numeric parameters using configured regex patterns."""
        params = {}
        for pattern, param_name, unit_type in self.NUMERIC_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                value, unit = matches[0] if isinstance(matches[0], tuple) else (matches[0], "")
                params[param_name] = f"{value}{unit}" if unit else value
        return params

    def scan_bcs(self, text: str) -> list[dict]:
        """Scan for boundary condition keywords."""
        text_lower = text.lower()
        found = []
        for bc_type, keywords in self.BC_KEYWORDS.items():
            matched_kw = [kw for kw in keywords if kw.lower() in text_lower]
            if matched_kw:
                found.append({"type": bc_type, "keywords_found": matched_kw})
        return found

    def detect_dimension(self, text: str) -> str:
        """Detect 2D vs 3D from text."""
        if any(kw in text for kw in self.DIMENSION_2D_KW):
            return "2D"
        if any(kw in text for kw in self.DIMENSION_3D_KW):
            return "3D"
        return "2D"

    def parse(self, pdf_path: Optional[Path] = None, text: str = "", title: str = "") -> PaperInfo:
        """Main entry: parse paper from PDF or text."""
        if pdf_path:
            text = extract_text_from_pdf(pdf_path)
            title = title or pdf_path.stem

        info = PaperInfo(title=title)
        scan = self.scan_domain(text)
        info.domain = scan["domain"]
        info.physics_type = scan["physics"]
        info.study_type = scan["study"]
        info.confidence = scan["confidence"]
        info.geometry_params = self.extract_params(text)
        info.boundary_conditions = self.scan_bcs(text)
        info.dimension = self.detect_dimension(text)

        if not info.geometry_params:
            info.missing_info.append("geometry params")
        if not info.boundary_conditions:
            info.missing_info.append("boundary conditions")
        if info.study_type == "unknown":
            info.missing_info.append("study type")
        if info.domain == "unknown":
            info.missing_info.append("domain (may need manual specification)")

        return info

    def format_for_agent(self, info: PaperInfo) -> str:
        """Format PaperInfo as agent-readable text."""
        lines = [
            f"## Paper: {info.title}",
            f"- Domain: {info.domain} (confidence: {info.confidence})",
            f"- Physics: {info.physics_type}",
            f"- Dimension: {info.dimension}",
            f"- Study type: {info.study_type}",
        ]
        if info.geometry_params:
            lines.append("\n### Extracted params")
            for k, v in info.geometry_params.items():
                lines.append(f"  - {k}: {v}")
        if info.boundary_conditions:
            lines.append("\n### Boundary conditions")
            for bc in info.boundary_conditions:
                lines.append(f"  - {bc['type']}")
        if info.missing_info:
            lines.append("\n### Missing (needs confirmation)")
            for m in info.missing_info:
                lines.append(f"  - {m}")
        return "\n".join(lines)


# Default instance for quick use
default_parser = BasePaperParser()
