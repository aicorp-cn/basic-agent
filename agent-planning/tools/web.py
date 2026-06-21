import re
import urllib.request
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def webfetch(url: str) -> str:
    """获取 URL 的完整纯文本内容（最大 2 MB）。"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"获取 {url} 失败：不支持的协议 '{parsed.scheme}'。仅支持 http 和 https。"
        max_bytes = 2 * 1024 * 1024
        req = urllib.request.Request(url, headers={"User-Agent": "agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get_content_type()
            if content_type and content_type not in (
                "text/html",
                "text/plain",
                "application/xhtml+xml",
            ):
                return f"获取 {url} 失败：不支持的内容类型 '{content_type}'。"
            charset = resp.headers.get_content_charset() or "utf-8"
            raw_chunks = []
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raw_chunks.append(chunk[: max_bytes - (total - len(chunk))])
                    break
                raw_chunks.append(chunk)
        raw = b"".join(raw_chunks).decode(charset, errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception as e:
        return f"获取 {url} 失败：{e}"