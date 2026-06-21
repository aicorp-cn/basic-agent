import subprocess


def run_bash(command: str) -> str:
    """执行 bash 命令并返回其输出。"""
    result = subprocess.run(
        command, shell=True, text=True, capture_output=True
    )
    output = result.stdout
    if result.stderr:
        output += f"\nSTDERR:\n{result.stderr}"
    return output or "(无输出)"