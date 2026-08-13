"""查询接口 - 用户提问 → 生成 SQL → 校验 → 执行 → 返回结果（支持多数据源）"""

import csv
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from app.llm import generate_sql, explain_result, fix_sql
from app.security import validate_sql, SQLSecurityError
from app.db import (
    execute_sql, get_datasource_list, get_schema_info,
    test_connection, refresh_schema_cache,
    add_datasource, remove_datasource,
)
from app.history import save_history, get_history, delete_history, clear_history

router = APIRouter()

logger = logging.getLogger(__name__)


# ========== 请求/响应模型 ==========

class QueryRequest(BaseModel):
    question: str
    conversation: list[dict] | None = None
    datasource_id: str | None = None


class ExecuteSQLRequest(BaseModel):
    sql: str
    question: str | None = None
    datasource_id: str | None = None


class ExplainRequest(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict]


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int
    auto_fixed: bool = False
    datasource_id: str | None = None


class AddDatasourceRequest(BaseModel):
    """前端添加数据源的请求体"""
    name: str               # 显示名称，如 "生产环境MySQL"
    type: str               # sqlite | mysql | postgresql
    host: str = ""          # 主机地址
    port: int | None = None # 端口
    username: str = ""      # 用户名
    password: str = ""      # 密码
    database: str = ""      # 数据库名


# ========== 数据源管理接口 ==========

@router.get("/datasources")
async def list_datasources():
    """获取所有已配置的数据源列表（脱敏）"""
    return get_datasource_list()


@router.post("/datasources")
async def create_datasource(request: AddDatasourceRequest):
    """添加新的数据源连接（前端填写连接信息）"""
    ds_config = {
        "name": request.name,
        "type": request.type,
        "host": request.host,
        "port": request.port,
        "username": request.username,
        "password": request.password,
        "database": request.database,
    }

    result = add_datasource(ds_config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.delete("/datasources/{datasource_id}")
async def delete_datasource(datasource_id: str):
    """删除一个数据源"""
    result = remove_datasource(datasource_id)
    return result


@router.post("/datasources/{datasource_id}/test")
async def test_datasource(datasource_id: str):
    """测试数据源连接"""
    result = test_connection(datasource_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/datasources/{datasource_id}/refresh-schema")
async def refresh_datasource_schema(datasource_id: str):
    """刷新指定数据源的 Schema 缓存"""
    try:
        refresh_schema_cache(datasource_id)
        schema = get_schema_info(datasource_id)
        return {"message": "Schema 已刷新", "schema_preview": schema[:500]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/datasources/{datasource_id}/schema")
async def get_datasource_schema(datasource_id: str):
    """获取指定数据源的 Schema 信息"""
    try:
        schema = get_schema_info(datasource_id)
        return {"datasource_id": datasource_id, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Schema 失败: {str(e)}")


# ========== 查询接口 ==========

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """核心接口：自然语言 → SQL → 执行 → 返回数据"""
    datasource_id = request.datasource_id

    # 1. LLM 生成 SQL
    try:
        sql = generate_sql(request.question, request.conversation, datasource_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL 生成失败: {str(e)}")

    # 2. 安全校验
    try:
        sql = validate_sql(sql)
    except SQLSecurityError as e:
        raise HTTPException(status_code=403, detail=f"SQL 安全校验失败: {str(e)}")

    # 3. 执行 SQL
    try:
        result = execute_sql(sql, datasource_id)
    except Exception as e:
        if isinstance(e, TimeoutError):
            raise HTTPException(status_code=408, detail=str(e))

        # 自动修复
        logger.info(f"SQL 执行失败，尝试自动修复: {e}")
        try:
            fixed_sql = fix_sql(request.question, sql, str(e), datasource_id)
            if fixed_sql:
                fixed_sql = validate_sql(fixed_sql)
                result = execute_sql(fixed_sql, datasource_id)
                sql = fixed_sql
                save_history(request.question, sql, result["row_count"], datasource_id)
                return QueryResponse(
                    question=request.question,
                    generated_sql=sql,
                    columns=result["columns"],
                    rows=result["rows"],
                    row_count=result["row_count"],
                    auto_fixed=True,
                    datasource_id=datasource_id,
                )
        except Exception as fix_error:
            logger.warning(f"自动修复失败: {fix_error}")

        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {str(e)}")

    # 4. 保存历史
    save_history(request.question, sql, result["row_count"], datasource_id)

    # 5. 返回结果
    return QueryResponse(
        question=request.question,
        generated_sql=sql,
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
        datasource_id=datasource_id,
    )


@router.post("/execute", response_model=QueryResponse)
async def execute_edited_sql(request: ExecuteSQLRequest):
    """直接执行用户编辑过的 SQL"""
    datasource_id = request.datasource_id

    try:
        sql = validate_sql(request.sql)
    except SQLSecurityError as e:
        raise HTTPException(status_code=403, detail=f"SQL 安全校验失败: {str(e)}")

    try:
        result = execute_sql(sql, datasource_id)
    except Exception as e:
        if isinstance(e, TimeoutError):
            raise HTTPException(status_code=408, detail=str(e))
        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {str(e)}")

    question = request.question or f"[手动执行] {sql[:50]}"
    save_history(question, sql, result["row_count"], datasource_id)

    return QueryResponse(
        question=question,
        generated_sql=sql,
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
        datasource_id=datasource_id,
    )


@router.post("/explain")
async def explain(request: ExplainRequest):
    """AI 解读查询结果"""
    try:
        explanation = explain_result(
            question=request.question,
            sql=request.sql,
            columns=request.columns,
            rows=request.rows,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 解读失败: {str(e)}")

    return {"explanation": explanation}


@router.post("/export/csv")
async def export_csv(request: QueryRequest):
    """将查询结果导出为 CSV"""
    datasource_id = request.datasource_id
    try:
        sql = generate_sql(request.question, request.conversation, datasource_id)
        sql = validate_sql(sql)
        result = execute_sql(sql, datasource_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=result["columns"])
    writer.writeheader()
    writer.writerows(result["rows"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=query_result.csv"}
    )


@router.get("/history")
async def list_history():
    """获取查询历史"""
    return get_history()


@router.delete("/history/{history_id}")
async def remove_history(history_id: int):
    """删除一条历史"""
    delete_history(history_id)
    return {"message": "已删除"}


@router.delete("/history")
async def clear_all_history():
    """清空历史"""
    clear_history()
    return {"message": "已清空"}
