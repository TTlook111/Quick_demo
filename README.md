# NL2SQL Demo

通过自然语言生成安全 SQL 并执行，返回查询结果。

## 技术栈

- **后端**: FastAPI + SQLAlchemy
- **LLM**: OpenAI API (兼容任何 OpenAI 格式的 API)
- **数据库**: SQLite (demo) / 可切换 MySQL、PostgreSQL
- **安全**: sqlparse 白名单校验 + 只读约束

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 3. 初始化示例数据库
uv run python scripts/init_db.py

# 4. 启动服务
uv run python main.py
```

访问 http://localhost:8000/docs 查看 API 文档。

## API 使用

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "技术部有多少人？"}'
```

## 项目结构

```
├── main.py              # FastAPI 入口
├── app/
│   ├── config.py        # 配置管理
│   ├── db.py            # 数据库连接 + Schema 获取
│   ├── llm.py           # LLM 调用生成 SQL
│   ├── security.py      # SQL 安全校验
│   └── routes/
│       └── query.py     # 查询接口
├── scripts/
│   └── init_db.py       # 初始化示例数据库
└── .env.example         # 环境变量模板
```
