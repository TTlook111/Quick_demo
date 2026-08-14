"""数据库连接 + Schema 获取 - 支持动态多数据源管理"""

import os
import time
import json
import logging
from sqlalchemy import create_engine, inspect, text
from app.config import settings

logger = logging.getLogger(__name__)

# 确保 data 目录存在
os.makedirs("data", exist_ok=True)

# ========== 数据源存储 ==========
# 持久化保存用户添加的数据源（存文件，重启不丢失）
_DATASOURCES_FILE = "data/datasources.json"
_engines: dict = {}  # datasource_id -> engine
_schema_caches: dict = {}  # datasource_id -> schema_str


def _load_datasources() -> list[dict]:
    """从文件加载已保存的数据源列表"""
    if not os.path.exists(_DATASOURCES_FILE):
        return []
    try:
        with open(_DATASOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_datasources(datasources: list[dict]):
    """保存数据源列表到文件"""
    with open(_DATASOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(datasources, f, ensure_ascii=False, indent=2)


def _build_connection_url(ds: dict) -> str:
    """根据数据源配置构建 SQLAlchemy 连接串"""
    db_type = ds["type"]
    host = ds.get("host", "localhost")
    port = ds.get("port")
    username = ds.get("username", "")
    password = ds.get("password", "")
    database = ds.get("database", "")

    if db_type == "sqlite":
        # SQLite 支持指定文件路径：相对路径放在 data 目录下，或使用绝对路径
        path = ds.get("database", "").strip() or "./data/demo.db"
        if not os.path.isabs(path):
            path = os.path.join("data", path)
        return f"sqlite:///{path.replace(os.sep, '/')}"
    elif db_type == "mysql":
        port = port or 3306
        # mysql+pymysql://user:pass@host:port/db
        auth = f"{username}:{password}@" if username else ""
        return f"mysql+pymysql://{auth}{host}:{port}/{database}?charset=utf8mb4"
    elif db_type == "postgresql":
        port = port or 5432
        # postgresql+psycopg2://user:pass@host:port/db
        auth = f"{username}:{password}@" if username else ""
        return f"postgresql+psycopg2://{auth}{host}:{port}/{database}"
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def get_datasource_list() -> list[dict]:
    """返回所有已配置的数据源（脱敏后供前端显示）"""
    datasources = _load_datasources()
    # 返回时隐藏密码
    result = []
    for ds in datasources:
        safe_ds = {
            "id": ds["id"],
            "name": ds["name"],
            "type": ds["type"],
            "host": ds.get("host", ""),
            "port": ds.get("port", ""),
            "database": ds.get("database", ""),
            "username": ds.get("username", ""),
        }
        result.append(safe_ds)
    return result


def add_datasource(ds_config: dict) -> dict:
    """添加一个新数据源，测试连接后保存"""
    import uuid

    datasources = _load_datasources()

    # 生成 ID
    ds_id = ds_config.get("id") or str(uuid.uuid4())[:8]
    ds_config["id"] = ds_id

    # 先测试连接
    try:
        url = _build_connection_url(ds_config)
        engine = create_engine(url, echo=False, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # 连接成功，缓存引擎
        _engines[ds_id] = engine
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}

    # 检查是否已存在同 ID 的数据源
    datasources = [ds for ds in datasources if ds["id"] != ds_id]
    datasources.append(ds_config)
    _save_datasources(datasources)

    # 预加载 Schema
    try:
        _schema_caches[ds_id] = _build_schema_info(ds_id)
    except Exception:
        pass

    return {"success": True, "id": ds_id, "message": "数据源添加成功"}


def remove_datasource(datasource_id: str) -> dict:
    """删除一个数据源"""
    datasources = _load_datasources()
    datasources = [ds for ds in datasources if ds["id"] != datasource_id]
    _save_datasources(datasources)

    # 清理缓存
    _engines.pop(datasource_id, None)
    _schema_caches.pop(datasource_id, None)

    return {"success": True, "message": "已删除"}


def _get_engine(datasource_id: str = None):
    """获取指定数据源的 SQLAlchemy engine"""
    # 如果没有指定或是 default，使用默认 SQLite
    if not datasource_id or datasource_id == "default":
        if "default" not in _engines:
            _engines["default"] = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
        return _engines["default"]

    if datasource_id in _engines:
        return _engines[datasource_id]

    # 从保存的数据源中查找并创建引擎
    datasources = _load_datasources()
    ds_config = None
    for ds in datasources:
        if ds["id"] == datasource_id:
            ds_config = ds
            break

    if ds_config is None:
        raise ValueError(f"未找到数据源: {datasource_id}")

    url = _build_connection_url(ds_config)
    engine = create_engine(url, echo=False, pool_pre_ping=True)
    _engines[datasource_id] = engine
    logger.info(f"已创建数据源引擎: {datasource_id} ({ds_config['type']})")
    return engine


def get_schema_info(datasource_id: str = None) -> str:
    """获取指定数据源的所有表结构信息，供 LLM 使用"""
    if not datasource_id:
        datasource_id = "default"

    if datasource_id in _schema_caches and _schema_caches[datasource_id] is not None:
        return _schema_caches[datasource_id]

    _schema_caches[datasource_id] = _build_schema_info(datasource_id)
    return _schema_caches[datasource_id]


def refresh_schema_cache(datasource_id: str = None):
    """手动刷新 Schema 缓存"""
    if not datasource_id:
        datasource_id = "default"
    _schema_caches[datasource_id] = _build_schema_info(datasource_id)


def _build_schema_info(datasource_id: str) -> str:
    """实际执行 Schema 反射"""
    engine = _get_engine(datasource_id)
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

    return "\n\n".join(schema_parts) if schema_parts else "(无表)"


def get_db_type(datasource_id: str = None) -> str:
    """获取指定数据源的数据库类型"""
    if not datasource_id or datasource_id == "default":
        url_lower = settings.DATABASE_URL.lower()
        if "mysql" in url_lower:
            return "mysql"
        elif "postgresql" in url_lower or "postgres" in url_lower:
            return "postgresql"
        return "sqlite"

    datasources = _load_datasources()
    for ds in datasources:
        if ds["id"] == datasource_id:
            return ds["type"]

    return "sqlite"


def execute_sql(sql: str, datasource_id: str = None) -> dict:
    """执行 SQL 并返回结果（带超时保护）"""
    engine = _get_engine(datasource_id)
    timeout = settings.QUERY_TIMEOUT

    with engine.connect() as conn:
        _set_query_timeout(conn, timeout, datasource_id)

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


def _set_query_timeout(conn, timeout_seconds: int, datasource_id: str = None):
    """根据数据库类型设置查询超时"""
    db_type = get_db_type(datasource_id)

    if db_type == "sqlite":
        raw_conn = conn.connection.dbapi_connection
        start_time = time.time()

        def progress_handler():
            if time.time() - start_time > timeout_seconds:
                return 1
            return 0

        raw_conn.set_progress_handler(progress_handler, 1000)

    elif db_type == "postgresql":
        conn.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}'"))

    elif db_type == "mysql":
        conn.execute(text(f"SET max_execution_time = {timeout_seconds * 1000}"))


def test_connection(datasource_id: str) -> dict:
    """测试指定数据源的连接"""
    try:
        engine = _get_engine(datasource_id)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


def test_connection_config(ds_config: dict) -> dict:
    """测试连接配置（前端添加数据源时，保存前测试）"""
    try:
        url = _build_connection_url(ds_config)
        engine = create_engine(url, echo=False, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


# 启动时预热默认数据源
try:
    get_schema_info("default")
except Exception as e:
    logger.warning(f"启动时预热默认 Schema 失败: {e}")
