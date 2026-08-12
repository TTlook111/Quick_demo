"""NL2SQL Demo - FastAPI 入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.query import router as query_router

app = FastAPI(
    title="NL2SQL Demo",
    description="通过自然语言生成安全 SQL 并执行，返回查询结果",
    version="0.1.0",
)

# 跨域配置（开发阶段允许所有）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(query_router, prefix="/api", tags=["查询"])


@app.get("/")
async def root():
    return {"message": "NL2SQL Demo API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
