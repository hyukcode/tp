"""Transport-independent API actions. No sockets or persistence SQL here."""
from __future__ import annotations
from .extractor import extract_tasks
from .workbench import Workbench, instantiate, validate


class TemplateAPI:
    def __init__(self, workbench: Workbench):
        self.workbench = workbench
        self.actions = {
            'save': self.save,
            'validate': self.validate,
            'preview': self.preview,
            'publish': self.publish,
            'release': self.release,
            'definition': self.definition,
            'import': self.import_document,
        }

    def dispatch(self, action: str, data: dict):
        if action not in self.actions:
            raise LookupError('接口不存在')
        if not isinstance(data, dict):
            raise ValueError('请求必须是对象')
        try:
            return self.actions[action](data)
        except KeyError as error:
            raise ValueError(f'缺少字段: {error.args[0]}') from error

    def save(self, data):
        return self.workbench.save(data['document'], data.get('id', ''), data.get('revision', 0))

    def validate(self, data):
        return {'errors': validate(data['document'])}

    def preview(self, data):
        return instantiate(data['document'], data.get('values', {}))

    def publish(self, data):
        return self.workbench.publish(data['id'], data['revision'])

    def release(self, data):
        return self.workbench.release(data['id'], data['version'], data.get('values', {}))

    def definition(self, data):
        return self.workbench.definition(data['id'], data['version'])

    def import_document(self, data):
        name = data.get('name', '')
        if not isinstance(name, str):
            raise ValueError('名称必须是文本')
        return {
            'template_name': name,
            'system_prompt_extension': '',
            'parameters': [],
            'suggested_tasks': extract_tasks(data['content'], 'markdown'),
        }
