"""
Agent With Tools - 带工具调用能力的 AI Agent。

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
#OPENAI_API_KEY = "sk-xxxxxx"

# API 基础地址（本地 Ollama 默认 http://localhost:11434/v1）
#OPENAI_BASE_URL = "https://api.deepseek.com"

# 模型名称（本地默认 llama3.1:8b，云端默认 deepseek-v4-flash）
# LLM_MODEL = "deepseek-v4-flash"

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

        # 查找并执行工具
        if name not in TOOL_REGISTRY:
            result = f"错误：未知工具 '{name}'。可用工具：{list(TOOL_REGISTRY.keys())}"
        else:
            try:
                result = TOOL_REGISTRY[name](**args)
            except Exception as e:
                result = (
                    f"错误：工具 '{name}' 执行失败：{type(e).__name__}: {e}。"
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
    """运行 Agent 对话循环，自动处理多轮工具调用。"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个乐于助人的助手。你可以读写文件、搜索文件系统和浏览网页。"
                "请使用这些工具来帮助用户。"
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
    print(f"  Agent With Tools")
    print(f"  模式：{mode}")
    print(f"  模型：{LLM_MODEL}")
    print("=" * 40)

    client = get_llm_client()
    agent_loop(client)