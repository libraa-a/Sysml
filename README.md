# 基于 SysML 模型的文档自动生成系统

本项目是一个课程设计级 MBSE 原型，用于演示如何以 SysML 风格模型作为单一可信源，自动生成一致、可追溯的工程文档。系统围绕 MMS、VE、MDK、DocGen 四个组件组织，实现“模型一次编辑，文档处处复用”的闭环。

## 核心功能

- `MMS` 模型管理：项目、分支、元素 CRUD、提交快照、标签、差异比较、回滚、合并、审计日志。
- `VE` 视图编辑器：浏览器内查看和编辑 SysML 元素，展示需求图、结构图、行为图和追踪矩阵。
- `MDK` 工具集成：提供可复用 Python 客户端、命令行入口、Cameo XMI、Jupyter Notebook 和 MATLAB 分析脚本适配器。
- `DocGen` 文档生成：按模板生成 Markdown、HTML、PDF，并写入模型指纹、来源分支、来源提交和追踪矩阵。
- 账号隔离：演示账号统一为普通用户；每个用户登录后只看到并操作自己的独立示例项目。

## 快速运行

```powershell
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python server.py --host 127.0.0.1 --port 8000
```

If `frontend/dist` is missing, the service now returns a clear error instead of silently falling back to the legacy `static/` frontend.

## 重构记录

后端分层重构说明见：

- [docs/backend-refactor-notes.md](docs/backend-refactor-notes.md)

打开：

```text
http://127.0.0.1:8000
```

OpenAPI 文档：

```text
http://127.0.0.1:8000/docs
```

演示账号：

| 用户 | 密码 | 角色 |
| --- | --- | --- |
| `teacher` | `teacher123` | 私有示例项目 |
| `engineer` | `engineer123` | 私有示例项目 |
| `reviewer` | `reviewer123` | 私有示例项目 |

说明：系统已取消 `admin` / `author` / `reader` 三种演示角色。所有账号都是普通用户，登录后只看到并操作自己的独立示例数据。

## 典型流程

1. 使用 `engineer / engineer123` 登录 VE。
2. 在“模型仓库”中创建或修改 Requirement、Block、Interface、Port、Constraint、Activity、State、TestCase。
3. 在“图形建模”中查看关系图，或添加 `satisfy`、`verify`、`refine`、`connect` 等关系。
4. 点击“保存快照”，将当前模型提交到 MMS。
5. 在“追踪矩阵”和“SysML 语义校验”中检查需求闭环。
6. 在”文档生成”中编辑 DocGen 模板并生成 HTML、Markdown、PDF、Word (DOCX)。
7. 使用导出或 `tools/mdk_sync.py` 与外部工具交换 JSON/XMI 模型。

## MDK 命令行示例

```powershell
python tools/mdk_sync.py parse --file data/import_example.json --tool json
python tools/mdk_sync.py push --file data/import_example.json --tool json --commit --validate
python tools/mdk_sync.py push --file mdk/jupyter/example_analysis.ipynb --tool jupyter --commit --validate
python tools/mdk_sync.py push --file mdk/matlab/example_analysis.m --tool matlab --commit --validate
python tools/mdk_sync.py pull --format json --out data/exported_model.json
python tools/mdk_sync.py pull --format xmi --out data/exported_model.xmi
python tools/mdk_sync.py generate --format pdf --out data/generated_document.pdf
python tools/mdk_sync.py generate --format docx --out data/generated_document.docx
```

更多外部工具集成方式见 [docs/mdk.md](docs/mdk.md)。

## DocGen 模板标记

| 标记 | 作用 |
| --- | --- |
| `{{element:REQ-001.name}}` | 引用指定模型元素字段 |
| `{{element:REQ-001.attributes.text}}` | 引用元素扩展属性 |
| `{{model:summary}}` | 生成模型统计摘要 |
| `{{table:requirements}}` | 生成需求表 |
| `{{table:blocks}}` | 生成结构块表 |
| `{{table:interfaces}}` | 生成接口与端口表 |
| `{{table:constraints}}` | 生成约束表 |
| `{{table:tests}}` | 生成验证表 |
| `{{trace:matrix}}` | 生成需求追踪矩阵 |
| `{{validation:issues}}` | 生成语义校验结果 |

## 目录说明

```text
server.py                  FastAPI 启动入口
sysml_docgen/app.py        REST API：MMS / VE / MDK / DocGen
sysml_docgen/store.py      SQLite 模型仓库、版本和审计
sysml_docgen/metamodel.py  SysML 元模型、校验和图数据
sysml_docgen/docgen.py     模板渲染、追踪矩阵和文档输出（基于 Pandoc）
sysml_docgen/mdk.py        MDK 客户端和工具适配器
sysml_docgen/xmi.py        JSON/XMI 交换
static/                    Web VE
tools/mdk_sync.py          MDK 风格同步客户端
mdk/jupyter/               Jupyter 集成 helper 和示例
mdk/matlab/                MATLAB 集成函数和示例
data/sample_project.json   卫星电源系统示例模型
outputs/                   运行时生成的文档输出
tests/                     单元测试与接口测试
```

## 测试

```powershell
python -B -m unittest discover -s tests
```

## Docker

```powershell
docker compose up --build
```

Docker Compose 使用 MongoDB 存储；本地直接运行默认使用 SQLite。可通过以下环境变量调整：

```text
SYSML_STORAGE=sqlite|mongodb
SYSML_OUTPUT_DIR=outputs
SYSML_FRONTEND_DIST=frontend/dist
SYSML_ALLOW_STATIC_FRONTEND=false
SYSML_MAX_MODEL_BYTES=10485760
SYSML_PANDOC_PATH=           # 可选，Pandoc 路径
SYSML_PDF_ENGINE=pandoc|wkhtmltopdf|builtin-fallback
SYSML_DOCX_REFERENCE=        # 可选，Word 参考模板 .docx
```

### Windows 下验证 MongoDB 存储

Docker Desktop 本地运行本项目不需要注册或登录 Docker 账号。若 `docker compose up --build`
因为 Docker Hub 网络问题无法拉取 `python` 或 `node` 基础镜像，可以先只启动 MongoDB
容器，再用本地 Python 后端连接 MongoDB 完成数据库验证：

```powershell
cd C:\Users\86189\Desktop\sysml2
docker compose up -d mongo

$env:SYSML_STORAGE="mongodb"
$env:SYSML_MONGO_STRICT="true"
$env:MONGO_URL="mongodb://127.0.0.1:27017"
.\.venv-1\Scripts\python.exe server.py --host 127.0.0.1 --port 8000
```

然后访问：

```text
http://127.0.0.1:8000/api/ready
```

如果返回内容中包含以下字段，说明系统已经成功使用 MongoDB：

```json
{
  "ready": true,
  "storage": "mongodb"
}
```

也可以用命令行直接验证仓储后端：

```powershell
$env:SYSML_STORAGE="mongodb"
$env:SYSML_MONGO_STRICT="true"
$env:MONGO_URL="mongodb://127.0.0.1:27017"
.\.venv-1\Scripts\python.exe -c "from sysml_docgen.repository.factory import create_model_store; print(create_model_store().__class__.__name__)"
```

成功时应输出：

```text
MongoModelStore
```

如果 Docker Desktop 弹出 Ubuntu WSL integration 错误，可在弹窗中选择
`Skip WSL distro integration`，然后进入 Docker Desktop 的
`Settings -> Resources -> WSL Integration` 关闭 `Ubuntu` 集成。本项目只需要
Docker Desktop 自身的 Linux 引擎，不依赖 Ubuntu 发行版集成。

PDF 生成默认支持内置 fallback，不依赖系统安装 `wkhtmltopdf`。如果运行环境中存在 `wkhtmltopdf`，系统会自动优先使用它。

### 提升输出质量（推荐）

安装 [Pandoc](https://pandoc.org/) 可显著提升 HTML/PDF/Word 输出质量（参考 [Quarto](https://quarto.org/) 的技术架构）：

```powershell
# Windows (推荐方式)
winget install pandoc

# 或使用 Chocolatey
choco install pandoc

# 高质量 PDF 引擎（可选，三选一）
pip install weasyprint              # 轻量 HTML/CSS → PDF
winget install MiKTeX.MiKTeX       # LaTeX → PDF（功能最强）
winget install wkhtmltopdf          # WebKit → PDF
```

安装 Pandoc 后，系统将自动启用：
- **HTML**：语法高亮、智能排版、更丰富的 CSS（斑马纹表格、响应式、打印优化）
- **PDF**：多引擎支持（WeasyPrint / LaTeX / wkhtmltopdf）
- **Word (DOCX)**：新增格式，支持参考模板自定义样式（`SYSML_DOCX_REFERENCE`）
## 协作关系与数据库设计

当前这套项目的协作关系不是靠“三个演示角色”，而是靠“用户 - 工作台 - 共享项目成员”三层结构来表达。

- `users`：保存登录账号、密码哈希、显示名、普通用户身份。
- `projects`：保存项目本体，包含 `owner`、`visibility`、`kind`、`members`、`source_project_id`、`published_*`、`copied_*` 等字段。
- `branches` / `elements` / `commits` / `documents`：都挂在项目之下，个人工作台和共享项目都遵循同一套模型结构。

协作规则：

1. 登录后默认只进入自己的空工作台，格式通常是 `workspace-用户名`。
2. 工作台默认是空的，不再自动注入示例元素。
3. 新建项目默认创建为共享项目，可以直接指定协作成员。
4. “发布到共享库”会把个人工作台发布成共享项目。
5. “从共享库复制到个人工作台”会生成一个私有副本。

也就是说，共享关系由项目成员表来决定，不再靠硬编码的示例账号。
