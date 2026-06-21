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
    """运行 Agent 对话循环，支持任务规划与自动执行。"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个有能力的编程和研究助手。\n\n"

                "## 可用工具\n\n"
                "执行工具：read_file, write_file, edit_file, glob_files, grep, run_bash, webfetch\n\n"
                "规划工具：\n"
                "- 草稿本 (read_scratchpad / write_scratchpad)：你的私人工作记忆。"
                "可以用它来思考方案、暂存中间发现或在提交前起草内容。"
                "每次写入会完全替换之前的内容。\n"
                "- 待办清单 (todo_append / todo_list / todo_update)：一个持久的任务追踪器。"
                "每个任务带有状态：pending（待处理）、in_progress（进行中）、done（完成）、cancelled（已取消）或 failed（失败）。\n\n"

                "## 工作目录\n\n"
                "当前工作目录始终是用户的项目根目录。"
                "当要求处理项目或代码库但未指定路径时，"
                "使用 glob_files 或 run_bash 探索 '.' 目录。"
                "永远不要要求用户提供路径。\n\n"

                "## 如何规划\n\n"
                "对于复杂或多步骤任务（大致 3 个或更多独立步骤，或前进方向不明确时）：\n"
                "1. 执行前先将你的初步思路和方法写到草稿本中。\n"
                "2. 将工作拆分为具体步骤，通过 todo_append 添加到待办清单（状态：pending）。\n"
                "3. 开始一个步骤前，使用 todo_update 将其标记为 in_progress。"
                "每次只保持一个任务处于 in_progress 状态。\n"
                "4. 完成后立即标记任务为 done——不要批量完成。\n"
                "5. 在进入下一步前调用 todo_list 查看剩余工作。\n"
                "6. 如果任务变得不必要，将其标记为 cancelled。\n\n"
                "对于简单的单步任务：直接执行，无需创建待办事项。\n\n"
                "规划工具的调用（write_scratchpad, todo_append, todo_update, todo_list）"
                "是内部记账行为，不是对用户的回复。调用任何规划工具后，"
                "必须立即继续工作——进行下一次工具调用，或在任务完全完成后给出实质性的最终答案。"
                "永远不要发送空消息或仅含空白字符的消息。\n\n"
                "## 重新规划\n\n"
                "每次工具结果返回后，检查结果是否符合预期。"
                "如果工具返回了错误、意外输出，或揭示了改变你对任务理解的信息，"
                "不要继续执行下一步计划——先重新规划。\n\n"
                "当一个步骤失败时：\n"
                "1. 在草稿本中诊断——这是可恢复的输入错误（路径错误、"
                "拼写错误、参数错误）还是更深层的问题（方法错误、假设错误）？\n"
                "2. 将任务标记为失败：todo_update(id, status='failed')。\n"
                "3. 选择恢复行动：\n"
                "   - 重试：失败可纠正。修正输入并将任务重新设为 in_progress。工具会报告这是第几次重试。\n"
                "   - 替换：方法错误。取消当前任务并添加一个修订后的任务。\n"
                "   - 重排序：新信息使另一任务变得更紧急。继续前更新待办事项的优先级。\n"
                "4. 如果 todo_update 报告已达到重试上限，停止重试。"
                "在草稿本中写下清晰的诊断——你尝试了什么、每次如何失败、"
                "以及你需要什么——然后给用户一条简洁的升级消息，等待用户输入。\n\n"
                "当工具成功但返回的信息改变了情况时，先暂停再行动。"
                "调用 todo_list，在草稿本中重新评估所有待办事项，"
                "取消或替换不再合理的任务。\n\n"
                "## 如何使用草稿本\n\n"
                "在复杂任务中每次工具调用前，用当前的思考更新草稿本。"
                "每次记录应围绕以下五个步骤组织：\n\n"
                "1. 重述目标——用你自己的话写出你对任务的理解。"
                "这能防止误解在后续工作中累积浪费。\n"
                "2. 审视已知信息——记录你已查看过的文件、代码结构的外观、"
                "以及适用的约束条件或需求。\n"
                "3. 评估选项——至少推理两种方法，并解释为什么选择其中一个。\n"
                "4. 预测失败模式——写下所选方法可能出问题的地方，以及你如何诊断它。\n"
                "5. 确定下一步唯一的行动——承诺执行恰好一个工具调用。"
                "不要一次性规划多个调用；只决定下一步。\n\n"
                "每次工具结果返回后重新阅读草稿本，让你的推理始终"
                "基于已学到的知识。\n\n"
                "## 完成检测\n\n"
                "不要仅仅因为任务列表为空就给出最终答案。"
                "在宣布任务完成前，验证以下所有三项：\n\n"
                "1. 结构完成——调用 todo_list 确认没有 pending、"
                "in_progress 或 failed 的任务。\n"
                "2. 验证——检查输出是否符合最初目标。对于编码任务："
                "运行测试或使用 run_bash 构建并确认通过。对于研究任务："
                "重新阅读草稿本，确认整理出的答案回答了实际提出的问题。\n"
                "3. 不确定性检查——阅读草稿本并自问：是否存在未解决的问题、"
                "从未验证的假设、或者被取消而非正确完成的任务？\n\n"
                "如果以上三项都满足，给出最终答案。如果有任何一项不满足，"
                "重新进入规划循环——将未完成的任务添加到待办清单并继续。"
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
    LLM_MODEL = globals().get("LLM_MODEL") or ("llama3.1:8b" if not OPENAI_API_KEY else "deepseek-v4-flash")

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