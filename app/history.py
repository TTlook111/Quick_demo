"""查询历史记录管理 - 支持记录数据源"""

import time
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///./data/history.db", echo=False)

# 初始化历史表（增加 datasource_id 字段）
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            generated_sql TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            datasource_id TEXT DEFAULT 'default',
            created_at REAL NOT NULL
        )
    """))
    conn.commit()

    # 兼容旧表：尝试添加 datasource_id 列（如果不存在）
    try:
        conn.execute(text("ALTER TABLE query_history ADD COLUMN datasource_id TEXT DEFAULT 'default'"))
        conn.commit()
    except Exception:
        pass  # 列已存在，忽略


def save_history(question: str, sql: str, row_count: int, datasource_id: str = None):
    """保存一条查询记录"""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO query_history (question, generated_sql, row_count, datasource_id, created_at)
            VALUES (:question, :sql, :row_count, :datasource_id, :created_at)
        """), {
            "question": question,
            "sql": sql,
            "row_count": row_count,
            "datasource_id": datasource_id or "default",
            "created_at": time.time(),
        })
        conn.commit()


def get_history(limit: int = 20) -> list[dict]:
    """获取最近的查询记录"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, question, generated_sql, row_count, datasource_id, created_at
            FROM query_history
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"limit": limit})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


def delete_history(history_id: int):
    """删除一条历史记录"""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM query_history WHERE id = :id"), {"id": history_id})
        conn.commit()


def clear_history():
    """清空所有历史"""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM query_history"))
        conn.commit()
