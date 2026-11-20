"""tasker-template —— 从项目文件中提取任务拆解模板。

用法：
    from template import extract_template
    template = extract_template("path/to/readme.md")
    print(template.to_planner_json())

    from template import store_template, list_templates, catalog_for_llm
    store_template("spec/payment.md", tags=["payment", "api"])
    print(catalog_for_llm())  # 供 LLM 决策使用
"""

from __future__ import annotations

from .importer import extract_template
from .models import SuggestedTask, TaskTemplate
from .loader import load_file, load_files, load_directory
from .extractor import extract_tasks
from .converter import to_task_template, to_planner_json
from .store import (
    Store,
    catalog_for_llm,
    get_template,
    list_templates,
    remove_template,
    search_templates,
    store_template,
)

__version__ = "0.0.0"
try:
    from ._version import __version__  # type: ignore[attr-defined]  # noqa: F401
except ImportError:
    try:
        import re
        from pathlib import Path

        _text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
        _m = re.search(r'^version\s*=\s*"([^"]+)"', _text, re.MULTILINE)
        if _m:
            __version__ = _m.group(1)
    except Exception:
        pass
__all__ = [
    "extract_template",
    "TaskTemplate",
    "SuggestedTask",
    "load_file",
    "load_files",
    "load_directory",
    "extract_tasks",
    "to_task_template",
    "to_planner_json",
    "Store",
    "store_template",
    "list_templates",
    "search_templates",
    "get_template",
    "remove_template",
    "catalog_for_llm",
]
