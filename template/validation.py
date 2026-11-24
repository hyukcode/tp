"""Shared structural and publication checks; drafts may be incomplete."""
from __future__ import annotations
from .parameters import is_parameter_name, placeholders

TASK_FIELDS = ('title', 'description', 'acceptance', 'tool')
DOCUMENT_FIELDS = ('template_name', 'system_prompt_extension', 'source_file', 'description')


def validate(document: object, *, complete: bool = True) -> list[str]:
    if not isinstance(document, dict):
        return ['模板必须是对象']
    errors = []
    for key in DOCUMENT_FIELDS:
        if not isinstance(document.get(key, ''), str):
            errors.append(f'{key} 必须是文本')
    if complete and not document.get('template_name', ''):
        errors.append('请填写模板名称')
    elif complete and isinstance(document.get('template_name'), str) and not document['template_name'].strip():
        errors.append('请填写模板名称')
    tags = document.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        errors.append('标签必须是文本列表')
    tasks = document.get('suggested_tasks', [])
    if not isinstance(tasks, list):
        errors.append('任务必须是列表')
        tasks = []
    if complete and not tasks:
        errors.append('至少需要一个任务')
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            errors.append(f'任务 {index} 必须是对象')
            continue
        for key in TASK_FIELDS:
            value = task.get(key, '')
            if not isinstance(value, str):
                errors.append(f'任务 {index} 的 {key} 必须是文本')
            elif complete and key != 'tool' and not value.strip():
                errors.append(f'任务 {index} 的 {key} 不能为空')
    parameters = document.get('parameters', [])
    if not isinstance(parameters, list):
        errors.append('参数必须是列表')
        parameters = []
    names = set()
    for parameter in parameters:
        if not isinstance(parameter, dict):
            errors.append('参数必须是对象')
            continue
        name = parameter.get('name', '')
        if not isinstance(name, str):
            errors.append('参数名必须是文本')
        elif complete:
            if not is_parameter_name(name) or name in names:
                errors.append('参数名必须是唯一标识符')
            names.add(name)
        if not isinstance(parameter.get('default', ''), str):
            errors.append('参数默认值必须是文本')
        if not isinstance(parameter.get('required', True), bool):
            errors.append('required 必须是布尔值')
    if complete:
        errors.extend(validate_references(document, tasks, names))
    return errors


def validate_references(document: dict, tasks: list, names: set[str]) -> list[str]:
    fields = [document.get(key, '') for key in ('template_name', 'system_prompt_extension')]
    fields.extend(task.get(key, '') for task in tasks if isinstance(task, dict) for key in TASK_FIELDS)
    errors = []
    used = set()
    for text in fields:
        if not isinstance(text, str):
            continue
        try:
            used.update(token.name for token in placeholders(text))
        except ValueError as error:
            errors.append(str(error))
    errors.extend(f'未定义参数: {name}' for name in sorted(used - names))
    return errors


def require_valid(document: object, *, complete: bool = True) -> None:
    errors = validate(document, complete=complete)
    if errors:
        raise ValueError('\n'.join(errors))
