import glob as glob_module
import re
from pathlib import Path

_CWD = Path.cwd().resolve()


def _resolve_path(path: str) -> str:
    """解析路径并确保其位于当前工作目录内。"""
    p = Path(path)
    if not p.is_absolute():
        p = _CWD / p
    try:
        p = p.resolve()
        p.relative_to(_CWD)
    except (ValueError, OSError):
        raise PermissionError(
            f"路径 '{path}' 不在工作目录 '{_CWD}' 内。"
            f"文件操作仅限于当前工作目录。"
        )
    return str(p)


def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
    """读取文件中的若干行，支持指定偏移量和行数限制。"""
    resolved = _resolve_path(path)
    p = Path(resolved)
    if not p.exists():
        return f"错误：文件不存在：{path}"
    lines = p.read_text(errors="replace").splitlines()
    selected = lines[offset - 1: offset - 1 + limit]
    return "\n".join(f"{offset + i}: {line}" for i, line in enumerate(selected))


def glob_files(pattern: str, path: str = ".") -> str:
    """在目录中查找匹配 glob 模式的文件。"""
    resolved_dir = _resolve_path(path)
    matches = glob_module.glob(f"{resolved_dir}/**/{pattern}", recursive=True)
    matches += glob_module.glob(f"{resolved_dir}/{pattern}")
    unique = sorted(set(matches))
    return "\n".join(unique) if unique else "(无匹配)"


def grep(pattern: str, path: str = ".", include: str = "*") -> str:
    """搜索文件内容中的正则表达式模式，可选按文件名过滤。"""
    resolved_dir = _resolve_path(path)
    results = []
    for filepath in glob_module.glob(f"{resolved_dir}/**/{include}", recursive=True):
        fp = Path(filepath)
        if not fp.is_file():
            continue
        try:
            for i, line in enumerate(fp.read_text(errors="replace").splitlines(), 1):
                if re.search(pattern, line):
                    results.append(f"{filepath}:{i}: {line}")
        except OSError:
            pass
    return "\n".join(results) if results else "(无匹配)"


def write_file(path: str, content: str) -> str:
    """将内容写入文件，如果文件不存在则创建。"""
    resolved = _resolve_path(path)
    p = Path(resolved)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"已写入 {len(content)} 字节到 {path}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """替换文件中第一个出现的 old_string 为 new_string。"""
    resolved = _resolve_path(path)
    p = Path(resolved)
    if not p.exists():
        return f"错误：文件不存在：{path}"
    original = p.read_text()
    if old_string not in original:
        return f"错误：在 {path} 中未找到指定字符串"
    p.write_text(original.replace(old_string, new_string, 1))
    return f"已编辑 {path}"