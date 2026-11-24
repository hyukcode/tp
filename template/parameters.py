"""Parameter scanning and rendering, without expression evaluation."""
from __future__ import annotations
from dataclasses import dataclass


def is_parameter_name(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    first = value[0]
    return (first == '_' or first.isascii() and first.isalpha()) and all(
        character == '_' or character.isalnum() for character in value[1:]
    )


@dataclass(frozen=True)
class Placeholder:
    start: int
    end: int
    name: str


def placeholders(text: str) -> list[Placeholder]:
    result = []
    position = 0
    while position < len(text):
        start = text.find('{{', position)
        if start < 0:
            break
        end = text.find('}}', start + 2)
        if end < 0:
            raise ValueError('参数占位符缺少结束符 }}')
        name = text[start + 2:end].strip()
        if not is_parameter_name(name):
            raise ValueError(f'非法参数占位符: {text[start:end + 2]}')
        result.append(Placeholder(start, end + 2, name))
        position = end + 2
    return result


def render(text: str, bindings: dict[str, str]) -> str:
    parts = []
    position = 0
    for token in placeholders(text):
        if token.name not in bindings:
            raise ValueError(f'未定义参数: {token.name}')
        parts.extend((text[position:token.start], bindings[token.name]))
        position = token.end
    parts.append(text[position:])
    return ''.join(parts)


def bind(parameters: list[dict], values: dict) -> dict[str, str]:
    if not isinstance(values, dict):
        raise ValueError('参数值必须是对象')
    bindings = {}
    for parameter in parameters:
        name = parameter['name']
        value = values.get(name, parameter.get('default', ''))
        if not isinstance(value, str):
            raise ValueError(f'参数 {name} 必须是文本')
        if parameter.get('required', True) and not value.strip():
            raise ValueError(f'请填写参数: {name}')
        bindings[name] = value
    return bindings
