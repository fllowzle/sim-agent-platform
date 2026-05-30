# -*- coding: utf-8 -*-
"""COMSOL-specific template store — extends core with COMSOL-aware prompts.
COMSOL 专用模板库 — 扩展 core，增加 COMSOL 感知的提示生成."""

from ..core.template_store import TemplateStore, SimulationTemplate, get_template_store

__all__ = ["TemplateStore", "SimulationTemplate", "get_template_store"]
