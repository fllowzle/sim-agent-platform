# Simulation Agent Platform Skill

## Role / 角色
You are a **Simulation Agent Generator**. You help users create autonomous simulation agents for ANY simulation software (COMSOL, ANSYS, Lumerical, ABAQUS, Gmsh, etc.).

## When to use this skill / 何时使用
Trigger when user says:
- "Create an agent for [software]" / "为 [软件] 创建一个 Agent"
- "I want to automate [software] simulations" / "我想自动化 [软件] 仿真"
- "Build a simulation agent" / "构建仿真 Agent"

## Core Workflow / 核心流程

### Step 1: Load the MCP Wizard
```python
from sim_agent.adapters.mcp_wizard import McpWizard
wizard = McpWizard()
```

### Step 2: Guide the user through 6 setup steps
Ask ONE question at a time. Do NOT ask all at once.

**Step 1 — Software Identity / 软件身份:**
- "What is the simulation software called? / 仿真软件叫什么名字？"
- "Does it have a Python SDK? Package name? / 有 Python SDK 吗？包名？"
- "How to install the SDK? / 如何安装？"
- "Connection mode: (1) Python SDK (2) CLI subprocess (3) Input file driven (4) COM/Java API"

**Step 2 — Physics Domains / 物理领域:**
- "How many physics domains? List them with their typical study types."
- "例如：structural (stationary, transient), thermal (stationary), electromagnetic (eigenfrequency, frequency_domain)"

**Step 3 — Error Patterns / 错误模式:**
- "What are 5-10 common solver errors? For each: keyword → root cause → fixes"
- "例如：'rigid body motion' → insufficient constraints → add fixed supports"

**Step 4 — Template Seeds / 模板播种:**
- "What are 3-5 typical simulation workflows? Name, domain, brief steps."
- "例如：Cantilever beam analysis → structural → geometry→mesh→fix one end→apply force→solve"

**Step 5 — Paper Keywords / 论文关键词:**
- "For each domain, list keywords found in research papers."
- "例如：structural: [stress, strain, von Mises, FEA, displacement, deformation]"

**Step 6 — MCP Tools / MCP 工具:**
- "What are 5-10 core operations users perform? These become MCP tools."
- "例如：create_geometry(), assign_material(), apply_load(), mesh(), solve(), get_result()"

### Step 3: Generate all files
After all 6 steps complete:
```python
plan = wizard.generate_file_plan()
```

Then create each file listed in `plan["files_to_create"]`.

### Step 4: Register with Codex
Add to `C:\Users\...\.codex\mcp.json`:
```json
plan["codex_mcp_config"]
```

### Step 5: Test
"Now say: 'Simulate a [first template name]' and I'll walk through it."

## Available Modules / 可用模块

After the wizard generates files, the new agent project can import from `sim_agent`:

| Module / 模块 | Purpose / 用途 |
|--------------|---------------|
| `sim_agent.core.template_store` | YAML template management / YAML 模板管理 |
| `sim_agent.core.experience_store` | Correction memory / 纠错记忆 |
| `sim_agent.adapters.base_parser` | PDF paper parser (pluggable keywords) / 论文解析器 |
| `sim_agent.adapters.base_diagnostics` | Solver failure diagnostics / 求解诊断器 |
| `sim_agent.adapters.mcp_wizard` | Guided setup wizard / 引导式配置向导 |

## Platform Architecture / 平台架构

```
sim-agent-platform (THIS / 本项目 — 通用骨架)
  |
  +---> comsol-agent (COMSOL-specific / COMSOL 专属)
  +---> ansys-agent  (ANSYS-specific / ANSYS 专属)
  +---> lumerical-agent (Lumerical-specific / Lumerical 专属)
  +---> your-agent (any software / 任意软件)
```

Each child project only contains:
每个子项目只需包含：
- Software-specific config (agent_config.py)
- YAML templates (templates/)
- MCP server (src/mcp_server/)
- Its own SKILL.md
