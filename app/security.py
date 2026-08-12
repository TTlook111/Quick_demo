"""SQL 安全校验 - 只允许 SELECT 查询"""

import sqlparse


# 危险关键词黑名单
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
    "UNION",  # 防止 UNION 注入
}


class SQLSecurityError(Exception):
    """SQL 安全校验失败"""
    pass


def validate_sql(sql: str) -> str:
    """
    校验 SQL 安全性，返回清理后的 SQL。
    不安全则抛出 SQLSecurityError。
    """
    # 1. 基本清理
    sql = sql.strip().rstrip(";")

    if not sql:
        raise SQLSecurityError("SQL 语句为空")

    # 2. 解析 SQL
    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        raise SQLSecurityError("只允许执行单条 SQL 语句")

    statement = parsed[0]

    # 3. 必须是 SELECT 语句
    if statement.get_type() != "SELECT":
        raise SQLSecurityError(f"只允许 SELECT 查询，检测到: {statement.get_type()}")

    # 4. 检查危险关键词
    tokens_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # 确保是独立关键词，不是列名的一部分
        if f" {keyword} " in f" {tokens_upper} ":
            raise SQLSecurityError(f"包含禁止的关键词: {keyword}")

    # 5. 检查注释（防止注释注入）
    if "--" in sql or "/*" in sql:
        raise SQLSecurityError("SQL 中不允许包含注释")

    return sql
