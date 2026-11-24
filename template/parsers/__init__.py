"""Composable import strategies with a stable dictionary boundary."""
from functools import partial
from .markdown import parse_markdown
from .code import parse_code
from .text import parse_text, parse_configuration

PARSERS = {'markdown': parse_markdown}
for language in ('python', 'javascript', 'typescript', 'go', 'rust', 'java', 'c', 'cpp'):
    PARSERS[language] = partial(parse_code, file_type=language)
for format_name in ('json', 'yaml', 'toml'):
    PARSERS[format_name] = partial(parse_configuration, file_type=format_name)


def parse(content: str, file_type: str):
    return PARSERS.get(file_type, parse_text)(content)
