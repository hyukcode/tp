"""Read the project's literal version without executing configuration."""
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version


def project_version(path: Path) -> str:
    section = ''
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
        if section != 'project':
            continue
        key, separator, value = line.partition('=')
        if separator and key.strip() == 'version':
            value = value.strip()
            if value and value[0] in '\"\'':
                end = value.find(value[0], 1)
                if end > 1:
                    return value[1:end]
            raise ValueError('project.version 必须是带引号的文本')
    raise ValueError('缺少 project.version')


def package_version() -> str:
    try:
        from ._version import __version__
        return __version__
    except ImportError:
        pass
    source = Path(__file__).resolve().parent.parent / 'pyproject.toml'
    if source.is_file():
        return project_version(source)
    try:
        return version('tp-wy')
    except PackageNotFoundError:
        return '0.0.0'
