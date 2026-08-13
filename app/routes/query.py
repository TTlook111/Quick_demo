"""查询接口 - 用户提问 → 生成 SQL → 校验 → 执行 → 返回结果"""

import csv
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.llm import generate_sql, explain_result
from app.security import validate_sql, SQLSecurityError
from app.db import execute_sql
from app.history import save_history, get_history, delete_history, clear_history

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    # 多轮对话上下文：前端传入之前的问答记录
    conversation: list[dict] | None = None


class ExecuteSQLRequest(BaseModel):
    sql: str
    question: str | None = None


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


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """核心接口：自然语言 → SQL → 执行 → 返回数据"""
    # 1. LLM 生成 SQL（带上下文）
    try:
        sql = generate_sql(request.question, request.conversation)
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
        result = execute_sql(sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {str(e)}")

    # 4. 保存历史
    save_history(request.question, sql, result["row_count"])

    # 5. 返回结果
    return QueryResponse(
        question=request.question,
        generated_sql=sql,
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
    )


@router.post("/execute", response_model=QueryResponse)
async def execute_edited_sql(request: ExecuteSQLRequest):
    """直接执行用户编辑过的 SQL（仍做安全校验）"""
    # 1. 安全校验
    try:
        sql = validate_sql(request.sql)
    except SQLSecurityError as e:
        raise HTTPException(status_code=403, detail=f"SQL 安全校验失败: {str(e)}")

    # 2. 执行 SQL
    try:
        result = execute_sql(sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {str(e)}")

    # 3. 保存历史
    question = request.question or f"[手动执行] {sql[:50]}"
    save_history(question, sql, result["row_count"])

    # 4. 返回结果
    return QueryResponse(
        question=question,
        generated_sql=sql,
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
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
    try:
        sql = generate_sql(request.question, request.conversation)
        sql = validate_sql(sql)
        result = execute_sql(sql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 生成 CSV
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
