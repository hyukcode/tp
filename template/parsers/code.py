"""Python AST extraction; other languages use a documented lexical heuristic."""
from __future__ import annotations

import ast
from ..models import SuggestedTask
from .text import parse_text


def symbol_task(name: str, kind: str = '函数') -> SuggestedTask:
    return SuggestedTask(f'实现/修改 {kind} `{name}`', f'处理与 `{name}` 相关的代码逻辑。')


def parse_python(content: str) -> list[SuggestedTask]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return parse_text(content)
    definitions = [node for node in ast.walk(tree)
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    definitions.sort(key=lambda node: (node.lineno, node.col_offset))
    return [symbol_task(node.name, '类' if isinstance(node, ast.ClassDef) else '函数')
            for node in definitions[:30]]


def tokens(content: str, file_type: str = ""):
    """Skip comments/string literals; emit identifiers and punctuation in source order."""
    position = 0
    while position < len(content):
        character = content[position]
        if content.startswith('//', position):
            end = content.find('\n', position)
            position = len(content) if end < 0 else end + 1
        elif content.startswith('/*', position):
            end = content.find('*/', position + 2)
            position = len(content) if end < 0 else end + 2
        elif character == "'" and file_type == 'rust' and position + 1 < len(content) and content[position + 1].isalpha() and (position + 2 >= len(content) or content[position + 2] != "'"):
            # A Rust lifetime such as 'a is not a quoted string.
            yield character
            position += 1
        elif character in '\"\'`':
            quote = character
            position += 1
            while position < len(content):
                if content[position] == '\\':
                    position += 2
                elif content[position] == quote:
                    position += 1
                    break
                else:
                    position += 1
        elif character.isalpha() or character in '_$':
            end = position + 1
            while end < len(content) and (content[end].isalnum() or content[end] in '_$'):
                end += 1
            yield content[position:end]
            position = end
        else:
            if not character.isspace():
                yield character
            position += 1


def parse_code(content: str, file_type: str) -> list[SuggestedTask]:
    if file_type == 'python':
        return parse_python(content)
    if file_type not in ('javascript', 'typescript', 'go', 'rust'):
        return parse_text(content)
    stream = list(tokens(content, file_type))
    keywords = {'javascript': ('function', 'class'), 'typescript': ('function', 'class'),
                'go': ('func',), 'rust': ('fn',)}[file_type]
    tasks = []
    for index, token in enumerate(stream[:-1]):
        if file_type in ('javascript', 'typescript') and token in ('const', 'let', 'var'):
            name = arrow_name(stream, index)
            if name:
                tasks.append(symbol_task(name))
                if len(tasks) == 30:
                    break
            continue
        if token not in keywords:
            continue
        cursor = index + 1
        if file_type == 'go' and stream[cursor] == '(':
            depth = 1
            cursor += 1
            while cursor < len(stream) and depth:
                depth += (stream[cursor] == '(') - (stream[cursor] == ')')
                cursor += 1
        if cursor < len(stream) and stream[cursor].isidentifier():
            tasks.append(symbol_task(stream[cursor], '类' if token == 'class' else '函数'))
        if len(tasks) == 30:
            break
    return tasks


def arrow_name(stream: list[str], index: int) -> str | None:
    """Recognize a variable assigned an arrow function, not arbitrary calls."""
    if index + 3 >= len(stream) or not stream[index + 1].isidentifier() or stream[index + 2] != '=':
        return None
    name = stream[index + 1]
    cursor = index + 3
    if stream[cursor] == 'async':
        cursor += 1
    if cursor >= len(stream):
        return None
    if stream[cursor] == '(':
        depth = 1
        cursor += 1
        while cursor < len(stream) and depth:
            depth += (stream[cursor] == '(') - (stream[cursor] == ')')
            cursor += 1
    elif stream[cursor].isidentifier():
        cursor += 1
    else:
        return None
    return name if stream[cursor:cursor + 2] == ['=', '>'] else None
