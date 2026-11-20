"""Document import shared by the SDK and CLI."""
from __future__ import annotations

from pathlib import Path

from .loader import load_directory, load_file
from .extractor import extract_tasks
from .converter import to_task_template
from .models import TaskTemplate

def extract_template(
    path: str,
    *,
    template_name: str = "",
    extra_context: str = "",
) -> TaskTemplate:
    """从文件或目录路径提取任务拆解模板。

    一键函数：文件加载 → 任务提取 → 模板转换。
    """
    p = Path(path).expanduser().resolve()

    if p.is_dir():
        files = load_directory(p)
        if not files:
            raise FileNotFoundError(f"目录 {p} 中没有可读取的文件")
        items = []
        for _, content, file_type in files:
            items.extend(extract_tasks(content, file_type))
    else:
        content, file_type = load_file(p)
        items = extract_tasks(content, file_type)

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

    return to_task_template(items, template_name=name, source_file=str(p), extra_context=extra_context)
