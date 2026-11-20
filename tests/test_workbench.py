import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from template import extract_template
from template.cli import main
from template.extractor import extract_tasks
from template.workbench import Workbench, instantiate, validate


def sample():
    return dict(template_name='实现 {{feature}}', system_prompt_extension='', parameters=[dict(name='feature',required=True,default='')], suggested_tasks=[dict(title='实现',description='完成 {{feature}}',acceptance='测试通过',tool='codex')])


class WorkbenchTests(unittest.TestCase):
    def test_markdown_subheadings_do_not_duplicate(self):
        tasks=extract_tasks('# 模板\n## 开发\n描述\n### 细节\n补充\n## 验收\n完成标准：通过', 'markdown')
        self.assertEqual(len(tasks),2)
        self.assertIn('细节',tasks[0]['description'])
        self.assertIsNot(tasks[0],tasks[1])

    def test_directory_keeps_code_and_markdown_and_cli_matches_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'README.md').write_text('# 流程\n## 验收\n检查结果')
            Path(tmp,'app.py').write_text('def run():\n    pass\n')
            expected=extract_template(tmp).to_dict()
            self.assertEqual(len(expected['suggested_tasks']),2)
            out=io.StringIO()
            with contextlib.redirect_stdout(out): main([tmp,'--json'])
            self.assertEqual(json.loads(out.getvalue()),expected)

    def test_parameters_and_validation(self):
        self.assertIn('请填写参数',self.error(lambda:instantiate(sample(),{})))
        self.assertEqual(instantiate(sample(),{'feature':'登录'})['suggested_tasks'][0]['description'],'完成 登录')
        doc=sample();doc['parameters']=[]
        self.assertTrue(validate(doc))

    def error(self, fn):
        with self.assertRaises(ValueError) as caught: fn()
        return str(caught.exception)

    def test_releases_are_immutable_and_drafts_detect_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Workbench(Path(tmp,'studio.db'));doc=sample();saved=store.save(doc)
            release=store.publish(**saved)
            doc['suggested_tasks'][0]['title']='修改后'
            store.save(doc,**saved)
            self.error(lambda:store.save(doc,**saved))
            self.error(lambda:store.publish(**saved))
            self.assertEqual(store.release(**release,values={'feature':'登录'})['suggested_tasks'][0]['title'],'实现')
            self.assertEqual(len(store.list()),1)

    def test_invalid_draft_cannot_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Workbench(Path(tmp,'studio.db'))
            self.error(lambda:store.publish(**store.save({})))

if __name__=='__main__': unittest.main()
