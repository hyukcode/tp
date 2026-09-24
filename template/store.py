"""模板本地存储。

模板文件存放在 ~/.tasker/templates/ 目录，跨平台兼容（macOS / Linux / Windows）。

文件格式：单 JSON 文件，_meta 作为第一个 key 携带元信息：
  {
    "_meta": {"v":1,"name":"...","source":"...","tags":[...],"desc":"...","stored_at":"..."},
    "template_name": "...",
    "system_prompt_extension": "...",
    "suggested_tasks": [...]
  }

LLM 通过读取 _meta 中的 tags/desc/name 来决定调用哪个模板。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _store_dir() -> Path:
    """获取模板存储目录（创建若不存在）。"""
    p = Path.home() / ".tasker" / "templates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_filename(name: str) -> str:
    """将模板名转为安全的文件名（仅保留字母数字和连字符）。"""
    import re

    safe = re.sub(r"[^\w\-]", "-", name).strip("-").lower()
    return safe or "template"


class Store:
    """模板本地存储。"""

    def __init__(self, store_dir: str | Path | None = None):
        self._dir = Path(store_dir) if store_dir else _store_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def dir(self) -> Path:
        return self._dir

    # ---- 写入 ----
    def add(
        self,
        template: dict,
        *,
        name: str = "",
        source: str = "",
        tags: list[str] | None = None,
        description: str = "",
    ) -> Path:
        """存储一个模板，返回文件路径。

        template 是 to_dict() 输出的 dict。
        name/source/tags/description 用于构造 _meta。
        """
        name = name or template.get("template_name", "unnamed")
        tpl = dict(template)  # shallow copy

        # 构造 _meta，始终放在最前面
        meta: dict = {
            "v": 1,
            "name": name,
            "source": source or template.get("source_file", ""),
            "tags": sorted(set(tags or [])),
            "desc": (description or "").strip()[:200],
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        # _meta 放在第一层 key 的最前面
        out = {"_meta": meta}
        out.update(tpl)

        filename = _safe_filename(name) + ".json"
        fpath = self._dir / filename
        fpath.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return fpath

    def add_file(self, file_path: str | Path, *, tags: list[str] | None = None, description: str = "") -> Path:
        """直接从项目文件路径提取并存储模板。"""
        from . import extract_template

        tpl = extract_template(str(file_path))
        name = tpl.template_name
        source = str(Path(file_path).resolve())
        # 优先用传入的 description，否则用任务数量作为摘要
        desc = description or (f"{len(tpl.suggested_tasks)} 个子任务" if tpl.suggested_tasks else "")
        return self.add(
            tpl.to_dict(), name=name, source=source, tags=tags, description=desc,
        )

    # ---- 读取 ----
    def list(self) -> list[dict]:
        """列出所有已存储模板的 _meta 信息（只读第一层元数据）。"""
        result: list[dict] = []
        for f in sorted(self._dir.glob("*.json")):
            meta = self._read_meta(f)
            if meta:
                result.append(meta)
        return result

    def get(self, name: str) -> dict | None:
        """按名称读取完整模板。"""
        fname = _safe_filename(name) + ".json"
        fpath = self._dir / fname
        if not fpath.exists():
            return None
        try:
            return json.loads(fpath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def remove(self, name: str) -> bool:
        """删除一个模板。"""
        fname = _safe_filename(name) + ".json"
        fpath = self._dir / fname
        if fpath.exists():
            fpath.unlink()
            return True
        return False

    def search(self, *, tags: list[str] | None = None, keyword: str = "") -> list[dict]:
        """按 tags 或关键词搜索模板，返回匹配的 _meta 列表。

        关键词同时搜索元数据和完整模板内容，确保 tasker 的自动匹配
        可以命中任务标题、工具和验收标准，而不只是模板名/标签。
        """
        if not tags and not keyword:
            return self.list()
        result: list[dict] = []
        for fpath in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                meta = data.get("_meta") or {}
            except (json.JSONDecodeError, OSError):
                continue
            if tags and not any(t in (meta.get("tags") or []) for t in tags):
                continue
            if keyword:
                kw = keyword.lower()
                hay = json.dumps(data, ensure_ascii=False).lower()
                if kw not in hay:
                    continue
            result.append(meta)
        return result

    def catalog_text(self) -> str:
        """生成供 LLM 使用的模板目录摘要文本。"""
        items = self.list()
        if not items:
            return "（无已存储的模板。用 `template store <file>` 存入模板。）"
        lines = [f"共 {len(items)} 个模板可用："]
        for m in items:
            tags = ", ".join(m.get("tags") or [])
            name = m.get("name", "?")
            desc = (m.get("desc") or "")[:80]
            line = f"  - **{name}**"
            if tags:
                line += f"  [{tags}]"
            if desc:
                line += f"  {desc}"
            # 目录仍保持摘要性质，但补充任务标题/工具，帮助 planner 选择模板。
            try:
                tpl = self.get(name) or {}
                tasks = tpl.get("suggested_tasks") or []
                hints = []
                for task in tasks[:6]:
                    title = str(task.get("title") or "").strip()
                    tool = str(task.get("tool") or task.get("skill") or "").strip()
                    hint = title
                    if tool:
                        hint += f" [{tool}]"
                    if hint:
                        hints.append(hint)
                if hints:
                    line += "\n      任务: " + "；".join(hints)
            except Exception:
                pass
            lines.append(line)
        return "\n".join(lines)

    # ---- 内部 ----
    @staticmethod
    def _read_meta(fpath: Path) -> dict | None:
        """快速读取文件第一层 _meta（不解析完整 JSON 的情况下）。

        策略：读前几 KB，用简单正则提取 _meta 对象。
        如果文件很大，这个方法远快于完整 JSON 解析。
        """
        try:
            head = fpath.read_text(encoding="utf-8")[:4096]
            # 尝试完整 JSON 解析（文件通常 < 100KB，开销可接受）
            data = json.loads(fpath.read_text(encoding="utf-8"))
            return data.get("_meta")
        except (json.JSONDecodeError, OSError):
            return None


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
