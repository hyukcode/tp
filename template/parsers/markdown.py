"""A small line-state parser for task headings, labels and fenced examples."""
from __future__ import annotations

from dataclasses import dataclass, field
from ..models import SuggestedTask

LABELS = {
    '目标': 'title', '任务': 'title', '描述': 'description',
    '工具': 'tool', '技能': 'tool', '标准': 'acceptance',
    '验收标准': 'acceptance', '完成标准': 'acceptance', '验收': 'acceptance',
}


def label_value(line: str) -> tuple[str, str] | None:
    for index, character in enumerate(line):
        if character in ':：':
            field_name = LABELS.get(line[:index].strip())
            if field_name:
                return field_name, line[index + 1:].strip()
            return None
    return None


def heading(line: str) -> tuple[int, str] | None:
    text = line.lstrip(' ')
    if len(line) - len(text) > 3:
        return None
    level = len(text) - len(text.lstrip('#'))
    if not 1 <= level <= 6 or len(text) <= level or not text[level].isspace():
        return None
    title = text[level:].strip()
    return (level, title) if title else None


@dataclass
class TaskSection:
    title: str
    active: str = 'description'
    fields: dict[str, list[str]] = field(default_factory=lambda: {
        'description': [], 'tool': [], 'acceptance': [],
    })

    def __post_init__(self):
        label = label_value(self.title)
        self.fixed_title = bool(label and label[0] == 'title' and label[1])
        if self.fixed_title:
            self.title = label[1]

    def append(self, line: str, *, literal: bool = False):
        text = line.strip()
        if not text:
            return
        label = None if literal else label_value(text)
        if label is None:
            self.fields[self.active].append(text)
            return
        name, value = label
        if name == 'title':
            if value and not self.fixed_title:
                self.title = value
            self.active = 'description'
        else:
            self.active = name
            if value:
                self.fields[name].append(value)

    def task(self) -> SuggestedTask:
        return SuggestedTask(self.title, **{
            name: '\n'.join(lines).strip()[:500 if name == 'tool' else 2000]
            for name, lines in self.fields.items()
        })


def parse_markdown(content: str) -> list[SuggestedTask]:
    tasks = []
    section = None
    fence_character = ''
    fence_length = 0
    for line in content.splitlines():
        text = line.strip()
        if fence_character:
            if section:
                section.append(line, literal=True)
            run = len(text) - len(text.lstrip(fence_character))
            if run >= fence_length and not text[run:].strip():
                fence_character = ''
            continue
        if text.startswith(('```', '~~~')):
            fence_character = text[0]
            fence_length = len(text) - len(text.lstrip(fence_character))
            if section:
                section.append(line, literal=True)
            continue
        marker = heading(line)
        if marker is None:
            if section:
                section.append(line)
            continue
        level, title = marker
        if level <= 2:
            if section:
                tasks.append(section.task())
            section = TaskSection(title) if level == 2 else None
        elif section:
            section.append(f'**{title}**', literal=True)
    if section:
        tasks.append(section.task())
    return tasks
