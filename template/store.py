"""Legacy named-file library; retained for taskdispatcher automatic lookup."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from .catalog import catalog_text
from .json_files import read_object, write_object


def _safe_filename(name: str) -> str:
    safe = ''.join(character if character.isalnum() or character in '_-' else '-'
                   for character in name).strip('-').lower()
    return safe or 'template'


class Store:
    def __init__(self, store_dir: str | Path | None = None):
        self._dir = Path(store_dir).expanduser() if store_dir else Path.home() / '.tasker' / 'templates'
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def dir(self) -> Path:
        return self._dir

    def _path(self, name: str) -> Path:
        return self._dir / (_safe_filename(name) + '.json')

    def _records(self) -> list[dict]:
        records = []
        for path in sorted(self._dir.glob('*.json')):
            record = read_object(path)
            if record and isinstance(record.get('_meta'), dict) and record['_meta']:
                records.append(record)
        return records

    def add(self, template: dict, *, name: str = '', source: str = '',
            tags: list[str] | None = None, description: str = '') -> Path:
        name = name or template.get('template_name', 'unnamed')
        meta = {
            'v': 1, 'name': name,
            'source': source or template.get('source_file', ''),
            'tags': sorted(set(tags or [])),
            'desc': description.strip()[:200],
            'stored_at': datetime.now(timezone.utc).isoformat(),
        }
        document = {'_meta': meta}
        document.update({key: value for key, value in template.items() if key != '_meta'})
        path = self._path(name)
        write_object(path, document)
        return path

    def add_file(self, file_path: str | Path, *, tags: list[str] | None = None,
                 description: str = '') -> Path:
        from .importer import extract_template
        template = extract_template(str(file_path))
        count = len(template.suggested_tasks)
        description = description or (f'{count} 个子任务' if count else '')
        return self.add(template.to_dict(), tags=tags, description=description)

    def list(self) -> list[dict]:
        return [record['_meta'] for record in self._records()]

    def get(self, name: str) -> dict | None:
        return read_object(self._path(name))

    def remove(self, name: str) -> bool:
        try:
            self._path(name).unlink()
        except FileNotFoundError:
            return False
        return True

    def search(self, *, tags: list[str] | None = None, keyword: str = '') -> list[dict]:
        result = []
        for record in self._records():
            meta = record['_meta']
            if tags and not any(tag in (meta.get('tags') or []) for tag in tags):
                continue
            if keyword and keyword.lower() not in json.dumps(record, ensure_ascii=False).lower():
                continue
            result.append(meta)
        return result

    def catalog_text(self) -> str:
        return catalog_text(self._records())


# 模块级便捷函数
_default_store: Store | None = None


def _get_store() -> Store:
    global _default_store
    if _default_store is None:
        _default_store = Store()
    return _default_store


def store_template(file_path: str, *, tags: list[str] | None = None) -> Path:
    """从文件提取并存储模板。"""
    return _get_store().add_file(file_path, tags=tags)


def list_templates() -> list[dict]:
    """列出所有已存储模板的元信息。"""
    return _get_store().list()


def search_templates(tags: list[str] | None = None, keyword: str = "") -> list[dict]:
    """搜索模板。"""
    return _get_store().search(tags=tags, keyword=keyword)


def get_template(name: str) -> dict | None:
    """获取模板完整内容。"""
    return _get_store().get(name)


def remove_template(name: str) -> bool:
    """删除模板。"""
    return _get_store().remove(name)


def catalog_for_llm() -> str:
    """生成供 LLM 决策的模板目录摘要。"""
    return _get_store().catalog_text()
