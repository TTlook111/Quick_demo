"""LLM 调用 - 根据用户问题生成 SQL（支持多轮对话上下文）"""

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
6. 如果用户的问题是对之前查询的追问或修改（如"只看技术部"、"按薪资排序"、"换成降序"），请基于之前的 SQL 进行调整

数据库 Schema：
{schema}
"""


def generate_sql(question: str, conversation_history: list[dict] = None) -> str:
    """根据用户问题生成 SQL，支持多轮对话上下文"""
    schema = get_schema_info()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema)},
    ]

    # 加入历史对话上下文
    if conversation_history:
        for item in conversation_history[-5:]:  # 最多保留最近 5 轮
            messages.append({"role": "user", "content": item["question"]})
            messages.append({"role": "assistant", "content": item["sql"]})

    # 当前问题
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=500,
    )

    sql = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1]
        sql = sql.rsplit("```", 1)[0]
        sql = sql.strip()

    if sql == "CANNOT_GENERATE":
        raise ValueError("无法根据您的问题生成有效的 SQL 查询，请换一种方式描述。")

    return sql
