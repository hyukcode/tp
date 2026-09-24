#!/usr/bin/env python3
"""离线构建 tp-wy 纯 Python wheel（仅 stdlib zipfile/hashlib，无需网络/setuptools/wheel）。

用法：
    python scripts/build_wheel.py
产物：
    dist/tp_wy-0.2.0-py3-none-any.whl
目标机执行：
    pip install tp_wy-0.2.0-py3-none-any.whl
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import sys
import zipfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "template"
DIST = ROOT / "dist"
# wheel 文件名 / dist-info 目录用下划线（PEP 427），METADATA Name 用连字符
DIST_NAME = "tp_wy"
META_NAME = "tp-wy"
VERSION = "0.2.0"
DIST_INFO = f"{DIST_NAME}-{VERSION}.dist-info"


def _metadata() -> str:
    lines = ["Metadata-Version: 2.1", f"Name: {META_NAME}", f"Version: {VERSION}"]
    lines.append("Requires-Python: >=3.9")
    lines.append("License: MIT")
    return "\n".join(lines) + "\n"


WHEEL = """\
Wheel-Version: 1.0
Generator: tp-wy.build_wheel (stdlib-only)
Root-Is-Purelib: true
Tag: py3-none-any
"""

ENTRY_POINTS = """\
[console_scripts]
tp = template.cli:main
"""


def _all_py_files() -> list[str]:
    out = []
    for p in sorted(PKG.rglob("*.py")):
        out.append(p.relative_to(ROOT).as_posix())
    return out


def _hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build() -> Path:
    DIST.mkdir(exist_ok=True)
    whl = DIST / f"{DIST_NAME}-{VERSION}-py3-none-any.whl"
    files = _all_py_files()
    records: list[tuple[str, str, str]] = []

    with zipfile.ZipFile(whl, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            data = (ROOT / rel.replace("/", os.sep)).read_bytes()
            records.append((rel, _hash(data), str(len(data))))
            zf.writestr(rel, data)
        # 注入版本号文件（安装后 __init__.py 优先读它）
        ver_rel = "template/_version.py"
        ver_data = f'__version__ = "{VERSION}"\n'.encode("utf-8")
        records.append((ver_rel, _hash(ver_data), str(len(ver_data))))
        zf.writestr(ver_rel, ver_data)
        for name, content in [
            ("METADATA", _metadata()),
            ("WHEEL", WHEEL),
            ("entry_points.txt", ENTRY_POINTS),
        ]:
            data = content.encode("utf-8")
            records.append((f"{DIST_INFO}/{name}", _hash(data), str(len(data))))
            zf.writestr(f"{DIST_INFO}/{name}", data)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for path, h, size in records:
            w.writerow([path, f"sha256={h}", size])
        w.writerow([f"{DIST_INFO}/RECORD", "", ""])
        zf.writestr(f"{DIST_INFO}/RECORD", buf.getvalue().encode("utf-8"))

    print(f"[OK] wheel 已生成: {whl}")
    print(f"[OK] 共 {len(files)} 个模块，纯 Python，py3-none-any。")
    print(f"     目标机执行:  pip install {DIST_NAME}-{VERSION}-py3-none-any.whl")
    return whl


if __name__ == "__main__":
    build()
