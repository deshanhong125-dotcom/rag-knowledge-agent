from fastapi import FastAPI

from api.routers import (
    chat,
    sessions,
    documents,
)

app = FastAPI(
    title="RAG Knowledge Agent API",
    description="企业知识库 Agent 后端接口",
    version="0.1.0",
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(documents.router)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """检查API服务是否正常运行。"""

    return {
        "status": "ok",
        "service": "rag-agent-api",
    }





