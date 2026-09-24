"""内容提取：根据文件类型，用启发式规则提取隐含的任务描述。"""

from __future__ import annotations

import json
import re


def extract_tasks(content: str, file_type: str) -> list[dict]:
    """从文本内容中提取任务条目。

    返回 list[dict]，每个 dict 含 title, description, acceptance。
    """
    if file_type == "markdown":
        return _extract_markdown(content)
    if file_type in ("python", "javascript", "typescript", "go", "rust", "java", "c", "cpp"):
        return _extract_code(content, file_type)
    if file_type in ("json", "yaml", "toml"):
        return _extract_structured(content, file_type)
    return _extract_text(content)


# ---- Markdown ----
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_TASK_LABEL = re.compile(
    r"^\s*(目标|任务|工具|技能|标准|验收标准|完成标准|验收|描述)\s*[:：]\s*(.*)$"
)


def _extract_markdown(content: str) -> list[dict]:
    """按 Markdown 标题层级拆分：每个 ## 标题为一个潜在任务。
    ### 子标题作为子描述；# 标题作为模板名。"""
    lines = content.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    current_lines: list[str] = []
    template_name = ""

    for line in lines:
        m = _MD_HEADING.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # 保存前一个 section（即使没有正文也保留标题）
            if current is not None:
                _finalize_task(current, current_lines)
                sections.append(current)

            if level == 1:
                template_name = template_name or title
                current = None
                current_lines = []
            elif level == 2:
                current = {"title": title, "acceptance": "", "tool": ""}
                current_lines = []
            elif level >= 3 and current is not None:
                # 子标题成为 description 的一部分
                current_lines.append(f"**{title}**")
            else:
                current = None
                current_lines = []
        else:
            if current is not None and line.strip():
                current_lines.append(line.strip())

    # 最后一个 section（即使没有正文也保留标题）
    if current is not None:
        _finalize_task(current, current_lines)
        sections.append(current)

    # 默认无模板名时从首行取
    if not template_name:
        template_name = (sections[0]["title"] if sections else "未命名模板")

    return sections


def _finalize_task(task: dict, lines: list[str]) -> None:
    """把任务区块中的目标/工具/标准标签转换成结构化字段。

    兼容旧模板：没有标签的正文仍然完整进入 description。
    """
    title = str(task.get("title", "")).strip()
    heading = re.match(r"^(?:目标|任务)\s*[:：]\s*(.+)$", title)
    if heading:
        task["title"] = heading.group(1).strip()

    descriptions: list[str] = []
    tools: list[str] = []
    acceptances: list[str] = []
    active: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        match = _TASK_LABEL.match(line)
        if match:
            label, value = match.groups()
            if label in ("工具", "技能"):
                active = "tool"
                if value:
                    tools.append(value.strip())
            elif label in ("标准", "验收标准", "完成标准", "验收"):
                active = "acceptance"
                if value:
                    acceptances.append(value.strip())
            elif label == "描述":
                active = "description"
                if value:
                    descriptions.append(value.strip())
            elif label in ("目标", "任务"):
                if value and not heading:
                    task["title"] = value.strip()
                active = None
            continue

        if active == "tool":
            tools.append(line)
        elif active == "acceptance":
            acceptances.append(line)
        else:
            descriptions.append(line)

    task["description"] = _clean_section_body(descriptions)
    task["tool"] = "\n".join(tools)[:500]
    task["acceptance"] = _clean_section_body(acceptances)


def _clean_section_body(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    # 限制长度，避免 context 过大
    return text[:2000]


# ---- 代码文件 ----
def _extract_code(content: str, file_type: str) -> list[dict]:
    """从代码文件中提取函数/类签名和 docstring 作为任务参考。"""
    items: list[dict] = []

    if file_type == "python":
        items = _extract_python(content)
    elif file_type in ("javascript", "typescript"):
        items = _extract_js_ts(content)
    elif file_type == "go":
        items = _extract_go(content)
    elif file_type == "rust":
        items = _extract_rust(content)
    else:
        items = _extract_generic_code(content)

    return items


_PY_DEF = re.compile(
    r"^\s*(?:(?:async\s+)?def\s+(\w+)\s*\([^)]*\)|class\s+(\w+))",
    re.MULTILINE,
)


def _extract_python(content: str) -> list[dict]:
    items: list[dict] = []
    for m in _PY_DEF.finditer(content):
        name = m.group(1) or m.group(2)
        kind = "函数" if m.group(1) else "类"
        items.append({
            "title": f"实现/修改 {kind} `{name}`",
            "description": f"处理与 `{name}` 相关的代码逻辑。",
            "acceptance": "",
        })
    return items[:30]  # 截断，避免模板过大


_JS_TS_DEF = re.compile(
    r"^\s*(?:(?:export\s+)?(?:async\s+)?function\s+(\w+)|(?:export\s+)?class\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()",
    re.MULTILINE,
)


def _extract_js_ts(content: str) -> list[dict]:
    items: list[dict] = []
    for m in _JS_TS_DEF.finditer(content):
        name = m.group(1) or m.group(2) or m.group(3)
        kind = "函数" if m.group(1) or m.group(3) else "类"
        items.append({
            "title": f"实现/修改 {kind} `{name}`",
            "description": f"处理与 `{name}` 相关的代码逻辑。",
            "acceptance": "",
        })
    return items[:30]


_GO_DEF = re.compile(r"^\s*func\s+(?:\(\s*\w+\s+\*?\w+\s*\)\s+)?(\w+)\s*\(", re.MULTILINE)


def _extract_go(content: str) -> list[dict]:
    items: list[dict] = []
    for m in _GO_DEF.finditer(content):
        name = m.group(1)
        items.append({
            "title": f"实现/修改函数 `{name}`",
            "description": f"处理与 `{name}` 相关的代码逻辑。",
            "acceptance": "",
        })
    return items[:30]


_RUST_DEF = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]", re.MULTILINE)


def _extract_rust(content: str) -> list[dict]:
    items: list[dict] = []
    for m in _RUST_DEF.finditer(content):
        items.append({
            "title": f"实现/修改函数 `{m.group(1)}`",
            "description": f"处理与 `{m.group(1)}` 相关的代码逻辑。",
            "acceptance": "",
        })
    return items[:30]


def _extract_generic_code(content: str) -> list[dict]:
    # 回退：按空行分段
    return _extract_text(content)


# ---- 结构化文件 ----
def _extract_structured(content: str, file_type: str) -> list[dict]:
    """从 JSON/YAML/TOML 中提取顶层 key 作为任务参考。"""
    try:
        if file_type == "json":
            data = json.loads(content)
        elif file_type == "toml":
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
                data = tomllib.loads(content)
            else:
                return _extract_text(content)
        else:  # yaml
            return _extract_text(content)
    except Exception:
        return _extract_text(content)

    if not isinstance(data, dict):
        return _extract_text(content)

    items: list[dict] = []
    for key in data:
        items.append({
            "title": f"处理配置项 `{key}`",
            "description": f"根据 {key} 的配置内容进行相应处理。",
            "acceptance": "",
        })
    return items[:30]


# ---- 纯文本 ----
_PARAGRAPH = re.compile(r"(.+?)(?:\n\n|$)", re.DOTALL)


def _extract_text(content: str) -> list[dict]:
    """按空行分隔的段落作为任务组。"""
    paragraphs: list[str] = []
    for m in _PARAGRAPH.finditer(content):
        text = m.group(1).strip()
        if text and len(text) > 10:  # 跳过太短的段落
            paragraphs.append(text)

    items: list[dict] = []
    for i, para in enumerate(paragraphs[:20]):  # 最多 20 个
        # 取首句作为标题
        first_sentence = para.split("。")[0].split(".")[0].strip()[:80]
        items.append({
            "title": first_sentence,
            "description": para[:1500],
            "acceptance": "",
        })

    return items
