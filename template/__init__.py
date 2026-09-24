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


def extract_template(
    path: str,
    *,
    template_name: str = "",
    extra_context: str = "",
) -> TaskTemplate:
    """从文件或目录路径提取任务拆解模板。

    一键函数：文件加载 → 任务提取 → 模板转换。
    """
    import os
    from pathlib import Path

    p = Path(path).expanduser().resolve()

    if p.is_dir():
        files = load_directory(p)
        if not files:
            raise FileNotFoundError(f"目录 {p} 中没有可读取的文件")
        combined_parts: list[str] = []
        all_items: list[dict] = []
        for fpath, content, file_type in files:
            combined_parts.append(f"# 文件: {fpath}\n\n{content}")
            all_items.extend(extract_tasks(content, file_type))
        combined = "\n\n---\n\n".join(combined_parts)
        items = extract_tasks(combined, "markdown")
        if not items:
            items = all_items
        source = str(p)
    else:
        content, file_type = load_file(p)
        items = extract_tasks(content, file_type)
        source = str(p)

    name = template_name or p.stem or "从文件提取的模板"

    # 尝试读取 README 作为额外的上下文
    if not extra_context:
        try:
            readme_dir = p.parent if p.is_file() else p
            readme = readme_dir / "README.md"
            if readme.exists():
                extra_context = readme.read_text(encoding="utf-8", errors="replace")[:2000]
        except Exception:
            pass

    return to_task_template(items, template_name=name, source_file=source, extra_context=extra_context)
