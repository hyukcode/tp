"""CLI adapter: parse arguments and delegate to the shared importer/store."""
from __future__ import annotations
import argparse
import json
import sys

from . import __version__
from .importer import extract_template
from .store import Store


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog='tp', description='任务模板导入与查询')
    root.add_argument('-V', '--version', action='version', version=__version__)
    commands = root.add_subparsers(dest='command', required=True)
    extract = commands.add_parser('import', help='导入文件或目录')
    extract.add_argument('path')
    extract.add_argument('--tags', default='')
    extract.add_argument('--desc', default='')
    extract.add_argument('--json', action='store_true')
    extract.add_argument('--planner-json', action='store_true')
    extract.add_argument('--compact', action='store_true')
    commands.add_parser('ls', aliases=['list'], help='列出模板')
    for command, aliases in (('rm', ['remove']), ('show', [])):
        child = commands.add_parser(command, aliases=aliases)
        child.add_argument('name')
    return root


def cmd_default(argv: list[str]) -> int:
    args = parser().parse_args(['import', *argv])
    template = extract_template(args.path)
    if args.json or args.planner_json:
        output = template.to_planner_json() if args.planner_json else template.to_dict()
        print(json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2))
        return 0
    store = Store()
    tags = [tag.strip() for tag in args.tags.split(',') if tag.strip()]
    store.add(template.to_dict(), tags=tags, description=args.desc)
    print(f'已存储: {template.template_name}')
    print(store.catalog_text())
    return 0


def cmd_list() -> int:
    print(Store().catalog_text())
    return 0


def cmd_remove(name: str) -> int:
    if not name or not Store().remove(name):
        print(f'模板不存在: {name}', file=sys.stderr)
        return 1
    print(f'已删除: {name}')
    return 0


def cmd_show(name: str) -> int:
    data = Store().get(name) if name else None
    if data is None:
        print(f'模板不存在: {name}', file=sys.stderr)
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    root = parser()
    if not arguments:
        root.print_help()
        return 1
    if arguments[0] == 'help':
        arguments = ['--help']
    commands = {'import', 'ls', 'list', 'rm', 'remove', 'show'}
    if arguments[0] not in commands and not arguments[0].startswith('-'):
        arguments.insert(0, 'import')
    try:
        args = root.parse_args(arguments)
        if args.command == 'import':
            return cmd_default(arguments[1:])
        if args.command in ('ls', 'list'):
            return cmd_list()
        if args.command in ('rm', 'remove'):
            return cmd_remove(args.name)
        return cmd_show(args.name)
    except SystemExit as error:
        return int(error.code)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
