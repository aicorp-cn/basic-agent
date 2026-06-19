# basic-agent

本仓库是 AICorp 系列文章中关于从零构建简单 AI Agent 框架的配套代码。

## Agent 列表

| Agent | 说明 | 文件 |
|-------|------|------|
| **simple-agent** | 基础对话 Agent，支持多轮对话 | `simple-agent/agent.py` |
| **agent-with-tools** | 带工具调用能力（读写文件、Shell、网页抓取） | `agent-with-tools/agent.py` |
| **agent-planning** | 具备 Scratchpad 和 To-do List 的规划型 Agent | `agent-planning/agent.py` |
| **agent-human-in-the-loop** | 带权限管控的 Agent，用户可控制工具执行 | `agent-human-in-the-loop/agent.py` |

## 环境要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

## 设置

```bash
git clone <repo-url>
cd basic-agent-harness
uv sync
```

## 配置

每个 Agent 的 `agent.py` 文件顶部都有**配置区域**，直接修改即可：

```python
# ========================================
# 配置区域 - 按需修改即可
# ========================================

# 云端模式：设置 API Key 后将自动使用云端模式，否则使用本地 Ollama
# OPENAI_API_KEY = "sk-xxx"

# API 基础地址（本地 Ollama 默认 http://localhost:11434/v1）
# OPENAI_BASE_URL = "http://localhost:11434/v1"

# 模型名称（本地默认 llama3.1:8b，云端默认 gpt-4o）
# LLM_MODEL = "llama3.1:8b"

# 温度参数（0.0 - 2.0，默认 0.7）
# LLM_TEMPERATURE = 0.7
```

取消注释对应配置项即可切换：

```bash
# 本地模式（默认，使用 Ollama）
uv run simple-agent/agent.py

# 云端模式
OPENAI_API_KEY="sk-xxx" uv run simple-agent/agent.py

# 使用其他 OpenAI 兼容服务（如 DeepSeek、Azure 等）
OPENAI_API_KEY="sk-xxx" OPENAI_BASE_URL="https://api.deepseek.com/v1" LLM_MODEL="deepseek-chat" uv run simple-agent/agent.py
```

## 运行

```bash
# simple-agent - 基础对话
uv run simple-agent/agent.py

# agent-with-tools - 带工具调用
uv run agent-with-tools/agent.py

# agent-planning - 带任务规划
uv run agent-planning/agent.py

# agent-human-in-the-loop - 带权限管控
#   --mode default       ：读写工具需确认（默认）
#   --mode acceptEdits   ：工作目录内写入免确认
#   --mode dangerouslySkipPermissions ：全部免确认
uv run agent-human-in-the-loop/agent.py
uv run agent-human-in-the-loop/agent.py --mode acceptEdits
uv run agent-human-in-the-loop/agent.py --mode dangerouslySkipPermissions
```

输入 `\exit` 退出对话。

## 目录结构

```
simple-agent/
  agent.py                          # 基础对话 Agent

agent-with-tools/
  agent.py                          # 带工具调用的 Agent
  tools/
    filesystem.py                   # 读取、写入、搜索文件
    shell.py                        # 运行 Shell 命令
    web.py                          # 获取网页内容
    registry.py                     # 工具注册中心与 Schema

agent-planning/
  agent.py                          # 带规划能力的 Agent
  tools/
    filesystem.py                   # 文件系统工具
    shell.py                        # Shell 工具
    web.py                          # 网页工具
    registry.py                     # 工具注册中心
    scratchpad.py                   # 工作记忆（Scratchpad）
    todo.py                         # 任务追踪（To-do List）

agent-human-in-the-loop/
  agent.py                          # 带权限管控的 Agent
  tools/
    filesystem.py                   # 文件系统工具
    shell.py                        # Shell 工具
    web.py                          # 网页工具
    registry.py                     # 工具注册中心
    scratchpad.py                   # 工作记忆
    todo.py                         # 任务追踪
    interaction.py                  # 用户交互（ask_question）
```

## 许可证

MIT