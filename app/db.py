"""数据库连接 + Schema 获取"""

import os
import threading
from sqlalchemy import create_engine, inspect, text, event
from app.config import settings

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

# ========== Schema 缓存 ==========
_schema_cache: str | None = None


def get_schema_info() -> str:
    """获取数据库所有表的结构信息，供 LLM 使用"""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    _schema_cache = _build_schema_info()
    return _schema_cache


def refresh_schema_cache():
    """手动刷新 Schema 缓存（数据库结构变更后调用）"""
    global _schema_cache
    _schema_cache = _build_schema_info()


def _build_schema_info() -> str:
    """实际执行 Schema 反射"""
    inspector = inspect(engine)
    schema_parts = []

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        col_defs = []
        for col in columns:
            col_str = f"  {col['name']} {col['type']}"
            if col.get("comment"):
                col_str += f"  -- {col['comment']}"
            col_defs.append(col_str)

        schema_parts.append(
            f"TABLE: {table_name}\n" + "\n".join(col_defs)
        )

    return "\n\n".join(schema_parts)


def execute_sql(sql: str) -> dict:
    """执行 SQL 并返回结果（带超时保护）"""
    import sqlite3

    timeout = settings.QUERY_TIMEOUT

    with engine.connect() as conn:
        # 设置语句级超时
        _set_query_timeout(conn, timeout)

        try:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(settings.MAX_ROWS)]
        except Exception as e:
            err_msg = str(e)
            if "interrupt" in err_msg.lower() or "timeout" in err_msg.lower():
                raise TimeoutError(f"查询超时（超过 {timeout} 秒），请简化查询条件")
            raise

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def _set_query_timeout(conn, timeout_seconds: int):
    """根据数据库类型设置查询超时"""
    url = str(settings.DATABASE_URL).lower()

    if "sqlite" in url:
        # SQLite: 使用 progress_handler 实现超时
        import time
        raw_conn = conn.connection.dbapi_connection
        start_time = time.time()

        def progress_handler():
            if time.time() - start_time > timeout_seconds:
                return 1  # 非零值中断查询
            return 0

        raw_conn.set_progress_handler(progress_handler, 1000)

    elif "postgresql" in url or "postgres" in url:
        conn.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}'"))

    elif "mysql" in url:
        conn.execute(text(f"SET max_execution_time = {timeout_seconds * 1000}"))


# 启动时预热缓存
get_schema_info()
