"""查询接口 - 用户提问 → 生成 SQL → 校验 → 执行 → 返回结果"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.llm import generate_sql
from app.security import validate_sql, SQLSecurityError
from app.db import execute_sql

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[dict]
    row_count: int


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    核心接口：自然语言 → SQL → 执行 → 返回数据
    """
    # 1. LLM 生成 SQL
    try:
        sql = generate_sql(request.question)
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

    # 4. 返回结果
    return QueryResponse(
        question=request.question,
        generated_sql=sql,
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
    )
