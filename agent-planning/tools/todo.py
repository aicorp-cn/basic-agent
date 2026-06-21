RETRY_LIMIT = 3


class ToDoList:
    """
        辅助类，用于在内存中维护待办清单
    """

    statuses = ["pending", "in_progress", "done", "cancelled", "failed"]

    def __init__(self):
        self._items = []

    def read(self, include_completed=False):
        """读取待办清单"""
        if include_completed:
            return [item.copy() for item in self._items]
        else:
            return [item.copy() for item in self._items
                    if item["status"] != "done" and item["status"] != "cancelled"]

    def append(self, id, content, status):
        if status not in ToDoList.statuses:
            raise Exception(f"无效的状态 {status}。"
                            "有效的待办状态：pending, in_progress, done, "
                            "cancelled, failed")
        if self.contains(id):
            raise Exception(f"待办项 {id} 已存在！")
        new_item = {"id": id, "content": content,
                    "status": status, "retries": 0}
        self._items.append(new_item)
        return new_item.copy()

    def contains(self, id) -> bool:
        """检查待办清单中是否包含指定 ID 的项"""
        for item in self._items:
            if item["id"] == id:
                return True
        return False

    def update(self, id, content, status):
        if status is not None and status not in ToDoList.statuses:
            raise Exception(f"无效的状态 {status}。"
                            "有效的待办状态：pending, in_progress, done, "
                            "cancelled, failed")
        idx = 0
        while idx < len(self._items):
            if self._items[idx]["id"] == id:
                if content is not None:
                    self._items[idx]["content"] = content
                if status is not None:
                    prev_status = self._items[idx]["status"]
                    self._items[idx]["status"] = status
                    # 将失败任务重新设为 in_progress 算作一次重试
                    if prev_status == "failed" and status == "in_progress":
                        self._items[idx]["retries"] += 1
                return self._items[idx].copy()
            idx += 1
        raise Exception(f"未找到 ID 为 {id} 的待办项")


todo_store = ToDoList()


def todo_append(id, content, status) -> str:
    """向待办清单中添加一个新项"""
    id_str = str(id)
    content_str = str(content)
    status_str = str(status)
    try:
        todo_store.append(id_str, content_str, status_str)
        return f"成功将待办项 {id_str} 添加到待办清单！"
    except Exception as e:
        return f"添加待办项失败：{e}"


def todo_list(include_completed=False) -> str:
    """列出待办清单中的所有项"""
    items = todo_store.read(include_completed)

    result = f"待办清单（{len(items)} 项）\n"
    for status in ToDoList.statuses:
        count = sum(1 for i in items if i["status"] == status)
        result += f"{count} 个 {status} 项\n"

    result += "-----\n"
    for item in items:
        retry_note = f"，{item['retries']} 次重试" if item["retries"] > 0 else ""
        result += f"- [{item['id']}] {item['content']} ({item['status']}{retry_note})\n"

    return result


def todo_update(id, content=None, status=None) -> str:
    if content is None and status is None:
        return "未提供要更新的内容或状态，无需操作。"
    try:
        item = todo_store.update(id, content, status)
        retries = item["retries"]
        if item["status"] == "in_progress" and retries > 0:
            if retries >= RETRY_LIMIT:
                return (
                    f"已更新待办项 {id} 为 in_progress — "
                    f"但这是第 {retries} 次重试（共 {RETRY_LIMIT} 次，已达上限）。"
                    f"不要再重试，请升级给用户处理。"
                )
            return (
                f"成功更新待办项 {id}！"
                f"第 {retries} 次重试（共 {RETRY_LIMIT} 次）。"
            )
        return f"成功更新待办项 {id}！"
    except Exception as e:
        return f"更新待办项 {id} 失败：{e}"