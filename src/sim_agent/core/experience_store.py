# -*- coding: utf-8 -*-
"""COMSOL-specific experience store — re-exports core + COMSOL defaults.
COMSOL 专用经验库 — 从 core 导入 + COMSOL 默认路径."""

from ..core.experience_store import ExperienceStore, Experience, get_experience_store

__all__ = ["ExperienceStore", "Experience", "get_experience_store"]
