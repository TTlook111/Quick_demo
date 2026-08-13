"""NL2SQL Demo - FastAPI 入口"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes.query import router as query_router

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

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

# 注册 API 路由
app.include_router(query_router, prefix="/api", tags=["查询"])

# 托管静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """返回前端页面"""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, use_colors=False)
