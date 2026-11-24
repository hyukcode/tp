"""Loopback HTTP adapter for the template application service."""
from __future__ import annotations
import argparse
import json
import logging
import mimetypes
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .api import TemplateAPI
from .workbench import Workbench

MAX_REQUEST_BYTES = 1024 * 1024
STATIC_ROOT = Path(__file__).parent / 'static'
logger = logging.getLogger(__name__)


def static_file(url: str, root: Path = STATIC_ROOT) -> Path | None:
    route = unquote(urlsplit(url).path)
    if route != '/' and not route.startswith('/assets/'):
        return None
    root = root.resolve()
    path = (root / ('index.html' if route == '/' else route.lstrip('/'))).resolve()
    return path if root in path.parents and path.is_file() else None


def allowed_request(headers, port: int) -> bool:
    hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
    origins = {f'http://{host}' for host in hosts}
    origin = headers.get('Origin')
    return (headers.get('Host') in hosts
            and (origin is None or origin in origins)
            and headers.get('Content-Type', '').split(';', 1)[0] == 'application/json')


def handler_for(workbench):
    api = TemplateAPI(workbench)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, data, content_type='application/json; charset=utf-8'):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                if urlsplit(self.path).path == '/api/templates':
                    self.reply(200, workbench.list())
                    return
                path = static_file(self.path)
                if path is None:
                    self.reply(404, {'error': 'Not found'})
                    return
                mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                self.reply(200, path.read_bytes(), mime)
            except (OSError, sqlite3.Error):
                logger.exception('读取失败')
                self.reply(500, {'error': '读取失败，请查看服务日志'})

        def read_json(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError('请求大小必须在 1 MB 内')
            return json.loads(self.rfile.read(length))

        def do_POST(self):
            if not allowed_request(self.headers, self.server.server_port):
                self.reply(403, {'error': '仅允许本机同源 JSON 请求'})
                return
            route = urlsplit(self.path).path
            if not route.startswith('/api/'):
                self.reply(404, {'error': 'Not found'})
                return
            try:
                result = api.dispatch(route.removeprefix('/api/'), self.read_json())
                self.reply(200, result)
            except LookupError as error:
                self.reply(404, {'error': str(error)})
            except (ValueError, TypeError) as error:
                self.reply(400, {'error': str(error)})
            except (OSError, sqlite3.Error):
                logger.exception('保存失败')
                self.reply(500, {'error': '保存失败，请查看服务日志'})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description='本地模板工作台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--database', default=str(Path.home() / '.tasker' / 'workbench.sqlite3'))
    args = parser.parse_args(argv)
    with HTTPServer(('127.0.0.1', args.port), handler_for(Workbench(args.database))) as server:
        print(f'Template Studio: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
