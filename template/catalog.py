"""Render legacy library records for planner selection."""
from __future__ import annotations


def task_hint(task: dict) -> str:
    title = str(task.get('title') or '').strip()
    tool = str(task.get('tool') or task.get('skill') or '').strip()
    return f'{title} [{tool}]' if tool else title


def catalog_text(records: list[dict]) -> str:
    if not records:
        return '（无已存储的模板。用 `tp <file>` 存入模板。）'
    lines = [f'共 {len(records)} 个模板可用：']
    for record in records:
        meta = record['_meta']
        line = f"  - **{meta.get('name', '?')}**"
        tags = meta.get('tags') or []
        if isinstance(tags, list) and tags:
            line += '  [' + ', '.join(str(tag) for tag in tags) + ']'
        description = str(meta.get('desc') or '')[:80]
        if description:
            line += '  ' + description
        tasks = record.get('suggested_tasks') or []
        if isinstance(tasks, list):
            hints = [task_hint(task) for task in tasks[:6] if isinstance(task, dict)]
            hints = [hint for hint in hints if hint]
            if hints:
                line += '\n      任务: ' + '；'.join(hints)
        lines.append(line)
    return '\n'.join(lines)
