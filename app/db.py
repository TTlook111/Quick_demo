"""数据库连接 + Schema 获取"""

from sqlalchemy import create_engine, inspect, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)


def get_schema_info() -> str:
    """获取数据库所有表的结构信息，供 LLM 使用"""
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
    """执行 SQL 并返回结果"""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchmany(settings.MAX_ROWS)]

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }
