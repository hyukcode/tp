"""CLI 入口 —— 极简接口。

用法：
  template <path>            解析文件/目录，提取任务模板，存入本地库，打印摘要
  template <path> --json      输出完整 JSON（不存储）
  template ls                 列出已存储模板
  template rm  <name>         删除模板
  template show <name>        查看模板完整 JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .loader import load_directory, load_file
from .extractor import extract_tasks
from .converter import to_task_template
from .store import Store


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # ---- 无参数：显示帮助 ----
    if not argv:
        _print_help()
        return 1

    first = argv[0]

    # ---- 子命令：ls / rm / show ----
    if first in ("ls", "list"):
        return cmd_list()
    if first in ("rm", "remove"):
        name = argv[1] if len(argv) > 1 else ""
        return cmd_remove(name)
    if first == "show":
        name = argv[1] if len(argv) > 1 else ""
        return cmd_show(name)
    if first in ("-h", "--help", "help"):
        _print_help()
        return 0
    if first in ("-V", "--version"):
        print(f"template {__version__}")
        return 0

    # ---- 默认：<path> —— 解析 + 存储 ----
    return cmd_default(argv)


def _print_help() -> None:
    print(
        f"template {__version__} —— 从项目文件提取任务拆解模板\n"
        "\n"
        "用法:\n"
        "  template <path>              解析文件/目录，存储模板，打印摘要\n"
        "  template <path> --json       仅输出 JSON（不存储）\n"
        "  template <path> --tags tag1,tag2 --desc \"描述\"\n"
        "  template ls                  列出已存储的模板\n"
        "  template rm  <name>          删除模板\n"
        "  template show <name>         查看模板完整内容\n"
        "\n"
        f"模板存储目录: {Store().dir}\n"
    )


# ================================================================
#  默认命令：template <path> [flags]
# ================================================================
def cmd_default(argv: list[str]) -> int:
    path_str = argv[0]
    tags_str = ""
    desc = ""
    json_only = False
    compact = False

    # 简陋但够用的 flag 解析
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--tags" and i + 1 < len(argv):
            tags_str = argv[i + 1]; i += 2
        elif a == "--desc" and i + 1 < len(argv):
            desc = argv[i + 1]; i += 2
        elif a == "--json":
            json_only = True; i += 1
        elif a == "--compact":
            compact = True; i += 1
        elif a == "--planner-json":
            json_only = True; i += 1
        else:
            i += 1

    path = Path(path_str).expanduser().resolve()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    # 提取
    if path.is_dir():
        items, source, name = _extract_dir(path)
    else:
        items, source, name = _extract_file(path)

    template = to_task_template(items, template_name=name, source_file=source)

    # --json：只输出不存储
    if json_only:
        output = template.to_planner_json() if "--planner-json" in argv else template.to_dict()
        indent = None if compact else 2
        print(json.dumps(output, ensure_ascii=False, indent=indent))
        return 0

    # 存储
    store = Store()
    store.add(template.to_dict(), name=name, source=source, tags=tags, description=desc)
    print(f"已存储: {name}")
    print(store.catalog_text())
    return 0


# ================================================================
#  子命令
# ================================================================
def cmd_list() -> int:
    store = Store()
    items = store.list()
    if not items:
        print("（无已存储的模板）")
        print(f"目录: {store.dir}")
        return 0
    print(store.catalog_text())
    return 0


def cmd_remove(name: str) -> int:
    if not name:
        print("用法: template rm <name>", file=sys.stderr)
        return 1
    store = Store()
    if store.remove(name):
        print(f"已删除: {name}")
    else:
        print(f"模板不存在: {name}", file=sys.stderr)
        print(f"可用: {[m.get('name') for m in store.list()]}", file=sys.stderr)
        return 1
    return 0


def cmd_show(name: str) -> int:
    if not name:
        print("用法: template show <name>", file=sys.stderr)
        return 1
    store = Store()
    data = store.get(name)
    if data is None:
        print(f"模板不存在: {name}", file=sys.stderr)
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


# ================================================================
#  提取逻辑
# ================================================================
def _extract_file(path: Path) -> tuple[list[dict], str, str]:
    content, file_type = load_file(path)
    items = extract_tasks(content, file_type)
    return items, str(path), path.stem or "unnamed"


def _extract_dir(path: Path) -> tuple[list[dict], str, str]:
    files = load_directory(path)
    if not files:
        raise FileNotFoundError(f"目录 {path} 中没有可读取的文件")

    combined_parts: list[str] = []
    all_items: list[dict] = []
    for fpath, content, file_type in files:
        combined_parts.append(f"# 文件: {fpath}\n\n{content}")
        all_items.extend(extract_tasks(content, file_type))
    combined = "\n\n---\n\n".join(combined_parts)
    items = extract_tasks(combined, "markdown")
    if not items:
        items = all_items
    return items, str(path), path.name or "unnamed"


if __name__ == "__main__":
    raise SystemExit(main())
