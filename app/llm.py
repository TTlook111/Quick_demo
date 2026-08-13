"""LLM 调用 - 根据用户问题生成 SQL（支持多轮对话上下文 + 多数据源）"""

import time
import logging
from openai import OpenAI
from app.config import settings
from app.db import get_schema_info, get_db_type

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 SQL 生成助手。根据用户的自然语言问题和数据库 Schema，生成安全的 SQL 查询语句。

数据库类型：{db_type}

规则：
1. 只生成 SELECT 语句，禁止任何修改数据的操作
2. 必须包含 LIMIT（默认 LIMIT 100）
3. 不要使用子查询超过 2 层嵌套
4. 只输出纯 SQL 语句，不要任何解释、markdown 格式或代码块标记
5. 如果用户问题无法转换为 SQL，输出：CANNOT_GENERATE
6. 如果用户的问题是对之前查询的追问或修改（如"只看技术部"、"按薪资排序"、"换成降序"），请基于之前的 SQL 进行调整
7. 注意根据数据库类型使用正确的 SQL 方言（如 MySQL 用 LIMIT，PostgreSQL 支持 ILIKE 等）

数据库 Schema：
{schema}
"""


def generate_sql(question: str, conversation_history: list[dict] = None, datasource_id: str = None) -> str:
    """根据用户问题生成 SQL，支持多轮对话上下文"""
    # 问题长度校验
    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise ValueError(f"问题过长（最大 {settings.MAX_QUESTION_LENGTH} 字），请精简描述。")

    schema = get_schema_info(datasource_id)
    db_type = get_db_type(datasource_id)

    # 数据库类型的友好名称
    db_type_display = {
        "sqlite": "SQLite",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
    }.get(db_type, db_type)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema, db_type=db_type_display)},
    ]

    # 加入历史对话上下文
    if conversation_history:
        for item in conversation_history[-5:]:  # 最多保留最近 5 轮
            messages.append({"role": "user", "content": item["question"]})
            messages.append({"role": "assistant", "content": item["sql"]})

    # 当前问题
    messages.append({"role": "user", "content": question})

    # 带重试的 LLM 调用
    last_error = None
    for attempt in range(1 + settings.LLM_MAX_RETRIES):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=500,
            )
            elapsed = time.time() - start
            logger.info(f"LLM generate_sql 耗时: {elapsed:.2f}s (attempt {attempt + 1})")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"LLM 调用失败 (attempt {attempt + 1}): {e}")
            if attempt < settings.LLM_MAX_RETRIES:
                time.sleep(1)  # 等 1 秒后重试
    else:
        raise RuntimeError(f"LLM 服务暂时不可用，请稍后重试。({last_error})")

    sql = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1]
        sql = sql.rsplit("```", 1)[0]
        sql = sql.strip()

    if sql == "CANNOT_GENERATE":
        raise ValueError("无法根据您的问题生成有效的 SQL 查询，请换一种方式描述。")

    return sql


FIX_SQL_PROMPT = """之前根据用户问题生成的 SQL 执行失败了，请修复。

数据库类型：{db_type}
用户问题：{question}
原始 SQL：{original_sql}
错误信息：{error}

数据库 Schema：
{schema}

规则：
1. 只生成 SELECT 语句，必须包含 LIMIT
2. 只输出纯 SQL 语句，不要任何解释或 markdown 标记
3. 注意根据数据库类型使用正确的 SQL 方言
4. 如果确实无法修复，输出：CANNOT_FIX
"""


def fix_sql(question: str, original_sql: str, error: str, datasource_id: str = None) -> str:
    """当 SQL 执行失败时，让 LLM 根据错误信息修复 SQL"""
    schema = get_schema_info(datasource_id)
    db_type = get_db_type(datasource_id)

    db_type_display = {
        "sqlite": "SQLite",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
    }.get(db_type, db_type)

    last_error = None
    for attempt in range(1 + settings.LLM_MAX_RETRIES):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": FIX_SQL_PROMPT.format(
                        question=question,
                        original_sql=original_sql,
                        error=error,
                        schema=schema,
                        db_type=db_type_display,
                    )}
                ],
                temperature=0,
                max_tokens=500,
            )
            elapsed = time.time() - start
            logger.info(f"LLM fix_sql 耗时: {elapsed:.2f}s (attempt {attempt + 1})")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"LLM fix_sql 调用失败 (attempt {attempt + 1}): {e}")
            if attempt < settings.LLM_MAX_RETRIES:
                time.sleep(1)
    else:
        raise RuntimeError(f"LLM 服务暂时不可用。({last_error})")

    sql = response.choices[0].message.content.strip()

    # 清理 markdown
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1]
        sql = sql.rsplit("```", 1)[0]
        sql = sql.strip()

    if sql == "CANNOT_FIX":
        return None

    return sql


EXPLAIN_PROMPT = """你是一个数据分析助手。根据以下信息，用简洁的中文给出分析解读：

用户问题：{question}
执行的 SQL：{sql}
查询结果（JSON）：{result_preview}

要求：
1. 先用一句话解释 SQL 做了什么
2. 再对查询结果给出关键洞察（如趋势、极值、对比等）
3. 如果数据量少可以做总结，数据量大则挑重点说
4. 输出控制在 3-5 句话内，不要输出 markdown 格式标记
"""


def explain_result(question: str, sql: str, columns: list[str], rows: list[dict]) -> str:
    """让 LLM 对查询结果进行自然语言解读"""
    import json

    # 限制传给 LLM 的结果量（避免 token 超限）
    preview_rows = rows[:20]
    result_preview = json.dumps(
        {"columns": columns, "rows": preview_rows, "total_rows": len(rows)},
        ensure_ascii=False,
        default=str,
    )

    last_error = None
    for attempt in range(1 + settings.LLM_MAX_RETRIES):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": EXPLAIN_PROMPT.format(
                        question=question,
                        sql=sql,
                        result_preview=result_preview,
                    )}
                ],
                temperature=0.3,
                max_tokens=400,
            )
            elapsed = time.time() - start
            logger.info(f"LLM explain_result 耗时: {elapsed:.2f}s (attempt {attempt + 1})")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"LLM explain 调用失败 (attempt {attempt + 1}): {e}")
            if attempt < settings.LLM_MAX_RETRIES:
                time.sleep(1)
    else:
        raise RuntimeError(f"AI 解读服务暂时不可用。({last_error})")

    return response.choices[0].message.content.strip()
