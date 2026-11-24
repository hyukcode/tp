# Template Studio / tp-wy

面向 taskdispatcher 的本地模板工作台。Vue 3 编辑器 + Python 标准库服务，运行时无需 Node 或第三方 Python 服务框架。

## 启动

源码检出后先运行 `npm ci --prefix frontend` 和 `npm run build --prefix frontend`。已构建的 wheel 自带静态资源，无需 Node。

```sh
python3 -m template.web
# 或安装本包后运行 tp-studio
```

打开 http://127.0.0.1:8765 。默认数据库为 `~/.tasker/workbench.sqlite3`，可通过 `--database <路径>` 修改。服务只监听本机。

新建或导入 Markdown → 编辑任务及验收标准 → 定义参数 → 校验 → 保存草稿 → 发布 → 填写参数并导出固定版本。
参数使用 `{{requirement}}` 形式，第一版支持文本参数、默认值及必填约束。版本发布后不可修改；修改草稿再发布会产生新版本。保存草稿采用修订号检测冲突。

## taskdispatcher 集成

已依据 taskdispatcher 的 `tasker/main.py::_load_template_from_file` 和 `template_compiler.py::nodes_from_template` 对接：导出包含 `template_name`、`source_file`、`system_prompt_extension`、`suggested_tasks`，任务包含 `title/description/acceptance/tool`。

```sh
tasker plan "实现需求" --template /absolute/path/template-ID-v1.json
```

工作台发布只保存模板定义，不启动 agent，也不自动写入旧模板目录。导出会实例化参数；传入 taskdispatcher 的应是导出的 JSON，而非数据库草稿。任务依赖和执行分配仍由 taskdispatcher 处理。

旧 Python SDK 和 `tp <path> --json` 保留，旧模板库 `~/.tasker/templates` 与新工作台数据库独立，不做隐式迁移。`to_planner_json()` 保留兼容用途，工作台导出使用原生模板格式。

```python
from template.workbench import Workbench
studio = Workbench('/path/to/workbench.sqlite3')
template = studio.release('template-id', 1, {'requirement': '登录功能'})
```

## 开发与验证

```sh
npm ci --prefix frontend
npm run build --prefix frontend
python3 -m unittest discover -s tests -v
```

Vue 源码位于 `frontend/src`，Vite 产物在 `template/static`，随 wheel 打包。开发时启动 Python 服务后运行 `npm run dev --prefix frontend`，Vite 将 `/api` 代理到 8765。

HTTP 验证脚本会创建一个测试模板，建议使用临时数据库启动服务后运行 `python3 tests/check_http.py http://127.0.0.1:8765`。

## 本地接口

所有写请求使用同源 `application/json`，请求上限 1 MB，错误返回 HTTP 400 与 `{ "error": "..." }`。

| 路径 | 请求 | 返回 |
| --- | --- | --- |
| GET /api/templates | 无 | 草稿列表及发布版本号 |
| POST /api/save | document, 可选 id/revision | id, revision |
| POST /api/validate | document | errors 列表 |
| POST /api/preview | document, values | 实例化模板 |
| POST /api/publish | id, revision | id, version |
| POST /api/release | id, version, values | 固定版本实例化模板 |
| POST /api/import | content, name | 待编辑 Markdown 草稿 |

这是单机工作台，不提供多用户登录、在线执行、可视化依赖编排或远程部署。


## 模块职责

- `parsers/`：Markdown 行状态解析、Python AST、其他语言词法提取，以及配置与段落解析。
- `parameters.py`：扫描占位符、绑定参数和替换文本，不执行表达式。
- `validation.py`：共享结构校验，区分可保存草稿与可发布模板。
- `workbench.py`：保存、发布、预览和导出用例。
- `repository.py`：可替换的仓库协议与 SQLite 实现；事务结束关闭连接。
- `api.py` / `web.py`：业务动作分发与 HTTP 传输分别实现。
- `store.py` / `json_files.py` / `catalog.py`：兼容旧模板库，分离原子写入与摘要展示。
- `frontend/src/composables/useWorkbench.js`：页面状态与用例；`api.js` 负责请求与下载。

自有 Python 和前端业务源码不使用正则表达式；Vue/Vite 等第三方依赖不在此约束范围内。
非 Python 代码提取是词法启发式，不承诺完整语言语法支持。YAML 与旧版 Python 上的 TOML 仍按文本回退。
非法或未闭合参数占位符现在会阻止发布；CLI 未知选项明确报错。目录导入跳过二进制和常见依赖目录。

新增 `POST /api/definition`，请求 `{id, version}`，返回该发布版本的原始模板定义。页面分别填写草稿和发布版本参数，避免历史版本与当前草稿不匹配。
