"""Template use cases, independent of HTTP and SQLite implementation details."""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4

from .models import SuggestedTask, TaskTemplate
from .parameters import bind, render
from .repository import SQLiteTemplateRepository, TemplateRepository
from .validation import TASK_FIELDS, require_valid, validate


def instantiate(document: dict, values: dict) -> dict:
    require_valid(document)
    bindings = bind(document.get('parameters', []), values)
    tasks = [SuggestedTask(**{key: render(task.get(key, ''), bindings) for key in TASK_FIELDS})
             for task in document['suggested_tasks']]
    return TaskTemplate(
        template_name=render(document['template_name'], bindings),
        source_file=document.get('source_file', ''),
        system_prompt_extension=render(document.get('system_prompt_extension', ''), bindings),
        suggested_tasks=tasks,
    ).to_dict()


def require_identity(id: object, number: object, *, allow_empty: bool = False):
    if not isinstance(id, str) or (not id and not allow_empty):
        raise ValueError('模板 ID 必须是非空文本')
    if type(number) is not int or number < (0 if allow_empty else 1):
        raise ValueError('修订号或版本号必须是有效整数')


class Workbench:
    def __init__(self, path: str | Path | None = None, *, repository: TemplateRepository | None = None):
        if repository is None and path is None:
            raise ValueError('必须提供数据库路径或仓库实现')
        self.repository = repository if repository is not None else SQLiteTemplateRepository(path)

    def list(self) -> list[dict]:
        return self.repository.list()

    def save(self, document: dict, id: str = '', revision: int = 0) -> dict:
        require_valid(document, complete=False)
        require_identity(id, revision, allow_empty=True)
        id = id or uuid4().hex
        return dict(id=id, revision=self.repository.save(id, revision, document))

    def publish(self, id: str, revision: int) -> dict:
        require_identity(id, revision)
        version = self.repository.publish(id, revision, require_valid)
        return dict(id=id, version=version)

    def definition(self, id: str, version: int) -> dict:
        require_identity(id, version)
        return self.repository.release(id, version)

    def release(self, id: str, version: int, values: dict) -> dict:
        return instantiate(self.definition(id, version), values)


__all__ = ['Workbench', 'instantiate', 'validate']
