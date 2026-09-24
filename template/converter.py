"""模板转换：将提取的任务条目转换为 tasker planner 兼容的模板。"""

from __future__ import annotations

from .models import SuggestedTask, TaskTemplate


def to_task_template(
    items: list[dict],
    template_name: str = "",
    source_file: str = "",
    *,
    extra_context: str = "",
) -> TaskTemplate:
    """将 extractor 返回的条目列表组装为 TaskTemplate。"""
    suggested: list[SuggestedTask] = []
    for item in items:
        suggested.append(
            SuggestedTask(
                title=item.get("title", ""),
                description=item.get("description", ""),
                acceptance=item.get("acceptance", ""),
                tool=item.get("tool", item.get("skill", "")),
            )
        )

    # 构造 system_prompt_extension：注入到 LLM 拆分 prompt 的附加上下文
    ext_parts: list[str] = []
    if extra_context:
        ext_parts.append(extra_context)
    if source_file:
        ext_parts.append(f"以下模板提取自文件: {source_file}")
    # 任务清单只保存在 suggested_tasks 中，避免同时以自然语言重复注入
    # planner，导致模型把模板本身当成待分析内容。

    return TaskTemplate(
        template_name=template_name or "从文件提取的模板",
        source_file=source_file,
        system_prompt_extension="\n\n".join(ext_parts),
        suggested_tasks=suggested,
    )


def to_planner_json(template: TaskTemplate) -> dict:
    """输出与 tasker planner SYSTEM_PROMPT 兼容的 JSON 结构。"""
    return template.to_planner_json()
