"""Versioned template authoring. Published revisions are immutable SQLite rows."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from .converter import to_task_template

VARIABLE = re.compile(r"\{\{\s*([a-zA-Z_]\w*)\s*\}\}")


def validate(document: dict) -> list[str]:
    errors = []
    for key in ('template_name', 'system_prompt_extension'):
        if not isinstance(document.get(key, ''), str):
            errors.append(f'{key} 必须是文本')
    if not str(document.get('template_name', '')).strip():
        errors.append('请填写模板名称')
    tasks = document.get('suggested_tasks', [])
    if not isinstance(tasks, list) or not tasks:
        errors.append('至少需要一个任务')
        tasks = []
    for i, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            errors.append(f'任务 {i} 格式错误')
            continue
        for field in ('title', 'description', 'acceptance', 'tool'):
            value = task.get(field, '')
            if not isinstance(value, str) or (field != 'tool' and not value.strip()):
                errors.append(f'任务 {i} 的 {field} 不能为空且必须是文本')
    parameters = document.get('parameters', [])
    names = set()
    if not isinstance(parameters, list):
        errors.append('参数必须是列表')
        parameters = []
    for param in parameters:
        if not isinstance(param, dict):
            errors.append('参数格式错误')
            continue
        name = param.get('name', '')
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z_]\w*', name) or name in names:
            errors.append('参数名必须是唯一标识符')
        else:
            names.add(name)
        if not isinstance(param.get('default', ''), str) or not isinstance(param.get('required', True), bool):
            errors.append('参数默认值必须是文本，required 必须是布尔值')
    fields = [document.get('template_name', ''), document.get('system_prompt_extension', '')]
    fields += [t.get(k, '') for t in tasks if isinstance(t, dict) for k in ('title', 'description', 'acceptance', 'tool')]
    used = set(VARIABLE.findall('\n'.join(str(x) for x in fields)))
    errors.extend(f'未定义参数: {name}' for name in sorted(used - names))
    return errors


def instantiate(document: dict, values: dict) -> dict:
    errors = validate(document)
    if errors:
        raise ValueError('\n'.join(errors))
    bindings = {}
    for param in document.get('parameters', []):
        value = values.get(param['name'], param.get('default', ''))
        if not isinstance(value, str):
            raise ValueError(f"参数 {param['name']} 必须是文本")
        if param.get('required', True) and not value.strip():
            raise ValueError(f"请填写参数: {param['name']}")
        bindings[param['name']] = value
    def render(value):
        return VARIABLE.sub(lambda match: bindings[match.group(1)], value)
    tasks = [{key: render(task.get(key, '')) for key in ('title', 'description', 'acceptance', 'tool')} for task in document['suggested_tasks']]
    return to_task_template(tasks, render(document['template_name']), document.get('source_file', ''), extra_context=render(document.get('system_prompt_extension', ''))).to_dict()


class Workbench:
    """One draft and immutable numbered releases per stable template ID."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS releases (id TEXT, version INTEGER, body TEXT NOT NULL, PRIMARY KEY(id, version));
            ''')

    def connect(self):
        return sqlite3.connect(self.path)

    def list(self):
        with self.connect() as db:
            return [dict(id=id, revision=revision, document=json.loads(body), versions=[v[0] for v in db.execute('SELECT version FROM releases WHERE id=? ORDER BY version DESC', (id,))]) for id, revision, body in db.execute('SELECT id, revision, body FROM drafts ORDER BY rowid DESC')]

    def save(self, document: dict, id: str = '', revision: int = 0):
        if not isinstance(document, dict):
            raise ValueError('模板必须是对象')
        id = id or uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision FROM drafts WHERE id=?', (id,)).fetchone()
            if (row[0] if row else 0) != revision:
                raise ValueError('草稿已被修改，请重新加载')
            revision += 1
            db.execute('INSERT OR REPLACE INTO drafts VALUES (?, ?, ?)', (id, revision, json.dumps(document, ensure_ascii=False)))
        return dict(id=id, revision=revision)

    def publish(self, id: str, revision: int):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision, body FROM drafts WHERE id=?', (id,)).fetchone()
            if not row or row[0] != revision:
                raise ValueError('草稿不存在或已变更，请重新加载')
            errors = validate(json.loads(row[1]))
            if errors:
                raise ValueError('\n'.join(errors))
            version = db.execute('SELECT COALESCE(MAX(version), 0)+1 FROM releases WHERE id=?', (id,)).fetchone()[0]
            db.execute('INSERT INTO releases VALUES (?, ?, ?)', (id, version, row[1]))
        return dict(id=id, version=version)

    def release(self, id: str, version: int, values: dict):
        with self.connect() as db:
            row = db.execute('SELECT body FROM releases WHERE id=? AND version=?', (id, version)).fetchone()
        if not row:
            raise ValueError('发布版本不存在')
        return instantiate(json.loads(row[0]), values)
