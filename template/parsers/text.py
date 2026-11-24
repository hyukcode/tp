"""Plain text paragraphs and structured configuration imports."""
from __future__ import annotations

import json
from ..models import SuggestedTask


def paragraphs(content: str):
    lines = []
    for line in content.splitlines():
        if line.strip():
            lines.append(line)
        elif lines:
            yield '\n'.join(lines).strip()
            lines = []
    if lines:
        yield '\n'.join(lines).strip()


def parse_text(content: str) -> list[SuggestedTask]:
    tasks = []
    for paragraph in paragraphs(content):
        if len(paragraph) <= 10:
            continue
        title = paragraph.split('。', 1)[0].split('.', 1)[0].strip()[:80]
        tasks.append(SuggestedTask(title, paragraph[:1500]))
        if len(tasks) == 20:
            break
    return tasks


def parse_configuration(content: str, file_type: str) -> list[SuggestedTask]:
    try:
        if file_type == 'json':
            data = json.loads(content)
        elif file_type == 'toml':
            try:
                import tomllib
            except ImportError:
                return parse_text(content)
            data = tomllib.loads(content)
        else:
            return parse_text(content)
    except ValueError:
        return parse_text(content)
    if not isinstance(data, dict):
        return parse_text(content)
    return [SuggestedTask(f'处理配置项 `{key}`', f'根据 {key} 的配置内容进行相应处理。')
            for key in list(data)[:30]]
