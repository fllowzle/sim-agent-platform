# -*- coding: utf-8 -*-
"""
=============================================================================
MCP Wizard — 引导式仿真 Agent 配置生成器
=============================================================================
Guided setup wizard for creating simulation Agent for ANY software.
引导式配置向导 — 为任意仿真软件创建 Agent。

When used with Codex (via SKILL.md), this wizard asks the user step-by-step:
当通过 Codex (SKILL.md) 使用时，向导会一步步询问用户：

  Step 1: Software identification / 软件识别
    - Software name? (e.g. ANSYS, Lumerical, ABAQUS)
    - Python SDK? CLI? File-driven?

  Step 2: Physics domains / 物理领域
    - What physics does this software handle?
    - What are the typical study types?

  Step 3: Error patterns / 错误模式
    - What are the most common solver errors?
    - What are their typical fixes?

  Step 4: Template seeding / 模板播种
    - What are the most common simulation workflows?
    - Generate the first 3-5 YAML templates

  Step 5: MCP Server generation / MCP 服务器生成
    - Generate a minimal MCP server skeleton
    - Register it in Codex config

  Step 6: Domain keywords / 领域关键词
    - What paper keywords indicate this domain?
    - Register in paper parser

Output / 输出: A complete, ready-to-use Agent for the target software.
输出：一个完整的、即开即用的目标软件 Agent。

Design Principle / 设计原则
----------------------------
This module does NOT execute anything itself. It generates structured
configuration data that Codex/LLM uses to build the actual files.
本模块不自己执行任何操作。它生成结构化配置数据，
Codex/LLM 用这些数据来构建实际文件。
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field


# ==========================================================================
# Data Structures / 数据结构
# ==========================================================================

@dataclass
class SoftwareProfile:
    """Complete configuration profile for a simulation software.
    一个仿真软件的完整配置画像。"""

    # ---- Identity / 身份 ----
    name: str = ""                          # e.g. "ANSYS", "Lumerical", "ABAQUS"
    mcp_server_name: str = ""               # e.g. "ansys-mcp"
    python_sdk: str = ""                    # e.g. "pyansys", "lumapi", ""
    sdk_install: str = ""                   # e.g. "pip install pyansys"
    connection_mode: str = "sdk"            # "sdk" | "cli" | "file_driven" | "com"

    # ---- Physics / 物理 ----
    domains: list[dict] = field(default_factory=list)
    # [{"name": "structural", "label": "Structure Mechanics / 结构力学",
    #   "physics_interfaces": ["StaticStructural", "TransientStructural"],
    #   "study_types": ["stationary", "transient"]}]

    # ---- Error Patterns / 错误模式 ----
    error_patterns: list[dict] = field(default_factory=list)
    # [{"keyword": "rigid body motion", "cause": "...", "fixes": [...]}]

    # ---- Template Seeds / 模板种子 ----
    template_seeds: list[dict] = field(default_factory=list)
    # [{"name": "Cantilever Beam / 悬臂梁", "domain": "structural", ...}]

    # ---- Domain Keywords (for paper parser) / 论文解析关键词 ----
    domain_keywords: dict[str, list[str]] = field(default_factory=dict)
    # {"structural": ["von Mises", "stress", "strain", "FEA", ...]}

    # ---- MCP Tools / MCP 工具 ----
    mcp_tools: list[dict] = field(default_factory=list)
    # [{"name": "ansys_start", "description": "...", "params": [...]}]

    # ---- KnowledgeBridge / 知识桥配置 ----
    kb_guides_dir: str = ""                 # Path to Markdown guides / Markdown 指南路径
    kb_pdf_dir: str = ""                    # Path to PDF manuals / PDF 手册路径
    kb_relevance_map: dict[str, list[str]] = field(default_factory=dict)  # domain→[module_names] / 领域→[模块名]

    # ---- Config / 配置 ----
    config_complete: bool = False           # All steps completed?
    config_steps_done: list[str] = field(default_factory=list)


# ==========================================================================
# Step Definitions / 步骤定义
# ==========================================================================

# Each step is a structured prompt that Codex asks the user.
# 每个步骤是一个结构化提示，Codex 用来向用户提问。

SETUP_STEPS = [

    {
        "step": 7,
        "id": "knowledge",
        "title": "Step 7: KnowledgeBridge Setup / KnowledgeBridge 知识桥配置 ★",
        "description": "Configure where your software documentation lives so the agent can auto-consult manuals. / 配置软件文档位置，Agent 将自动查阅手册。",
        "questions": [
            {
                "id": "guides_dir",
                "ask": "Q7.1: Path to Markdown guides? / Markdown 指南文档的路径？\n  (Absolute path like D:/.../guides/  |  'skip' if none  |  如无可填 'skip')",
                "example": "D:/ansys/docs/guides/  or  skip",
                "target_field": "kb_guides_dir",
            },
            {
                "id": "pdf_dir",
                "ask": "Q7.2: Path to PDF reference manuals? / PDF 参考手册的路径？\n  (These will be vector-indexed for semantic search  |  将建立向量索引用于语义搜索)\n  (Absolute path like D:/.../pdf/  |  'skip' if none)",
                "example": "D:/ansys/pdf/  or  skip",
                "target_field": "kb_pdf_dir",
            },
            {
                "id": "pdf_relevance",
                "ask": "Q7.3: Map each domain to relevant PDF modules? / 每个物理领域对应哪些 PDF 模块？\n  Format: domain_name: [module_folder1, module_folder2, ...]\n  (Separate entries with newline  |  每个领域一行)",
                "example": "structural: [Structural_Analysis, Material_Models]\nthermal: [Thermal_Analysis, CFD]\nelectromagnetic: [EM_Analysis, RF_Module]",
                "target_field": "kb_relevance_map",
            },
        ],
    },
    {
        "step": 1,
        "id": "identity",
        "title": "Step 1: Software Identity / 软件身份",
        "questions": [
            {
                "id": "software_name",
                "ask": "What is the simulation software called? / 仿真软件叫什么名字？",
                "example": "ANSYS Mechanical, Lumerical FDTD, ABAQUS, Gmsh...",
                "target_field": "name",
            },
            {
                "id": "python_sdk",
                "ask": "Does it have a Python SDK? If yes, what's the package name? / 有 Python SDK 吗？包名是什么？",
                "example": "pyansys, lumapi, abaqus (built-in)... or 'none' if only CLI/GUI",
                "target_field": "python_sdk",
            },
            {
                "id": "sdk_install",
                "ask": "How to install the Python SDK? / 如何安装 Python SDK？",
                "example": "pip install pyansys (or 'built-in' if comes with software)",
                "target_field": "sdk_install",
            },
            {
                "id": "connection_mode",
                "ask": "How to connect? / 连接方式？\n  (1) Python SDK\n  (2) Command-line subprocess\n  (3) Input file driven\n  (4) COM/Java API",
                "example": "1",
                "target_field": "connection_mode",
                "transform": lambda x: {"1": "sdk", "2": "cli", "3": "file_driven", "4": "com"}.get(x, "sdk"),
            },
        ],
    },
    {
        "step": 2,
        "id": "physics",
        "title": "Step 2: Physics Domains / 物理领域",
        "questions": [
            {
                "id": "domain_count",
                "ask": "How many physics domains does this software handle? / 这个软件能处理几个物理领域？\n  (List the main ones, e.g. structural, thermal, electromagnetic...)",
                "example": "3: structural mechanics, heat transfer, electromagnetics",
                "target_field": "_raw_domains",
            },
        ],
        "follow_up": "For EACH domain, ask:\n  1. Domain name (snake_case)\n  2. Display label (human readable)\n  3. COMSOL/software physics interface names\n  4. Typical study types (stationary, transient, eigenfrequency...)",
    },
    {
        "step": 3,
        "id": "errors",
        "title": "Step 3: Error Patterns / 错误模式",
        "questions": [
            {
                "id": "error_count",
                "ask": "What are the 5-10 most common solver errors in this software? / 这个软件最常见的 5-10 个求解错误是什么？\n  For each: error keyword → root cause → fixes",
                "example": "1. 'rigid body motion' → insufficient constraints → add fixed supports\n  2. 'negative Jacobian' → bad mesh → remesh with smaller elements\n  ...",
                "target_field": "_raw_errors",
            },
        ],
    },
    {
        "step": 4,
        "id": "templates",
        "title": "Step 4: Template Seeds / 模板播种",
        "questions": [
            {
                "id": "template_count",
                "ask": "What are the 3-5 most typical simulation workflows? / 最典型的 3-5 个仿真流程是什么？\n  For each: name, domain, brief description of steps",
                "example": "1. Cantilever beam analysis → structural → mesh beam → fix one end → apply force → solve\n  2. Heat sink thermal → thermal → mesh → apply heat source → convection BC → solve\n  ...",
                "target_field": "_raw_templates",
            },
        ],
    },
    {
        "step": 5,
        "id": "keywords",
        "title": "Step 5: Paper Keywords / 论文关键词",
        "questions": [
            {
                "id": "keywords_per_domain",
                "ask": "For each physics domain, list keywords that appear in research papers. / 每个物理领域，列出论文中常见的关键词。\n  These help the paper parser auto-detect the domain.",
                "example": "structural: [stress, strain, von Mises, FEA, finite element, displacement, deformation]\n  thermal: [heat flux, temperature, convection, conduction, Nusselt]",
                "target_field": "_raw_keywords",
            },
        ],
    },
    {
        "step": 6,
        "id": "mcp_tools",
        "title": "Step 6: MCP Tools Definition / MCP 工具定义",
        "questions": [
            {
                "id": "core_tools",
                "ask": "What are the 5-10 core operations users perform in this software? / 用户在这个软件中最常用的 5-10 个操作是什么？\n  These become MCP tools.",
                "example": "1. create_geometry(shape, params)\n  2. assign_material(name, properties)\n  3. apply_load(load_type, value, location)\n  4. set_boundary_condition(type, location)\n  5. mesh(size)\n  6. solve()\n  7. get_result(quantity, location)\n  8. export_plot(quantity)",
                "target_field": "_raw_tools",
            },
        ],
    },
]


# ==========================================================================
# Wizard Engine / 向导引擎
# ==========================================================================

class McpWizard:
    """Guided setup wizard for creating simulation agents.
    引导式仿真 Agent 创建向导。

    Usage with Codex / 在 Codex 中使用
    ---------------------------------
    1. User says: "Create an agent for ANSYS"
    2. Codex loads this wizard
    3. wizard starts asking questions step by step
    4. At each step, user answers → wizard builds the profile
    5. At end, wizard generates all files (MCP server, templates, config)

    Usage standalone / 独立使用
    ---------------------------
    wizard = McpWizard()
    wizard.start()                    # Begin the guided setup
    profile = wizard.get_profile()    # Get the completed profile
    files = wizard.generate(profile)  # Generate all files
    """

    def __init__(self):
        self._profile = SoftwareProfile()
        self._current_step = 0

    @property
    def profile(self) -> SoftwareProfile:
        return self._profile

    def get_next_question(self) -> Optional[dict]:
        """Get the next unanswered question. / 获取下一个未回答的问题。
        Returns None if all steps complete. / 如果全部完成则返回 None。
        """
        for step_def in SETUP_STEPS:
            step_id = step_def["id"]
            if step_id in self._profile.config_steps_done:
                continue

            # Find first unanswered question in this step
            for q in step_def.get("questions", []):
                if q["id"] not in self._profile.config_steps_done:
                    return {
                        "step": step_def["step"],
                        "step_id": step_id,
                        "title": step_def["title"],
                        "question": q,
                        "total_steps": len(SETUP_STEPS),
                        "progress": f"Step {step_def['step']}/{len(SETUP_STEPS)}",
                    }

            # All questions in this step answered → mark step done
            self._profile.config_steps_done.append(step_id)

        # All steps done
        self._profile.config_complete = True
        return None

    def answer(self, step_id: str, question_id: str, value: str) -> dict:
        """Record user's answer to a question. / 记录用户对问题的回答。"""
        # Find the step and question
        for step_def in SETUP_STEPS:
            if step_def["id"] != step_id:
                continue
            for q in step_def.get("questions", []):
                if q["id"] != question_id:
                    continue

                # Apply transform if defined
                if "transform" in q:
                    value = q["transform"](value)

                # Set the target field
                setattr(self._profile, q["target_field"], value)
                self._profile.config_steps_done.append(question_id)

                return {
                    "answered": True,
                    "step": step_def["step"],
                    "question": q["ask"].split("\n")[0],
                    "value": str(value),
                    "next": self.get_next_question(),
                }

        return {"answered": False, "error": f"Question not found: {step_id}/{question_id}"}

    def generate_file_plan(self) -> dict:
        """Generate the complete file creation plan.
        生成完整的文件创建计划。

        Returns a structured plan that Codex can execute to create all files.
        返回一个结构化计划，Codex 可以执行来创建所有文件。
        """
        if not self._profile.config_complete:
            return {"error": "Profile not complete. Finish all setup steps first. / 配置未完成，先完成所有设置步骤。"}

        p = self._profile
        snake_name = p.name.lower().replace(" ", "_")

        return {
            "project_name": f"{snake_name}-agent",
            "files_to_create": [
                {
                    "path": "pyproject.toml",
                    "type": "config",
                    "description": f"Python project config for {p.name} Agent",
                },
                {
                    "path": "src/mcp_server/server.py",
                    "type": "mcp_server",
                    "description": f"MCP Server for {p.name} — generated from template",
                    "template": "mcp_server_template.py",
                    "variables": {
                        "SOFTWARE_NAME": p.name,
                        "PYTHON_SDK": p.python_sdk,
                        "SDK_INSTALL": p.sdk_install,
                        "CONNECTION_MODE": p.connection_mode,
                    },
                },
                {
                    "path": "src/agent_config.py",
                    "type": "config",
                    "description": "Software-specific agent configuration / 软件专属 Agent 配置",
                    "content_generator": "agent_config",
                },
                {
                    "path": "templates/",
                    "type": "directory",
                    "description": "Template directory / 模板目录",
                },
                *[
                    {
                        "path": f"templates/{d['name']}/{seed['name'].lower().replace(' ', '_')}.yaml",
                        "type": "template",
                        "description": f"Template: {seed['name']}",
                    }
                    for d in p.domains
                    for seed in p.template_seeds
                    if seed.get("domain") == d["name"]
                ],
                {
                    "path": "skills/SKILL.md",
                    "type": "skill",
                    "description": f"Codex Skill for {p.name} Agent",
                },
                {
                    "path": "README.md",
                    "type": "readme",
                    "description": f"README for {p.name} Agent",
                },
                {
                    "path": "src/knowledge/knowledge_bridge.py",
                    "type": "knowledge_bridge",
                    "description": f"KnowledgeBridge for {p.name} — connects agent to software manuals / 连接 Agent 与软件手册",
                    "template": "base_knowledge_bridge",
                    "variables": {
                        "GUIDES_DIR": p.kb_guides_dir or "SKIP",
                        "PDF_DIR": p.kb_pdf_dir or "SKIP",
                        "PDF_RELEVANCE_MAP": str(p.kb_relevance_map) if p.kb_relevance_map else "{}",
                    },
                },
            ],
            "knowledge_bridge_config": {
                "guides_dir": p.kb_guides_dir or "",
                "pdf_dir": p.kb_pdf_dir or "",
                "pdf_relevance_map": p.kb_relevance_map or {},
            },
            "codex_mcp_config": {
                "mcpServers": {
                    f"{snake_name}": {
                        "command": "python",
                        "args": ["-m", "src.mcp_server.server"],
                        "cwd": f"./{snake_name}-agent",
                    }
                }
            },
            "next_steps": [
                f"1. Create the project directory: mkdir {snake_name}-agent",
                f"2. Generate all files using the plan above",
                "3. Install dependencies: pip install -e .",
                f"4. Add MCP config to Codex (C:\\Users\\...\\\\.codex\\mcp.json)",
                "5. Restart Codex and say: 'Simulate a {p.template_seeds[0][\"name\"] if p.template_seeds else \"basic case\"}'",
            ],
        }

    def get_prompt_for_codex(self, current_question: dict) -> str:
        """Generate the prompt for Codex to ask the user.
        生成 Codex 向用户提问的提示文本。"""
        q = current_question
        step = q["step"]
        total = q["total_steps"]
        return f"""
## {q["title"]} ({step}/{total})

{q["question"]["ask"]}

**Example answer / 示例回答**:
```
{q["question"]["example"]}
```

Please provide your answer / 请提供你的回答:
""".strip()


# ==========================================================================
# Agent Config Generator / Agent 配置生成器
# ==========================================================================

def generate_agent_config(profile: SoftwareProfile) -> str:
    """Generate the agent_config.py file for a software profile.
    根据软件画像生成 agent_config.py 文件。"""

    domain_entries = []
    for d in profile.domains:
        domain_entries.append(f'    "{d["name"]}": {d},')

    error_entries = []
    for e in profile.error_patterns:
        error_entries.append(f'    {e},')

    kw_entries = []
    for name, kws in profile.domain_keywords.items():
        kw_entries.append(f'    "{name}": {kws},')

    return f"""# -*- coding: utf-8 -*-
\"\"\"Agent configuration for {profile.name}.
{profile.name} Agent 专属配置 — 由 MCP Wizard 自动生成。
\"\"\"

# ---- Physics Domains / 物理领域 ----
DOMAINS: dict = {{
{chr(10).join(domain_entries)}
}}

# ---- Error Patterns (for solver diagnostics) / 错误模式（求解诊断用） ----
ERROR_PATTERNS: list = [
{chr(10).join(error_entries)}
]

# ---- Paper Keywords (for auto domain detection) / 论文关键词（自动领域识别） ----
DOMAIN_KEYWORDS: dict = {{
{chr(10).join(kw_entries)}
}}

# ---- Study Type Keywords / 求解类型关键词 ----
STUDY_KEYWORDS: dict = {{
    "stationary": ["stationary", "steady state", "static", "稳态"],
    "transient": ["transient", "time dependent", "time domain", "瞬态"],
    "eigenfrequency": ["eigenfrequency", "modal", "natural frequency", "本征频率"],
    "frequency_domain": ["frequency domain", "harmonic", "频域"],
}}

# ---- Software Connection / 软件连接信息 ----
SOFTWARE_NAME: str = "{profile.name}"
PYTHON_SDK: str = "{profile.python_sdk}"
SDK_INSTALL: str = "{profile.sdk_install}"
CONNECTION_MODE: str = "{profile.connection_mode}"
"""


# ==========================================================================
# Quick Start / 快速开始
# ==========================================================================

def create_profile_quick(
    name: str,
    python_sdk: str,
    sdk_install: str,
    connection_mode: str = "sdk",
) -> SoftwareProfile:
    """Quick profile creation (skip interactive wizard).
    快速创建画像（跳过交互式向导）。"""
    return SoftwareProfile(
        name=name,
        mcp_server_name=f"{name.lower().replace(' ', '-')}-mcp",
        python_sdk=python_sdk,
        sdk_install=sdk_install,
        connection_mode=connection_mode,
    )


# Usage example / 使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("MCP Wizard — Simulation Agent Generator")
    print("=" * 60)
    print()
    print("To use with Codex / 在 Codex 中使用:")
    print("  1. Load the sim-agent-platform SKILL.md")
    print('  2. Say: "Create an agent for [software name]"')
    print("  3. The wizard will guide you step by step")
    print()
    print("Quick start in Python / Python 快速开始:")
    print("  from sim_agent.adapters.mcp_wizard import McpWizard")
    print("  wizard = McpWizard()")
    print("  q = wizard.get_next_question()  # Get first question")
    print("  wizard.answer(q['step_id'], q['question']['id'], 'ANSYS')")
    print()
