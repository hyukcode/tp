"""文件加载：读取任意文本/代码文件，返回内容与文件类型。"""

from __future__ import annotations

from pathlib import Path

# 支持的文件扩展名 → 类型标记
EXT_MAP: dict[str, str] = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".rst": "text",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


def load_file(path: str | Path) -> tuple[str, str]:
    """读取文件，返回 (content, file_type)。

    file_type 为 ext_map 中对应的类型标记，未知扩展名返回 "text"。
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {p}")
    if not p.is_file():
        raise IsADirectoryError(f"路径是目录: {p}")

    content = p.read_text(encoding="utf-8")
    if "\x00" in content:
        raise ValueError(f"不能读取二进制文件: {p}")
    ext = p.suffix.lower()
    file_type = EXT_MAP.get(ext, "text")

    return content, file_type


def load_files(paths: list[str | Path]) -> list[tuple[str, str, str]]:
    """批量读取多个文件，返回 [(file_path, content, file_type), ...]。
    跳过目录和二进制文件。"""
    results: list[tuple[str, str, str]] = []
    for path in paths:
        try:
            content, ft = load_file(path)
            results.append((str(path), content, ft))
        except (OSError, UnicodeError, ValueError):
            continue
    return results


def load_directory(dir_path: str | Path, *, glob_pattern: str = "**/*") -> list[tuple[str, str, str]]:
    """读取目录下所有匹配文件，返回 [(file_path, content, file_type), ...]。
    默认读取所有文件；可通过 glob_pattern 筛选（如 "**/*.md"）。"""
    p = Path(dir_path).expanduser().resolve()
    if not p.is_dir():
        raise NotADirectoryError(f"路径不是目录: {p}")

    paths = [file for file in sorted(p.glob(glob_pattern))
             if file.is_file() and file.suffix.lower() not in _SKIP_EXTENSIONS
             and not any(part in {'.git', '.venv', 'node_modules', '__pycache__', 'dist', 'build'}
                         for part in file.relative_to(p).parts)]
    return load_files(paths)


_SKIP_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}
