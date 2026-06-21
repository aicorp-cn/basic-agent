"""
Simple AI Agent - 简单的对话式 AI Agent。

支持两种运行模式：
1. 本地模式：通过 Ollama 调用本地模型（默认）
2. 云端模式：配置 API Key 调用云端模型

使用方式：直接修改下方 CONFIG 区域的配置项即可。
"""
import httpx
from openai import OpenAI

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


def get_llm_client():
    """创建并返回 LLM 客户端。"""
    api_key = OPENAI_API_KEY
    base_url = OPENAI_BASE_URL

    if api_key:
        print(f"[配置] 云端模式 - API: {base_url}")
        return OpenAI(base_url=base_url, api_key=api_key)
    else:
        print(f"[配置] 本地模式 - Ollama: {base_url}")
        http_client = httpx.Client(
            timeout=60,
            mounts={
                "http://localhost": httpx.HTTPTransport(proxy=None),
                "http://127.0.0.1": httpx.HTTPTransport(proxy=None),
            },
        )
        return OpenAI(
            base_url=base_url,
            api_key="ollama",
            http_client=http_client,
        )


def agent_loop(client):
    """运行 Agent 对话循环。"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

    print("\n💬 对话已开始（输入 \\exit 退出）\n")

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if user_input.lower() == "\\exit":
            print("👋 再见！")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
            )
            reply = response.choices[0].message.content
            print(f"Assistant: {reply}")
            messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"❌ 请求失败：{e}")


if __name__ == "__main__":
    # 读取配置：用户取消注释后，变量的值会被 globals() 读取到
    api_key = globals().get("OPENAI_API_KEY") or ""
    base_url = globals().get("OPENAI_BASE_URL") or "http://localhost:11434/v1"
    temperature = globals().get("LLM_TEMPERATURE") or 0.7
    model = globals().get("LLM_MODEL") or ("llama3.1:8b" if not api_key else "gpt-4o")

    # 注入到全局供 get_llm_client 和 agent_loop 使用
    globals()["OPENAI_API_KEY"] = api_key
    globals()["OPENAI_BASE_URL"] = base_url
    globals()["LLM_MODEL"] = model
    globals()["LLM_TEMPERATURE"] = temperature

    mode = "云端" if api_key else "本地（Ollama）"
    print("=" * 40)
    print(f"  Agent 模式：{mode}")
    print(f"  模型：{model}")
    print("=" * 40)

    client = get_llm_client()
    agent_loop(client)
