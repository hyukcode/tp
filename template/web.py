"""Loopback-only authoring server. No arbitrary filesystem access from HTTP."""
from __future__ import annotations
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .extractor import extract_tasks
from .workbench import Workbench, instantiate, validate


def handler_for(workbench):
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
            if self.path == '/api/templates':
                self.reply(200, workbench.list())
            elif self.path == '/' or self.path.startswith('/assets/'):
                import mimetypes
                root = (Path(__file__).parent / 'static').resolve()
                path = (root / ('index.html' if self.path == '/' else self.path.lstrip('/'))).resolve()
                if root not in path.parents or not path.is_file():
                    self.reply(404, {'error': 'Not found'})
                    return
                mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                self.reply(200, path.read_bytes(), mime + '; charset=utf-8')
            else:
                self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            # Require same-origin JSON to prevent cross-site writes to a local service.
            host = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') not in (host, f'localhost:{self.server.server_port}') or self.headers.get('Origin', f'http://{host}') not in (f'http://{host}', f'http://localhost:{self.server.server_port}') or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                self.reply(403, {'error': '仅允许本机同源 JSON 请求'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError('请求大小必须在 1 MB 内')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('请求必须是对象')
                if self.path == '/api/save':
                    result = workbench.save(data['document'], data.get('id', ''), data.get('revision', 0))
                elif self.path == '/api/validate':
                    result = {'errors': validate(data['document'])}
                elif self.path == '/api/preview':
                    result = instantiate(data['document'], data.get('values', {}))
                elif self.path == '/api/publish':
                    result = workbench.publish(data['id'], data['revision'])
                elif self.path == '/api/release':
                    result = workbench.release(data['id'], data['version'], data.get('values', {}))
                elif self.path == '/api/import':
                    result = {'template_name': data.get('name', ''), 'system_prompt_extension': '', 'parameters': [], 'suggested_tasks': extract_tasks(data['content'], 'markdown')}
                else:
                    self.reply(404, {'error': 'Not found'})
                    return
                self.reply(200, result)
            except (ValueError, KeyError, TypeError) as error:
                self.reply(400, {'error': str(error)})
    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description='本地模板工作台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--database', default=str(Path.home() / '.tasker' / 'workbench.sqlite3'))
    args = parser.parse_args(argv)
    server = HTTPServer(('127.0.0.1', args.port), handler_for(Workbench(args.database)))
    print(f'Template Studio: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
