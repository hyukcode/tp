"""Behavioral regressions for reusable parsing, validation and persistence."""
import ast
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from template.api import TemplateAPI
from template.extractor import extract_tasks
from template.loader import load_directory
from template.parameters import placeholders, render
from template.repository import SQLiteTemplateRepository
from template.store import Store
from template.versioning import project_version
from template.web import static_file, allowed_request
from template.workbench import Workbench, validate, instantiate


def document():
    return {'template_name': '实现 {{feature}}', 'parameters': [{'name': 'feature', 'required': True}],
            'suggested_tasks': [{'title': '实现', 'description': '{{feature}}', 'acceptance': '通过'}]}


class ParserTests(unittest.TestCase):
    def test_markdown_fences_and_multiline_labels(self):
        tasks = extract_tasks('# 模板\n## 目标：开发\n描述：实现\n```md\n## 示例\n工具：literal\n```\n工具：codex\n标准：通过\n下一行\n### 说明\n正文', 'markdown')
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['title'], '开发')
        self.assertEqual(tasks[0]['tool'], 'codex')
        self.assertIn('工具：literal', tasks[0]['description'])
        self.assertIn('下一行', tasks[0]['acceptance'])

    def test_python_ast_ignores_strings_and_comments(self):
        source = '\"\"\"def fake(): pass\"\"\"\n# class Fake:\nclass Real:\n    async def run(self):\n        pass\n'
        titles = [task['title'] for task in extract_tasks(source, 'python')]
        self.assertEqual(titles, ['实现/修改 类 `Real`', '实现/修改 函数 `run`'])

    def test_lexical_languages(self):
        cases = [('javascript', '// function fake() {}\nconst x = "class Fake";\nexport function real() {}\nconst arrow = async (x) => x;\nconst call = (x);', ['real', 'arrow']),
                 ('go', 'func (s *Server) Run() {}', ['Run']),
                 ('rust', "fn first<'a>(x: &'a str) {}\nfn second() {}", ['first', 'second'])]
        for language, source, names in cases:
            with self.subTest(language=language):
                titles = [task['title'] for task in extract_tasks(source, language)]
                self.assertEqual(len(titles), len(names))
                for title, name in zip(titles, names):
                    self.assertIn('`' + name + '`', title)

    def test_configuration_and_paragraphs(self):
        self.assertEqual(extract_tasks('{"port": 80}', 'json')[0]['title'], '处理配置项 `port`')
        self.assertEqual(len(extract_tasks('first paragraph long enough\n \nsecond paragraph long enough', 'text')), 2)

    def test_binary_and_dependency_directories_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'fake.md').write_text('## 不导入')
            (root / 'binary').write_bytes(b'abc\x00def')
            (root / 'real.md').write_text('## 导入')
            self.assertEqual(len(load_directory(root)), 1)


class ParameterTests(unittest.TestCase):
    def test_scanner_and_non_recursive_rendering(self):
        self.assertEqual([token.name for token in placeholders('x {{ name }} {{name}}')], ['name', 'name'])
        self.assertEqual(render('{{name}}', {'name': '{{other}}'}), '{{other}}')
        for value in ('{{bad-name}}', '{{unfinished', '{{}}'):
            with self.assertRaises(ValueError):
                placeholders(value)

    def test_malformed_documents_and_values(self):
        for value in (None, [], {'parameters': [None]}, {'suggested_tasks': [None]}):
            self.assertTrue(validate(value))
        with self.assertRaises(ValueError):
            instantiate(document(), None)
        invalid = document()
        invalid['parameters'] *= 2
        self.assertTrue(validate(invalid))

    def test_source_context_is_not_appended_again(self):
        value = document()
        value['source_file'] = 'requirements.md'
        value['system_prompt_extension'] = '上下文'
        self.assertEqual(instantiate(value, {'feature': '登录'})['system_prompt_extension'], '上下文')


class PersistenceTests(unittest.TestCase):
    def test_concurrent_draft_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Workbench(Path(tmp) / 'studio.db')
            saved = service.save(document())
            def save():
                try:
                    service.save(document(), **saved)
                    return True
                except ValueError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(lambda _: save(), range(2))), [False, True])

    def test_release_definition_preserves_its_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = Workbench(Path(tmp) / 'studio.db')
            saved = service.save(document())
            released = service.publish(**saved)
            draft = document()
            draft['parameters'] = []
            service.save(draft, **saved)
            definition = TemplateAPI(service).dispatch('definition', released)
            self.assertEqual(definition['parameters'][0]['name'], 'feature')
            self.assertEqual(service.release(**released, values={'feature': '登录'})['template_name'], '实现 登录')

    def test_connection_closes_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = SQLiteTemplateRepository(Path(tmp) / 'studio.db')
            with self.assertRaises(ValueError):
                with repository.transaction(write=True) as connection:
                    raise ValueError('rollback')
            import sqlite3
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')

    def test_legacy_store_corruption_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            store.add({**document(), '_meta': {'name': 'injected'}}, name='正式 模板', tags=['dev'])
            Path(tmp, 'broken.json').write_text('[]')
            self.assertEqual(store.list()[0]['name'], '正式 模板')
            self.assertEqual(len(store.search(tags=['dev'], keyword='实现')), 1)
            self.assertIn('正式 模板', store.catalog_text())
            self.assertTrue(store.remove('正式 模板'))


class BoundaryTests(unittest.TestCase):
    def test_api_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            api = TemplateAPI(Workbench(Path(tmp) / 'studio.db'))
            for route, payload in [('save', {'document': None}), ('publish', {'id': [], 'revision': 1}),
                                   ('preview', {'document': document(), 'values': []}), ('import', {'content': None})]:
                with self.subTest(route=route), self.assertRaises(ValueError):
                    api.dispatch(route, payload)
            self.assertTrue(api.dispatch('validate', {'document': None})['errors'])

    def test_http_policy_and_static_paths(self):
        self.assertTrue(allowed_request({'Host': '127.0.0.1:8765', 'Content-Type': 'application/json'}, 8765))
        self.assertFalse(allowed_request({'Host': 'evil.test', 'Content-Type': 'application/json'}, 8765))
        self.assertIsNone(static_file('/assets/../../pyproject.toml'))
        self.assertIsNone(static_file('/assets/%2e%2e/%2e%2e/pyproject.toml'))

    def test_version_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pyproject.toml'
            path.write_text('[project]\nversion = "1.2.3"\n')
            self.assertEqual(project_version(path), '1.2.3')

    def test_no_regex_dependency_in_owned_python(self):
        for root in ('template', 'scripts'):
            for path in Path(root).rglob('*.py'):
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node, ast.Import):
                        self.assertFalse(any(alias.name in ('re', 'regex') for alias in node.names), str(path))
                    elif isinstance(node, ast.ImportFrom):
                        self.assertNotIn(node.module, ('re', 'regex'), str(path))

if __name__ == '__main__':
    unittest.main()
