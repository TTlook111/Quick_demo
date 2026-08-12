"""LLM 调用 - 根据用户问题生成 SQL"""

from openai import OpenAI
from app.config import settings
from app.db import get_schema_info

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)

SYSTEM_PROMPT = """你是一个 SQL 生成助手。根据用户的自然语言问题和数据库 Schema，生成安全的 SQL 查询语句。

规则：
1. 只生成 SELECT 语句，禁止任何修改数据的操作
2. 必须包含 LIMIT（默认 LIMIT 100）
3. 不要使用子查询超过 2 层嵌套
4. 只输出纯 SQL 语句，不要任何解释、markdown 格式或代码块标记
5. 如果用户问题无法转换为 SQL，输出：CANNOT_GENERATE

数据库 Schema：
{schema}
"""


def generate_sql(question: str) -> str:
    """根据用户问题生成 SQL"""
    schema = get_schema_info()

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=500,
    )

    sql = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1]  # 去掉第一行
        sql = sql.rsplit("```", 1)[0]  # 去掉最后的 ```
        sql = sql.strip()

    if sql == "CANNOT_GENERATE":
        raise ValueError("无法根据您的问题生成有效的 SQL 查询，请换一种方式描述。")

    return sql
