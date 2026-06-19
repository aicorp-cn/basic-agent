"""
Agent Planning - 带规划能力的 AI Agent。

具备 Scratchpad（工作记忆）和 To-do List（任务追踪）能力，
可自主规划、执行和调整复杂任务。

支持两种运行模式：
1. 本地模式：通过 Ollama 调用本地模型（默认）
2. 云端模式：配置 API Key 调用云端模型

使用方式：直接修改下方 CONFIG 区域的配置项即可。
"""
import json
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

# ========================================
# 以下代码无需修改
# ========================================

TOOL_REGISTRY = get_tool_registry()
TOOL_SCHEMAS = get_tool_schemas()


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


def handle_tool_calls(tool_calls, messages):
    """
    执行 LLM 请求的工具调用，并将结果追加到对话历史。

    Args:
        tool_calls: LLM 返回的工具调用列表
        messages: 对话消息列表（会被修改，追加工具执行结果）
    """
    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        print(f"  [工具] {name}({args})")

        if name not in TOOL_REGISTRY:
            result = f"错误：未知工具 '{name}'。可用工具：{list(TOOL_REGISTRY.keys())}"
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


def agent_loop(client):
    """运行 Agent 对话循环，支持任务规划与自动执行。"""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a capable coding and research assistant.\n\n"

                "## Available tools\n\n"
                "Action tools: read_file, write_file, edit_file, glob_files, grep, run_bash, webfetch\n\n"
                "Planning tools:\n"
                "- Scratchpad (read_scratchpad / write_scratchpad): your private working memory. "
                "Use it to think through an approach, store intermediate findings, or draft content "
                "before committing. Each write fully replaces the previous content.\n"
                "- To-do list (todo_append / todo_list / todo_update): a persistent task tracker. "
                "Items carry a status: pending, in_progress, done, cancelled, or failed.\n\n"

                "## Working directory\n\n"
                "The current working directory is always the user's project root. "
                "When asked to work on a project or codebase without a specified path, "
                "start by exploring '.' with glob_files or run_bash. "
                "Never ask the user to supply a path.\n\n"

                "## How to plan\n\n"
                "For complex or multi-step tasks (roughly 3 or more distinct steps, or when the "
                "path forward is unclear):\n"
                "1. Write your initial thinking and approach to the scratchpad before acting.\n"
                "2. Break the work into concrete steps and add each one to the to-do list with "
                "todo_append (status: pending).\n"
                "3. Before starting a step, mark it in_progress with todo_update. "
                "Keep only one item in_progress at a time.\n"
                "4. Mark items done immediately after completing them — do not batch completions.\n"
                "5. Call todo_list to review remaining work before moving to the next step.\n"
                "6. Mark tasks cancelled if they become unnecessary.\n\n"
                "For simple, single-step tasks: act directly without creating todos.\n\n"
                "Planning tool calls (write_scratchpad, todo_append, todo_update, todo_list) "
                "are internal bookkeeping, not responses to the user. After any planning tool "
                "call, always continue working immediately — make your next tool call or, once "
                "the task is fully complete, give a substantive final answer. "
                "Never emit an empty or whitespace-only message.\n\n"
                "## Replanning\n\n"
                "After every tool result, check whether the outcome matched your expectation. "
                "If a tool returns an error, unexpected output, or reveals information that "
                "changes your understanding of the task, do not move to the next planned step — "
                "replan first.\n\n"
                "When a step fails:\n"
                "1. Diagnose in the scratchpad — is this a recoverable input error (wrong path, "
                "typo, wrong argument) or a deeper problem (wrong approach, wrong assumption)?\n"
                "2. Mark the task failed: todo_update(id, status='failed').\n"
                "3. Choose a recovery action:\n"
                "   - Retry: the failure is correctable. Fix the input and set the task back to "
                "in_progress. The tool will report which retry attempt this is.\n"
                "   - Replace: the approach is wrong. Cancel the task and add a revised one.\n"
                "   - Reorder: new information makes a different task more urgent. Update the "
                "pending items before continuing.\n"
                "4. If todo_update reports that the retry limit has been reached, stop retrying. "
                "Write a clear diagnosis in the scratchpad — what you tried, what failed each "
                "time, and what you need — then give the user a concise escalation message "
                "and wait for their input.\n\n"
                "When a tool succeeds but returns information that changes the picture, pause "
                "before acting. Call todo_list, reassess all pending items in the scratchpad, "
                "and cancel or replace any tasks that no longer make sense.\n\n"
                "## How to use the scratchpad\n\n"
                "Before each tool call during a complex task, update the scratchpad with your "
                "current thinking. Structure each entry around these five steps:\n\n"
                "1. Restate the goal — write what you understand the task to be, in your own words. "
                "This catches misreads before they compound into wasted work.\n"
                "2. Survey what you know — note which files you have seen, what the code structure "
                "looks like, and what constraints or requirements apply.\n"
                "3. Evaluate options — reason through at least two approaches and explain why you "
                "are choosing one over the other.\n"
                "4. Anticipate failure modes — write down what could go wrong with the chosen "
                "approach and how you would diagnose it.\n"
                "5. Decide the next single action — commit to exactly one tool call. "
                "Do not plan several calls at once; decide the next step only.\n\n"
                "Re-read the scratchpad whenever you resume after a tool result to keep your "
                "reasoning grounded in what you have already learned.\n\n"
                "## Done detection\n\n"
                "Do not give a final answer based on the task list being empty alone. "
                "Before declaring the task complete, verify all three of the following:\n\n"
                "1. Structural completion — call todo_list and confirm there are no pending, "
                "in_progress, or failed items.\n"
                "2. Verification — check the output against the original goal. For code tasks: "
                "run the tests or build with run_bash and confirm they pass. For research tasks: "
                "re-read the scratchpad and confirm the assembled answer addresses what was "
                "actually asked.\n"
                "3. Uncertainty check — read the scratchpad and ask: are there unresolved "
                "questions, assumptions that were never validated, or tasks that were cancelled "
                "rather than properly completed?\n\n"
                "If all three are satisfied, give your final answer. If any are not, re-enter "
                "the planning loop — add the outstanding items to the todo list and continue."
            ),
        }
    ]

    print("\n💬 对话已开始（输入 \\exit 退出）\n")

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
                handle_tool_calls(message.tool_calls, messages)
            elif not message.content or not message.content.strip():
                # LLM 输出了空消息（通常在仅调用规划工具后发生）
                # 给一个 "继续" 提示，避免卡住
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

    # 注入到全局供各函数使用
    globals()["OPENAI_API_KEY"] = OPENAI_API_KEY
    globals()["OPENAI_BASE_URL"] = OPENAI_BASE_URL
    globals()["LLM_MODEL"] = LLM_MODEL
    globals()["LLM_TEMPERATURE"] = LLM_TEMPERATURE

    mode = "云端" if OPENAI_API_KEY else "本地（Ollama）"
    print("=" * 40)
    print(f"  Agent Planning")
    print(f"  模式：{mode}")
    print(f"  模型：{LLM_MODEL}")
    print("=" * 40)

    client = get_llm_client()
    agent_loop(client)