class Scratchpad:
    """读写内存中的草稿本"""

    def __init__(self):
        self._content = ""

    def read(self) -> str:
        if self._content == "":
            return "(空)"
        return self._content

    def write(self, content: str) -> str:
        self._content = str(content).strip()
        return self._content


scratchpad = Scratchpad()


def read_scratchpad():
    """读取草稿本的内容"""
    return scratchpad.read()


def write_scratchpad(content: str):
    """
    写入草稿本。之前的内容将被覆盖。
    """
    scratchpad.write(content)
    return "成功将内容写入草稿本"