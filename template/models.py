"""模板数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SuggestedTask:
    """一个建议的子任务条目。

    注意：模板不指定 executor（由哪个 agent 执行）和 depends_on（任务间依赖），
    这两项由 tasker 的 LLM 拆分阶段根据任务内容自行决定。
    """

    title: str
    description: str
    acceptance: str = ""
    tool: str = ""


@dataclass
class TaskTemplate:
    """从文件中提取出的任务拆解模板。

    可直接注入 tasker planner 的 SYSTEM_PROMPT 作为拆解参考。
    """

    template_name: str = ""
    source_file: str = ""
    system_prompt_extension: str = ""  # 追加到 planner SYSTEM_PROMPT 的上下文
    suggested_tasks: list[SuggestedTask] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "template_name": self.template_name,
            "source_file": self.source_file,
            "system_prompt_extension": self.system_prompt_extension,
            "suggested_tasks": [
                {
                    "title": t.title,
                    "description": t.description,
                    "acceptance": t.acceptance,
                    "tool": t.tool,
                }
                for t in self.suggested_tasks
            ],
        }

    def to_planner_json(self) -> dict:
        """输出与 tasker planner 兼容的 JSON 结构。"""
        return {
            "objective": self.template_name,
            "rationale": self.system_prompt_extension,
            "tasks": [
                {
                    "id": f"t{i+1}",
                    "title": t.title,
                    "description": t.description,
                    "tool": t.tool,
                    "acceptance": t.acceptance,
                }
                for i, t in enumerate(self.suggested_tasks)
            ],
        }
