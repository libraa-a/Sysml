# API 文档

默认服务地址：

```text
http://127.0.0.1:8000
```

交互式 OpenAPI 文档：

```text
http://127.0.0.1:8000/docs
```

## 认证

`POST /api/auth/login`

```json
{
  "username": "engineer",
  "password": "engineer123"
}
```

后续请求可使用：

```http
Authorization: Bearer <token>
```

也保留课堂演示头：

```http
X-User: engineer
X-Role: author
```

`reader` 只能读取，`author/admin` 可以写入。

## MMS 模型管理服务

- `GET /api/health`
- `GET /api/metamodel`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{projectId}`
- `GET /api/projects/{projectId}/branches`
- `POST /api/projects/{projectId}/branches`
- `POST /api/projects/{projectId}/branches/{targetBranch}/merge`
- `GET /api/projects/{projectId}/branches/{branch}/elements`
- `POST /api/projects/{projectId}/branches/{branch}/elements`
- `GET /api/projects/{projectId}/branches/{branch}/elements/{elementId}`
- `PUT /api/projects/{projectId}/branches/{branch}/elements/{elementId}`
- `DELETE /api/projects/{projectId}/branches/{branch}/elements/{elementId}`
- `POST /api/projects/{projectId}/branches/{branch}/commit`
- `GET /api/projects/{projectId}/commits`
- `GET /api/projects/{projectId}/branches/{branch}/diff?from={commit}&to=working`
- `POST /api/projects/{projectId}/branches/{branch}/rollback`
- `GET /api/projects/{projectId}/tags`
- `POST /api/projects/{projectId}/tags`
- `GET /api/projects/{projectId}/audit?limit=80`
- `GET /api/projects/{projectId}/branches/{branch}/validate`

说明书 MMS-API 命名兼容接口：

- `POST /api/mms/models`：创建模型或导入模型内容
- `GET /api/mms/models/{modelName}`：获取单个模型元素；若不是元素 ID，则返回分支模型包
- `PUT /api/mms/models/{modelName}`：更新模型
- `DELETE /api/mms/models/{modelName}`：删除模型元素
- `POST /api/mms/branches`：创建分支
- `GET /api/mms/branches?project=satellite-power`：获取分支列表
- `POST /api/mms/projects`：创建项目

模型导入大小限制默认为 10MB，可通过 `SYSML_MAX_MODEL_BYTES` 配置。

## MDK 同步接口

说明书函数 `parse_sysml(file_path)` 对应：

`POST /api/mdk/parse`

```json
{
  "filename": "Model_001.xmi",
  "format": "xmi",
  "content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

说明书函数 `mdk_push_model(model, username)` 对应：

`POST /api/mdk/push`

```json
{
  "project": "satellite-power",
  "branch": "main",
  "username": "engineer",
  "commit": true,
  "model": {
    "format": "json",
    "elements": []
  }
}
```

说明书函数 `mdk_pull_model(model_name)` 对应：

```http
GET /api/mdk/pull?project=satellite-power&branch=main&format=json
GET /api/mdk/pull?project=satellite-power&branch=main&format=xmi
```

说明书函数 `mdk_generate_doc(model_name, doc_type)` 对应：

`POST /api/mdk/generate`

```json
{
  "project": "satellite-power",
  "branch": "main",
  "doc_type": "pdf"
}
```

JSON 导入：

`POST /api/projects/{projectId}/branches/{branch}/import`

```json
{
  "format": "json",
  "elements": [
    {
      "id": "REQ-004",
      "name": "遥测监控需求",
      "type": "Requirement",
      "attributes": {
        "text": "系统应每 1s 下传电源遥测。",
        "verification": "Inspection"
      }
    }
  ]
}
```

XMI 导入：

```json
{
  "format": "xmi",
  "xmi": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>..."
}
```

导出 JSON：

```http
GET /api/projects/{projectId}/branches/{branch}/export?format=json
```

导出 XMI：

```http
GET /api/projects/{projectId}/branches/{branch}/export?format=xmi
```

## VE 视图接口

- `GET /api/projects/{projectId}/branches/{branch}/diagram?type=requirements`
- `GET /api/projects/{projectId}/branches/{branch}/diagram?type=structure`
- `GET /api/projects/{projectId}/branches/{branch}/diagram?type=behavior`
- `GET /api/projects/{projectId}/branches/{branch}/traceability`

前端部署规则：

- 默认服务 `static/` 中的 Web VE。
- 如需替换为其他前端构建产物，可将 `SYSML_FRONTEND_DIST` 指向包含 `index.html` 的目录。

## DocGen 文档接口

生成文档：

`POST /api/projects/{projectId}/branches/{branch}/documents`

```json
{
  "format": "html",
  "template": "# {{element:REQ-001.name}}\n\n{{table:requirements}}\n\n{{trace:matrix}}\n\n{{validation:issues}}"
}
```

查询文档：

- `GET /api/projects/{projectId}/branches/{branch}/documents`
- `GET /api/projects/{projectId}/branches/{branch}/documents/{documentId}`
- `GET /api/projects/{projectId}/branches/{branch}/documents/{documentId}?format=html`
- `GET /api/projects/{projectId}/branches/{branch}/documents/{documentId}?format=markdown`
- `GET /api/projects/{projectId}/branches/{branch}/documents/{documentId}?format=pdf`

说明书函数 `generate_html(model_name)` 和 `generate_pdf(model_name)` 对应：

- `POST /api/docgen/html`
- `POST /api/docgen/pdf`

生成的 HTML、Markdown 和 PDF 会同步保存到 `outputs/`。可通过环境变量 `SYSML_OUTPUT_DIR` 修改输出位置。

PDF 输出支持两种方式：

- 若运行环境安装了 `wkhtmltopdf`，系统会优先调用它渲染 PDF。
- 若未安装，则自动退回内置 PDF fallback，因此 Docker 和 CI 不依赖额外系统包也可以生成 PDF。

## 文件管理接口

- `GET /api/files`
- `GET /api/files/{filename}`
- `DELETE /api/files/{filename}`

## 运维接口

- `GET /api/ready`
- `GET /api/metrics`

`/api/metrics` 使用 Prometheus 文本格式，Docker 健康检查使用 `/api/ready`。
