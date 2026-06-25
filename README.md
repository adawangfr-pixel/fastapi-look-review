# fastapi-look-review

一个最小可运行的 **商品 look 审核与导出系统**：商品图片上传 → 规则产出 look 结果 → 人工审核状态机 → Excel 导出，并附带四个原生 HTML 页面。

无需任何前端构建工具，前端页面均为原生 HTML + 原生 `fetch`，引入 [Pico.css](https://picocss.com/) CDN 美化。后端基于 FastAPI + SQLModel + SQLite，可直接用 `uvicorn` 启动。

## 功能概览

- **上传**：上传商品图片与基础信息，自动创建/复用商品、保存图片、运行 look 规则、初始化审核状态为「待审核」。
- **规则引擎**：纯函数实现的可读规则（`app/rules.py`），根据类目、图片数量、名称关键词产出 look 结果与置信度，便于将来替换为配置化规则表。
- **人工审核状态机**：`待审核 → 通过` / `待审核 → 驳回` / `驳回 → 待审核（重新提交）`，非法流转返回 400。
- **改标签**：支持覆盖式更新商品标签。
- **Excel 导出**：用 Pandas + openpyxl 将商品、审核状态、look 结果汇总导出为 `report.xlsx`。

## 目录结构

```
fastapi-look-review/
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 应用入口（建表、注册路由、挂载静态目录）
│   ├── database.py        # SQLite 引擎与会话依赖
│   ├── models.py          # 6 张表 + 审核状态枚举 + 状态机
│   ├── rules.py           # look 规则引擎
│   ├── routers/
│   │   ├── upload.py      # POST /upload
│   │   ├── products.py    # GET  /products
│   │   ├── review.py      # POST/PATCH /review/{sku}、PUT /review/{sku}/tags
│   │   └── export.py      # GET  /export
│   └── static/
│       ├── upload.html
│       ├── products.html
│       ├── review.html
│       └── report.html
├── database.db            # 运行时自动创建（已被 .gitignore 忽略）
└── uploads/               # 运行时自动创建的图片存储目录（已被忽略）
```

## 快速开始

### 1. 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后会自动创建 SQLite 数据库文件 `database.db` 与上传目录 `uploads/`。

## 访问页面

服务默认运行在 `http://localhost:8000`：

- 上传页面：<http://localhost:8000/static/upload.html>
- 商品列表：<http://localhost:8000/static/products.html>
- 审核页面：<http://localhost:8000/static/review.html>
- 导出页面：<http://localhost:8000/static/report.html>
- 自动 API 文档（Swagger UI）：<http://localhost:8000/docs>

根路径 `/` 会自动重定向到上传页面。

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/upload` | 表单上传图片与商品信息，触发 look 规则并初始化审核状态 |
| GET | `/products?offset=&limit=` | 分页返回商品及图片、标签、最新 look 结果、审核状态 |
| POST / PATCH | `/review/{sku}` | 审核动作 `action`=`approve`/`reject`/`resubmit`，含 `reviewer`、`note` |
| PUT | `/review/{sku}/tags` | 覆盖式更新商品标签 |
| GET | `/export` | 导出汇总 Excel（`report.xlsx`） |

## 图片存储与导出说明

- **图片存储**：上传的图片保存在项目根目录的 `uploads/` 下，数据库中只保存相对路径。应用通过 `/uploads` 挂载该目录，前端用 `/<相对路径>` 直接显示缩略图。
- **导出**：`GET /export` 在内存中用 openpyxl 生成 Excel，并以附件形式（`Content-Disposition: attachment; filename=report.xlsx`）返回，浏览器会直接下载。

## 完整流程验证

1. 打开上传页面，填写 SKU、名称等并选择图片，点击「上传」。
2. 打开商品列表页面，确认能看到刚上传的商品、缩略图、look 结果与「待审核」状态。
3. 打开审核页面，点击「通过」或「驳回」，状态会按状态机更新；可尝试「改标签」。
4. 打开导出页面，点击「导出 Excel」，下载 `report.xlsx` 查看汇总结果。
