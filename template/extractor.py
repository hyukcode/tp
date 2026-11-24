"""Public extraction API. Parsers return typed tasks; callers retain dictionaries."""
from __future__ import annotations
from .parsers import parse


def extract_tasks(content: str, file_type: str) -> list[dict]:
    if not isinstance(content, str) or not isinstance(file_type, str):
        raise ValueError('内容和文件类型必须是文本')
    return [task.to_dict() for task in parse(content, file_type)]
