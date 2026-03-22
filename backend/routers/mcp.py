"""MCP 相關 API routes。"""

from pydantic import BaseModel
from fastapi import APIRouter

from services.mcp import mcp_registry

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


class McpTestRequest(BaseModel):
    """MCP 連線測試請求模型。"""

    selected_mcps: list[str]
    mcp_tokens: dict[str, str] = {}


@router.get("/list")
def mcp_list():
    """回傳所有可用 MCP 及 preset 定義。"""
    return {
        "mcps": mcp_registry.get_all(),
        "presets": mcp_registry.get_presets(),
    }


@router.post("/test")
async def mcp_test(req: McpTestRequest):
    """測試指定 MCP 的連線狀態。"""
    results = await mcp_registry.test_connection(req.selected_mcps, req.mcp_tokens)
    return {"results": results}
