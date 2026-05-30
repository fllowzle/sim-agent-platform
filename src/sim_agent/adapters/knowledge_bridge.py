# -*- coding: utf-8 -*-
u"""Universal Knowledge Bridge — software-agnostic multi-source knowledge integration.
通用知识桥 — 软件无关的多源知识集成。

This is the base class. For each software, subclass and configure:
这是基类。为每个软件创建子类并配置：

  class ComsolKnowledgeBridge(KnowledgeBridge):
      GUIDES_DIR = Path("D:/comsol-mcp/src/knowledge/prompts")
      PDF_MODULES_DIR = Path("D:/comsol-mcp/pdf")
      PDF_RELEVANCE_MAP = {"photonic_crystal": ["Wave_Optics", "RF_Module"], ...}

Architecture / 架构:
  Priority 1: ExperienceStore (correction memory)
  Priority 2: TemplateStore  (template pitfalls)
  Priority 3: Embedded Guides (Markdown manuals)
  Priority 4: PDF Search    (semantic vector search)
  Priority 5: Topic Guides  (structured physics/config guides)

When used with Codex + McpWizard:
  Step 1-6 creates the agent project
  Step 7 (new!): "Now set up your knowledge base. Where are the PDFs?"
  wizard auto-configures the bridge paths
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class KnowledgeBridge:
    u"""Universal knowledge bridge.

    Subclass and set:
    - GUIDES_DIR: path to Markdown documentation files
    - PDF_MODULES_DIR: path to PDF module directories
    - PDF_RELEVANCE_MAP: domain -> [relevant module names]
    - PHYSICS_TOPICS: {topic_name: {tips: [...], expressions: [...], ...}}
    """

    # === Override in subclass / 子类中覆盖 ===

    GUIDES_DIR: Path = Path(".")
    u"""Directory containing Markdown (.md) guide files."""
    
    PDF_MODULES_DIR: Path = Path(".")
    u"""Directory containing PDF module subdirectories."""

    PDF_RELEVANCE_MAP: dict[str, list[str]] = {}
    u"""Mapping: domain_name -> list of relevant PDF module names."""

    PHYSICS_TOPICS: dict[str, dict] = {}
    u"""Physics topic guides: {topic: {tips: [...], bc_types: [...], ...}}."""

    DOC_FILES: dict[str, dict] = {}
    u"""Known documentation files: {name: {file: str, title: str, description: str}}."""

    # === Implementation / 实现 ===

    def __init__(self):
        self._guides_cache: dict[str, str] = {}
        self._loaded = False

    # ---- Priority 1+2: Local stores ----

    def _get_experiences(self, domain: str, keywords: list[str] = None) -> list[dict]:
        u"""Get relevant correction experiences. Override if experience store path differs."""
        try:
            from ..core.experience_store import get_experience_store
            store = get_experience_store()
            if keywords:
                return [
                    {"trigger": e.trigger, "symptom": e.symptom, "fix": e.fix, "verified": e.verified_count}
                    for e in store.find_relevant(domain, keywords)
                ]
            return [
                {"trigger": e.trigger, "symptom": e.symptom, "fix": e.fix, "verified": e.verified_count}
                for e in store.find_by_domain(domain)
            ]
        except Exception:
            return []

    def _get_template_pitfalls(self, domain: str) -> list[str]:
        u"""Get common pitfalls from templates."""
        try:
            from ..core.template_store import get_template_store
            store = get_template_store()
            templates = store.find_by_domain(domain)
            pitfalls = []
            for t in templates:
                pits = t.to_dict().get("common_pitfalls", [])
                pitfalls.extend(pits)
            return pitfalls
        except Exception:
            return []

    # ---- Priority 3: Embedded guides ----

    def _load_guides(self):
        u"""Load all Markdown guides into cache."""
        if self._loaded:
            return
        if self.GUIDES_DIR.exists():
            for md_file in self.GUIDES_DIR.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    self._guides_cache[md_file.stem] = content
                except Exception:
                    pass
        self._loaded = True

    def get_embedded_doc(self, topic: str) -> Optional[str]:
        u"""Get embedded documentation by topic name."""
        self._load_guides()
        return self._guides_cache.get(topic)

    def list_embedded_docs(self) -> list[str]:
        u"""List available documentation topics."""
        self._load_guides()
        return list(self._guides_cache.keys())

    def search_guides(self, keywords: list[str]) -> list[dict]:
        u"""Search embedded guides for matching keywords."""
        self._load_guides()
        results = []
        for name, content in self._guides_cache.items():
            content_lower = content.lower()
            score = sum(1 for kw in keywords if kw.lower() in content_lower)
            if score > 0:
                paragraphs = content.split("\n\n")
                relevant_paras = []
                for p in paragraphs:
                    if any(kw.lower() in p.lower() for kw in keywords):
                        relevant_paras.append(p.strip()[:300])
                results.append({
                    "source": "guide",
                    "name": name,
                    "score": score,
                    "snippets": relevant_paras[:3],
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ---- Priority 4: PDF modules ----

    def list_pdf_modules(self) -> list[str]:
        u"""List all available PDF modules."""
        if not self.PDF_MODULES_DIR.exists():
            return []
        return sorted([d.name for d in self.PDF_MODULES_DIR.iterdir() if d.is_dir()])

    def find_relevant_pdf(self, domain: str) -> list[str]:
        u"""Find relevant PDF modules for a domain."""
        candidates = self.PDF_RELEVANCE_MAP.get(domain, [])
        all_mods = self.list_pdf_modules()
        relevant = []
        for mod in all_mods:
            if any(c.lower() in mod.lower() for c in candidates):
                relevant.append(mod)
        return relevant if relevant else all_mods[:5]

    # ---- Priority 5: Physics topics ----

    def get_physics_topic(self, physics_type: str) -> Optional[dict]:
        u"""Get physics topic guide."""
        for topic_name, topic_data in self.PHYSICS_TOPICS.items():
            if physics_type.lower() in topic_name.lower():
                return {"topic": topic_name, "data": topic_data}
        return None

    def list_physics_topics(self) -> list[str]:
        u"""List all available physics topics."""
        return list(self.PHYSICS_TOPICS.keys())

    def get_doc_info(self, name: str) -> Optional[dict]:
        u"""Get documentation file metadata."""
        return self.DOC_FILES.get(name)

    def list_doc_names(self) -> list[str]:
        u"""List all known doc file names."""
        return list(self.DOC_FILES.keys())

    # ==================================================================
    # Unified query / 统一查询
    # ==================================================================

    def query(self, question: str, domain: str = "", top_k: int = 5) -> dict:
        u"""Unified knowledge query across all sources.

        Args:
            question: Natural language question
            domain:   Physics domain for filtering
            top_k:    Max results per source

        Returns:
            {question, domain, results: {experiences, pitfalls, guides, topics, pdf_modules}, summary}
        """
        keywords = [w.lower() for w in re.findall(r'\w+', question) if len(w) > 2]

        results = {
            "experiences": [],
            "template_pitfalls": [],
            "embedded_guides": [],
            "physics_topics": [],
            "pdf_modules": [],
        }

        # Priority 1: Experiences
        if domain:
            exps = self._get_experiences(domain, keywords[:5])
            results["experiences"] = [
                {"trigger": e["trigger"], "fix": e["fix"], "verified": e["verified"]}
                for e in exps[:top_k]
            ]

        # Priority 2: Template pitfalls
        if domain:
            pitfalls = self._get_template_pitfalls(domain)
            relevant_pitfalls = []
            for p in pitfalls:
                if any(kw in p.lower() for kw in keywords):
                    relevant_pitfalls.append(p)
            results["template_pitfalls"] = relevant_pitfalls[:top_k]

        # Priority 3: Embedded guides
        results["embedded_guides"] = self.search_guides(keywords)[:top_k]

        # Priority 4: Physics topics
        for kw in keywords:
            topic = self.get_physics_topic(kw)
            if topic and topic not in results["physics_topics"]:
                results["physics_topics"].append(topic)

        # Priority 5: PDF modules
        results["pdf_modules"] = self.find_relevant_pdf(domain)[:top_k]

        # Generate summary
        summary = self._generate_summary(results, question)
        results["summary"] = summary

        return {"question": question, "domain": domain, "results": results, "summary": summary}

    def _generate_summary(self, results: dict, question: str) -> str:
        u"""Generate concise LLM-readable summary."""
        parts = []

        experiences = results.get("experiences", [])
        if experiences:
            parts.append("## Relevant Experiences")
            for e in experiences[:3]:
                parts.append("- {} -> Fix: {}".format(e['trigger'], e['fix']))

        pitfalls = results.get("template_pitfalls", [])
        if pitfalls:
            parts.append("\n## Common Pitfalls")
            for p in pitfalls[:3]:
                parts.append("- " + p)

        guides = results.get("embedded_guides", [])
        if guides:
            parts.append("\n## Documentation")
            for g in guides[:2]:
                snippets = "; ".join(g.get('snippets', [])[:2])
                parts.append("- " + g['name'] + ": " + snippets)

        topics = results.get("physics_topics", [])
        if topics:
            parts.append("\n## Physics Guides")
            for t in topics[:2]:
                tips = t.get("data", {}).get("tips", [])
                if tips:
                    parts.append("- " + t['topic'] + ": " + tips[0])

        modules = results.get("pdf_modules", [])
        if modules:
            parts.append("\n## Relevant PDF Modules")
            parts.append("- " + ", ".join(modules[:3]))

        if not parts:
            return "No relevant knowledge found. Try rephrasing or specify domain."

        return "\n".join(parts)

    # ==================================================================
    # Full context / 完整上下文
    # ==================================================================

    def get_full_context(self, domain: str = "", topic: str = "") -> str:
        u"""Generate complete LLM context combining all sources."""
        parts = []

        try:
            from ..core.template_store import get_template_store
            from ..core.experience_store import get_experience_store

            if domain:
                templates = get_template_store().find_by_domain(domain)
                if templates:
                    parts.append("## Available Templates")
                    for t in templates:
                        parts.append("- {}: {}, {}, study={}".format(
                            t.name, t.physics_type, t.dimension, t.to_dict()['study_type']))

                exp_ctx = get_experience_store().get_prompt_context(domain)
                if exp_ctx:
                    parts.append(exp_ctx)
        except Exception:
            pass

        parts.append("\n## Embedded Knowledge")
        for doc_name in self.list_embedded_docs():
            doc = self.get_embedded_doc(doc_name)
            if doc and topic and topic.lower() in doc.lower():
                parts.append("\n### " + doc_name)
                parts.append(doc[:2000] + "\n...(truncated)")
            elif doc and not topic:
                parts.append("\n### {} (available - {} chars)".format(doc_name, len(doc)))

        parts.append("\n## Physics Topics")
        topics = self.list_physics_topics()
        parts.append("- " + (", ".join(topics) if topics else "(none configured)"))

        parts.append("\n## PDF Modules")
        if domain:
            relevant = self.find_relevant_pdf(domain)
            parts.append("- Relevant: " + ", ".join(relevant[:5]))
        else:
            modules = self.list_pdf_modules()
            parts.append("- {} modules available".format(len(modules)))

        return "\n".join(parts)

    # ==================================================================
    # Status / 状态
    # ==================================================================

    def status_report(self) -> dict:
        u"""Report knowledge base status."""
        self._load_guides()
        return {
            "embedded_docs": len(self._guides_cache),
            "embedded_doc_names": list(self._guides_cache.keys()),
            "pdf_modules": len(self.list_pdf_modules()),
            "physics_topics": self.list_physics_topics(),
            "doc_files": self.list_doc_names(),
        }

    # ==================================================================
    # Wizard integration / 向导集成
    # ==================================================================

    @classmethod
    def wizard_questions(cls) -> list[dict]:
        u"""Generate Step 7 wizard questions for KnowledgeBridge setup.
        生成 Step 7 向导问题 — KnowledgeBridge 知识桥路径配置。

        These questions ask the user to specify where their software's
        documentation lives, so the generated agent can auto-consult manuals.
        这些问题询问用户软件文档的存储位置，生成的 Agent 将自动查阅手册。
        """
        return [
            {
                "step": 7,
                "id": "knowledge",
                "title": "Step 7: KnowledgeBridge Setup / KnowledgeBridge 知识桥配置 \u2605",
                "description": "Where does your software keep its documentation? The agent will build a bridge to auto-query these sources. / 你的软件文档在哪里？Agent 将建桥自动查询这些来源。",
                "questions": [
                    {
                        "id": "guides_dir",
                        "ask": "Q7.1: Path to Markdown guides (.md) for this software? / 软件的 Markdown 指南文档 (.md) 路径？\n  (Absolute path like D:/.../guides/  |  'skip' if none  |  如无可填 'skip')",
                        "example": "D:/ansys/docs/guides/  or  skip",
                        "target_field": "kb_guides_dir",
                    },
                    {
                        "id": "pdf_dir",
                        "ask": "Q7.2: Path to PDF reference manuals? / PDF 参考手册路径？\n  (Will be vector-indexed for semantic search via ChromaDB / 将通过 ChromaDB 建立向量索引用于语义搜索)\n  (Absolute path like D:/.../pdf/  |  'skip' if none)",
                        "example": "D:/ansys/pdf/  or  skip",
                        "target_field": "kb_pdf_dir",
                    },
                    {
                        "id": "pdf_relevance",
                        "ask": "Q7.3: Map each physics domain to relevant PDF module folders? / 每个物理领域对应哪些 PDF 模块文件夹？\n  Format: domain_name: [module_folder1, module_folder2, ...]\n  (One line per domain  |  每个领域一行  |  'skip' if none)",
                        "example": "structural: [Structural_Analysis, Material_Models]\nthermal: [Thermal_Analysis, CFD]\nelectromagnetic: [EM_Analysis, RF_Module]",
                        "target_field": "kb_relevance_map",
                    },
                ],
            },
        ]