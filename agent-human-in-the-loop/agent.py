"""
Agent Human-in-the-Loop - 带权限管控的 AI Agent。

在 Agent Planning 的基础上增加了工具调用权限控制：
- default：读取和规划工具免审批，其他工具需要用户确认
- acceptEdits：读取、规划和文件写入工具在工作目录内免审批
- dangerouslySkipPermissions：所有工具免审批

支持两种运行模式：
1. 本地模式：通过 Ollama 调用本地模型（默认）
2. 云端模式：配置 API Key 调用云端模型

使用方式：直接修改下方 CONFIG 区域的配置项即可。
"""
import argparse
import json
from enum import Enum
from pathlib import Path
import httpx
from openai import OpenAI
from tools import get_tool_registry, get_tool_schemas

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

# 权限模式（默认 default）
# 可选值：default, acceptEdits, dangerouslySkipPermissions
# PERMISSION_MODE = "default"

# ========================================
# 以下代码无需修改
# ========================================

TOOL_REGISTRY = get_tool_registry()
TOOL_SCHEMAS = get_tool_schemas()


# ---------------------------------------------------------------------------
# 权限管控
# ---------------------------------------------------------------------------

class PermissionMode(Enum):
    """权限模式枚举。"""
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    DANGEROUSLY_SKIP_PERMISSIONS = "dangerouslySkipPermissions"


# 始终免审批的工具：只读文件系统操作
READ_TOOLS = {"read_file", "glob_files", "grep"}

# 始终免审批的工具：内部规划/记录和用户交互（无外部副作用）
PLANNING_TOOLS = {"todo_append", "todo_list", "todo_update", "read_scratchpad", "write_scratchpad", "ask_question"}

# 在 acceptEdits 模式下，当目标在工作目录内时免审批的文件写入工具
WRITE_TOOLS = {"write_file", "edit_file"}


def _resolve_tool_path(tool_name: str, args: dict) -> str | None:
    """获取写入工具的目标文件路径，不适用时返回 None。"""
    if tool_name in WRITE_TOOLS:
        return args.get("path")
    return None


def _is_within_working_dir(path: str, working_dir: Path) -> bool:
    """判断路径是否在指定工作目录内。"""
    try:
        target = Path(path)
        if not target.is_absolute():
            target = working_dir / target
        target.resolve().relative_to(working_dir.resolve())
        return True
    except ValueError:
        return False


def _ask_permission(tool_name: str, args: dict) -> bool:
    """向用户交互式地请求工具调用许可。返回 True 表示允许。"""
    print(f"\n  [需要权限] {tool_name}")
    print(f"  参数：{json.dumps(args, ensure_ascii=False)}")
    while True:
        try:
            answer = input("  是否允许此操作？[y/n]: ").strip().lower()
        except EOFError:
            print("  (输入中断 — 拒绝权限)")
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  请输入 'y' 或 'n'。")


def check_permission(tool_name: str, args: dict, mode: PermissionMode, working_dir: Path) -> bool:
    """
    判断工具调用是否在当前权限模式下被允许。

    权限规则：
    - default：读取和规划工具免审批，其他需用户确认
    - acceptEdits：读取、规划和文件写入（工作目录内）免审批
    - dangerouslySkipPermissions：全部免审批

    Returns:
        True 表示允许执行，False 表示被拒绝
    """
    # 规划工具和读取工具始终免审批
    if tool_name in READ_TOOLS or tool_name in PLANNING_TOOLS:
        return True

    if mode == PermissionMode.DANGEROUSLY_SKIP_PERMISSIONS:
        return True

    if mode == PermissionMode.ACCEPT_EDITS and tool_name in WRITE_TOOLS:
        path = _resolve_tool_path(tool_name, args)
        if path and _is_within_working_dir(path, working_dir):
            return True  # 在工作目录内，自动批准
        # 路径在工作目录外 → 需要用户确认

    return _ask_permission(tool_name, args)


# ---------------------------------------------------------------------------
# Agent 核心逻辑
# ---------------------------------------------------------------------------


def get_llm_client():
    """创建并返回 LLM 客户端。"""
    if OPENAI_API_KEY:
        print(f"[配置] 云端模式 - API: {OPENAI_BASE_URL}")
        return OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
    else:
        print(f"[配置] 本地模式 - Ollama: {OPENAI_BASE_URL}")
        http_client = httpx.Client(
            timeout=60,
            mounts={
                "http://localhost": httpx.HTTPTransport(proxy=None),
                "http://127.0.0.1": httpx.HTTPTransport(proxy=None),
            },
        )
        return OpenAI(
            base_url=OPENAI_BASE_URL,
            api_key="ollama",
            http_client=http_client,
        )


def handle_tool_calls(tool_calls, messages, mode: PermissionMode, working_dir: Path):
    """
    执行 LLM 请求的工具调用（含权限检查），并将结果追加到对话历史。

    Args:
        tool_calls: LLM 返回的工具调用列表
        messages: 对话消息列表（会被修改）
        mode: 当前权限模式
        working_dir: 工作目录路径
    """
    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        print(f"  [工具] {name}({args})")

        if name not in TOOL_REGISTRY:
            result = (
                f"错误：未知工具 '{name}'。"
                f"可用工具：{list(TOOL_REGISTRY.keys())}"
            )
        elif not check_permission(name, args, mode, working_dir):
            result = (
                f"权限被拒：用户不允许执行 '{name}'。"
                "不要重试此工具调用，除非先询问用户。"
            )
        else:
            try:
                result = TOOL_REGISTRY[name](**args)
            except TypeError as e:
                result = (
                    f"错误：工具 '{name}' 的参数无效：{e}。"
                    "请检查工具 Schema 并使用正确的参数重试。"
                )

        print(f"  [工具结果] {result[:200]}{'...' if len(result) > 200 else ''}")

        # 将工具执行结果关联到对应的工具调用 ID 后追加到对话
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })


def agent_loop(client, mode: PermissionMode, working_dir: Path):
    """运行 Agent 对话循环，含权限管控和任务规划。"""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a capable coding and research assistant.\n\n"
                "## Available tools\n\n"
                "Action tools: read_file, write_file, edit_file, glob_files, grep, run_bash, webfetch\n\n"
                "Planning tools:\n"
                "- Scratchpad (read_scratchpad / write_scratchpad): your private working memory.\n"
                "- To-do list (todo_append / todo_list / todo_update): a persistent task tracker.\n"
                "- Clarification (ask_question): ask the user a single focused question when you "
                "are genuinely blocked and cannot reasonably infer the missing information from "
                "context. Do not use it for progress updates or to confirm actions you can already "
                "take — only ask when it is strictly necessary to proceed.\n\n"
                "## Working directory\n\n"
                "The current working directory is always the user's project root. "
                "Never ask the user to supply a path.\n\n"
                "## How to plan\n\n"
                "For complex or multi-step tasks:\n"
                "1. Write your initial thinking to the scratchpad before acting.\n"
                "2. Break the work into steps and add each to the to-do list.\n"
                "3. Before starting a step, mark it in_progress.\n"
                "4. Mark items done immediately after completing them.\n"
                "5. Call todo_list to review remaining work before the next step.\n\n"
                "For simple tasks: act directly without creating todos.\n\n"
                "Planning tool calls are internal bookkeeping. After any planning tool "
                "call, always continue working immediately. Never emit an empty message.\n\n"
                "## Replanning\n\n"
                "After every tool result, check if the outcome matched your expectation. "
                "If a tool returns an error or unexpected output, replan before continuing.\n\n"
                "## Done detection\n\n"
                "Before declaring the task complete, verify:\n"
                "1. No pending, in_progress, or failed items in the to-do list.\n"
                "2. The output matches the original goal (e.g., tests pass).\n"
                "3. No unresolved questions remain in the scratchpad."
            ),
        }
    ]

    print(f"\n💬 对话已开始（输入 \\exit 退出）\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "\\exit":
            print("👋 再见！")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        # 持续循环直到 LLM 停止调用工具并给出最终回复
        while True:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE,
            )

            message = response.choices[0].message

            # 将 Assistant 的回复追加到对话历史
            messages.append(message)

            if message.tool_calls:
                # LLM 请求调用工具 — 执行后再让 LLM 继续
                handle_tool_calls(message.tool_calls, messages, mode, working_dir)
            elif not message.content or not message.content.strip():
                # LLM 输出了空消息（通常在仅调用规划工具后发生）
                messages.append({
                    "role": "user",
                    "content": "Continue.",
                })
            else:
                # 没有工具调用：LLM 给出了最终回复
                print(f"Assistant: {message.content}")
                break


if __name__ == "__main__":
    # 读取配置
    OPENAI_API_KEY = globals().get("OPENAI_API_KEY") or ""
    OPENAI_BASE_URL = globals().get("OPENAI_BASE_URL") or "http://localhost:11434/v1"
    LLM_TEMPERATURE = globals().get("LLM_TEMPERATURE") or 0.7
    LLM_MODEL = globals().get("LLM_MODEL") or ("llama3.1:8b" if not OPENAI_API_KEY else "gpt-4o")
    PERMISSION_MODE_RAW = globals().get("PERMISSION_MODE") or "default"

    # 注入到全局供各函数使用
    globals()["OPENAI_API_KEY"] = OPENAI_API_KEY
    globals()["OPENAI_BASE_URL"] = OPENAI_BASE_URL
    globals()["LLM_MODEL"] = LLM_MODEL
    globals()["LLM_TEMPERATURE"] = LLM_TEMPERATURE

    # 解析命令行参数（优先级高于文件配置）
    parser = argparse.ArgumentParser(description="带权限管控的 AI Agent")
    parser.add_argument(
        "--mode",
        choices=["default", "acceptEdits", "dangerouslySkipPermissions"],
        default=None,
        help="权限模式：default（默认）/ acceptEdits / dangerouslySkipPermissions",
    )
    cli_args = parser.parse_args()

    # 命令行参数优先
    final_mode = cli_args.mode if cli_args.mode else PERMISSION_MODE_RAW
    mode = PermissionMode(final_mode)

    # 工作目录
    working_dir = Path.cwd()

    print("=" * 40)
    print(f"  Agent HITL (Human-in-the-Loop)")
    print(f"  模式：{mode.value}")
    print(f"  模型：{LLM_MODEL}")
    print(f"  工作目录：{working_dir}")
    print("=" * 40)

    client = get_llm_client()
    agent_loop(client, mode, working_dir)