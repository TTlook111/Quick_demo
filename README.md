# 🗣️ NL2SQL Demo

> 用自然语言查询数据库 — 输入问题，自动生成安全 SQL 并执行，返回结果 + AI 解读。

## ✨ 功能特性

- 🔤 **自然语言转 SQL** — 输入中文问题，自动生成对应的 SELECT 查询
- 🗄️ **多数据源支持** — 同时连接 SQLite/MySQL/PostgreSQL，前端一键切换
- 🔄 **多轮对话** — 支持追问和修改（如"只看技术部"、"按薪资排序"）
- 🛡️ **SQL 安全校验** — sqlparse 解析 + 黑名单关键词 + 注入防护，只允许 SELECT
- ✏️ **SQL 可编辑** — 生成的 SQL 可直接修改后重新执行
- 🤖 **AI 结果解读** — 查询完成后 LLM 自动分析数据，给出关键洞察
- 📊 **数据可视化** — 表格 + Chart.js 图表（柱状图/折线图/饼图）自由切换
- 📥 **CSV 导出** — 一键下载查询结果
- 📜 **查询历史** — 侧栏记录所有查询，点击可回顾

## 🖼️ 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  [历史记录]  │         NL2SQL Demo                       │
│              │                                           │
│  · 技术部..  │  ┌─────────────────────────────────┐      │
│  · 平均薪..  │  │ 💬 查询所有薪资超过2万的员工     │      │
│  · 订单统..  │  └─────────────────────────────────┘      │
│              │                                           │
│              │  [生成的 SQL（可编辑）]                     │
│              │  SELECT * FROM employees WHERE ...         │
│              │  [▶ 执行]                                  │
│              │                                           │
│              │  🤖 AI 解读: 共有6名员工薪资超过...        │
│              │                                           │
│              │  [表格] [图表]          [导出CSV]          │
│              │  ┌──────┬──────┬───────────────┐          │
│              │  │ 姓名 │ 部门 │ 薪资          │          │
│              │  ├──────┼──────┼───────────────┤          │
│              │  │ 张三 │ 技术 │ 35,000        │          │
│              │  │ ...  │ ...  │ ...           │          │
└─────────────────────────────────────────────────────────┘
```

## 🏗️ 技术架构

```
用户输入 → FastAPI → LLM (生成SQL) → sqlparse (安全校验) → DB Engine (执行) → 返回结果
                                                                         ↓
                                                              LLM (AI 解读)
```

| 层 | 技术选型 | 说明 |
|----|----------|------|
| Web 框架 | FastAPI + Uvicorn | 高性能异步，自带 OpenAPI 文档 |
| 数据库 | SQLite/MySQL/PostgreSQL + SQLAlchemy | 多引擎管理，SQLAlchemy Core 执行原始 SQL |
| LLM | OpenAI SDK | 兼容所有 OpenAI 协议的模型（通义千问、DeepSeek 等） |
| SQL 安全 | sqlparse | 语法解析 + 类型检查 + 黑名单关键词 |
| 前端 | 原生 HTML/CSS/JS | 零框架零构建，多页面（聊天页 + 数据源管理页） |
| 图表 | Chart.js 4.x | 柱状图、折线图、饼图 |
| 包管理 | uv | 极速 Python 包管理器 |

## 📁 项目结构

```
nl2sql-demo/
├── main.py                  # 应用入口，FastAPI 实例配置
├── app/
│   ├── __init__.py
│   ├── config.py            # 环境变量配置（.env 加载）
│   ├── db.py                # 数据库连接、Schema 提取、SQL 执行
│   ├── llm.py               # LLM 调用（SQL 生成 + 结果解读）
│   ├── security.py          # SQL 安全校验（白名单 + 黑名单）
│   ├── history.py           # 查询历史 CRUD（独立 SQLite）
│   └── routes/
│       ├── __init__.py
│       └── query.py         # API 路由（查询/执行/解读/导出/历史）
├── static/
│   ├── index.html           # 聊天查询页（历史侧栏 + 数据源选择 + 结果渲染）
│   ├── datasources.html     # 数据源管理页（添加/测试/删除/切换数据源）
│   ├── css/
│   │   ├── common.css       # 共享样式（变量/暗色主题/Toast）
│   │   ├── main.css         # 聊天页样式
│   │   └── datasources.css  # 数据源管理页样式
│   └── js/
│       ├── common.js        # 共享工具（Toast/主题/工具函数）
│       ├── main.js          # 聊天页逻辑
│       └── datasources.js   # 数据源管理页逻辑
├── scripts/
│   └── init_db.py           # 初始化示例数据库脚本
├── data/
│   ├── demo.db              # 业务数据（员工/部门/订单）
│   └── history.db           # 查询历史记录
├── pyproject.toml           # 项目依赖声明
└── uv.lock                  # 依赖锁定文件
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装 & 运行

```bash
# 1. 克隆项目
git clone git@github.com:TTlook111/Quick_demo.git
cd Quick_demo

# 2. 安装依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 LLM API Key
```

`.env` 文件内容：

```env
# LLM 配置（示例为通义千问 DashScope）
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# 数据库（默认 SQLite，可换 MySQL/PostgreSQL）
DATABASE_URL=sqlite:///./data/demo.db

# 安全限制
MAX_ROWS=100
QUERY_TIMEOUT=10
```

```bash
# 4. 初始化示例数据库
uv run python scripts/init_db.py

# 5. 启动服务
uv run python main.py
```

浏览器打开 **http://localhost:8000** 即可使用。

> 💡 开发模式（热重载）：`uv run uvicorn main:app --reload --port 8000`

## 📡 API 文档

启动后访问 http://localhost:8000/docs 查看 Swagger 文档。

### 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/query` | 自然语言查询（输入问题 → 返回 SQL + 结果） |
| POST | `/api/execute` | 直接执行 SQL（用户编辑后的 SQL） |
| POST | `/api/explain` | AI 解读查询结果 |
| POST | `/api/export/csv` | 导出查询结果为 CSV |
| GET | `/api/history` | 获取查询历史 |
| DELETE | `/api/history/{id}` | 删除单条历史 |
| DELETE | `/api/history` | 清空所有历史 |

### 请求示例

```bash
# 自然语言查询
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "技术部有多少人？"}'

# 带多轮上下文
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "按薪资降序排列",
    "conversation": [
      {"question": "技术部有哪些人", "sql": "SELECT * FROM employees WHERE department = '\''技术部'\'' LIMIT 100"}
    ]
  }'

# 执行编辑后的 SQL
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department LIMIT 100"}'
```

## 🛡️ 安全机制

| 防护层 | 实现 |
|--------|------|
| LLM Prompt 约束 | 指令限制只生成 SELECT，禁止修改操作 |
| sqlparse 解析 | 验证 SQL 语法树类型必须为 SELECT |
| 关键词黑名单 | 拦截 INSERT/UPDATE/DELETE/DROP/ALTER/UNION 等 |
| 注释检测 | 禁止 `--` 和 `/*` 防止注释注入 |
| 单语句限制 | 只允许执行单条 SQL |
| 行数限制 | `fetchmany(MAX_ROWS)` 防止大量数据拖垮内存 |

## 🗄️ 示例数据

初始化脚本创建 3 张表：

**employees** (员工表 - 10 条)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 姓名 |
| department | TEXT | 部门 |
| position | TEXT | 职位 |
| salary | REAL | 薪资 |
| hire_date | TEXT | 入职日期 |

**departments** (部门表 - 4 条)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 部门名称 |
| manager | TEXT | 部门经理 |
| budget | REAL | 预算 |

**orders** (订单表 - 8 条)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| customer_name | TEXT | 客户名 |
| product | TEXT | 产品 |
| amount | REAL | 金额 |
| quantity | INTEGER | 数量 |
| order_date | TEXT | 下单日期 |
| status | TEXT | 状态 |

### 示例问题

- "技术部有多少人？"
- "薪资最高的前5名员工"
- "每个部门的平均薪资是多少？"
- "已完成的订单总金额"
- "哪个客户下单最多？"

## 🔧 自定义配置

### 切换 LLM 模型

修改 `.env` 中的 `OPENAI_BASE_URL` 和 `OPENAI_MODEL` 即可适配不同模型：

```env
# 通义千问
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# OpenAI 官方
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 切换数据库

**方式一：单数据源**

```env
# SQLite（默认）
DATABASE_URL=sqlite:///./data/demo.db

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/mydb

# PostgreSQL
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/mydb
```

**方式二：多数据源（前端可切换）**

在 `.env` 中配置 `DATASOURCES` 环境变量（JSON 数组格式）：

```env
DATASOURCES=[{"id":"local","name":"本地SQLite","url":"sqlite:///./data/demo.db","type":"sqlite"},{"id":"mysql_prod","name":"MySQL生产库","url":"mysql+pymysql://user:pass@host:3306/dbname","type":"mysql"},{"id":"pg_analytics","name":"PG分析库","url":"postgresql+psycopg2://user:pass@host:5432/dbname","type":"postgresql"}]
```

配置后前端会显示数据源下拉选择器，可以在不同数据库之间自由切换查询。

### 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/datasources` | 获取所有可用数据源列表 |
| POST | `/api/datasources/{id}/test` | 测试数据源连接 |
| POST | `/api/datasources/{id}/refresh-schema` | 刷新 Schema 缓存 |
| GET | `/api/datasources/{id}/schema` | 获取数据源表结构 |

> 💡 驱动已内置在依赖中（`pymysql` + `psycopg2-binary`），无需额外安装。

## 📝 License

MIT
