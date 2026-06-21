from tools.filesystem import read_file, glob_files, grep, write_file, edit_file
from tools.shell import run_bash
from tools.web import webfetch
from tools.todo import todo_append, todo_list, todo_update
from tools.scratchpad import read_scratchpad, write_scratchpad


def get_tool_registry():
    return {
        "run_bash":          run_bash,
        "read_file":         read_file,
        "glob_files":        glob_files,
        "grep":              grep,
        "write_file":        write_file,
        "edit_file":         edit_file,
        "webfetch":          webfetch,
        "todo_append":       todo_append,
        "todo_list":         todo_list,
        "todo_update":       todo_update,
        "read_scratchpad":   read_scratchpad,
        "write_scratchpad":  write_scratchpad,
    }


def get_tool_schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": "run_bash",
                "description": "在用户机器上执行一条 bash 命令并返回输出。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "要执行的 bash 命令。",
                        }
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取文件中的若干行，返回带行号前缀的内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件的绝对路径或相对路径。"},
                        "offset": {"type": "integer", "description": "起始行号（从 1 开始），默认为 1。"},
                        "limit": {"type": "integer", "description": "最大返回行数，默认为 200。"},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "glob_files",
                "description": "在目录中查找匹配 glob 模式的文件（例如 '**/*.py'）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "用于匹配文件名的 glob 模式。"},
                        "path": {"type": "string", "description": "搜索的根目录，默认为 '.'。"},
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep",
                "description": "搜索文件内容中的正则表达式模式，返回匹配行及其文件路径和行号。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "要搜索的正则表达式。"},
                        "path": {"type": "string", "description": "搜索的目录，默认为 '.'。"},
                        "include": {"type": "string", "description": "按文件名 glob 过滤搜索文件（例如 '*.py'），默认为 '*'。"},
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "将内容写入文件，如果文件（或缺失的父目录）不存在则自动创建。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "要写入的文件路径。"},
                        "content": {"type": "string", "description": "要写入文件的完整内容。"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "替换文件中第一个出现的 old_string 为 new_string。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "要编辑的文件路径。"},
                        "old_string": {"type": "string", "description": "要查找和替换的精确字符串。"},
                        "new_string": {"type": "string", "description": "用于替换的新字符串。"},
                    },
                    "required": ["path", "old_string", "new_string"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "webfetch",
                "description": (
                    "获取一个公开 URL（仅 http/https）并返回其完整的纯文本内容（最大 2 MB）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "要获取的 URL（http/https）。"},
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "todo_append",
                "description": (
                    "向待办清单中添加一个新项。"
                    "用于追踪你计划执行的任务。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "任务的唯一标识（例如 '1', 'task-setup'）。",
                        },
                        "content": {
                            "type": "string",
                            "description": "任务的描述。",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done", "cancelled", "failed"],
                            "description": "任务的初始状态。新任务请使用 'pending'。",
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "todo_list",
                "description": (
                    "读取当前的待办清单。"
                    "默认显示所有活跃项（pending, in_progress, failed）。"
                    "设置 include_completed=true 可同时查看 done 和 cancelled 项。"
                    "失败项会显示其重试次数。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_completed": {
                            "type": "boolean",
                            "description": "如果为 true，则包含 done 和 cancelled 项。默认为 false。",
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "todo_update",
                "description": (
                    "更新现有待办项的内容或状态。"
                    "至少需要提供 'content' 或 'status' 中的一个。"
                    "将失败项重新设为 in_progress 计为一次重试，"
                    "系统会自动追踪。达到重试上限时会发出警告。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "要更新的待办项 ID。",
                        },
                        "content": {
                            "type": "string",
                            "description": "项的新描述。省略则不修改。",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done", "cancelled", "failed"],
                            "description": "项的新状态。省略则不修改。",
                        },
                    },
                    "required": ["id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_scratchpad",
                "description": (
                    "读取内存中草稿本的当前内容。"
                    "如果尚未写入任何内容，返回 '(空)'。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_scratchpad",
                "description": (
                    "用新内容覆盖整个内存中的草稿本。"
                    "之前的内容将被永久替换。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "要存入草稿本的新内容。",
                        },
                    },
                    "required": ["content"],
                },
            },
        },
    ]