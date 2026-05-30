# -*- coding: utf-8 -*-
"""sim-agent-platform — Universal Simulation Agent Platform.
通用仿真 Agent 平台。

This is the software-agnostic skeleton. To create an agent for a specific
simulation software, use the MCP Wizard:
  这是软件无关的骨架。要为特定仿真软件创建 Agent，使用 MCP Wizard：

  from sim_agent.adapters.mcp_wizard import McpWizard
  wizard = McpWizard()
  # ... answer questions step by step ...
  plan = wizard.generate_file_plan()
"""

__version__ = "0.1.0"
