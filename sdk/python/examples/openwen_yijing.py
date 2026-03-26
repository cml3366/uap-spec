"""
examples/openwen_yijing.py
OpenWen 易经解析 Agent — UAP 接入完整示例

展示如何用 @uap_agent + @uap_capability 把业务逻辑接入 UAP 协议
并通过 UAPServer 暴露标准 HTTP 端点

运行方式:
    pip install fastapi uvicorn httpx
    uvicorn examples.openwen_yijing:app --reload --port 8088
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from uap.decorators import uap_agent, uap_capability, get_agent
from uap.capability import AccessTier
from uap.server import UAPServer

try:
    from fastapi import FastAPI
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Agent 声明（用装饰器）
# ─────────────────────────────────────────────────────────────

@uap_agent(
    did="did:uap:openwen:yijing-agent",
    name="易经解析 Agent",
    version="1.2.0",
    endpoint="http://localhost:8088",
    description="基于完整周易典籍的六十四卦深度解读，支持象辞爻辞、时位正应、卦变互卦分析",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["古典哲学", "易学", "决策支持", "中华文化"],
)
class YijingAgent:
    """
    易经解析 Agent
    OpenWen 的第一个 UAP 接入 Agent
    """

    # ── 开放层能力（无需鉴权）──────────────────────────────

    @uap_capability(
        capability_id="yijing.search",
        name="易经典籍检索",
        description="全文检索周易及历代注疏，返回相关条目及出处",
        access_tier=AccessTier.OPEN,
        rate_limit_rpm=60,
        avg_latency_ms=500,
    )
    async def search(self, query: str, limit: int = 5) -> dict:
        """开放层：典籍关键词检索"""
        # TODO: 接入真实的 CorpusSearchTool + ChromaDB
        # 当前返回示例数据，展示接口契约
        mock_results = [
            {
                "text": f"《周易·乾卦》：天行健，君子以自强不息。（匹配：{query}）",
                "source": "周易·乾卦·象辞",
                "relevance": 0.92,
            },
            {
                "text": "《周易·坤卦》：地势坤，君子以厚德载物。",
                "source": "周易·坤卦·象辞",
                "relevance": 0.85,
            },
        ]
        return {
            "query": query,
            "results": mock_results[:limit],
            "total": len(mock_results),
            "note": "TODO: 接入真实向量检索",
        }

    # ── 鉴权层能力（需要 CapabilityToken）────────────────────

    @uap_capability(
        capability_id="yijing.interpret",
        name="卦象解读",
        description="输入卦名，返回深度义理解读，含象辞、彖辞、历代注疏精华",
        access_tier=AccessTier.AUTHENTICATED,
        rate_limit_rpm=20,
        avg_latency_ms=2000,
    )
    async def interpret(
        self,
        hexagram: str,
        question: str = "",
        context: str = "",
    ) -> dict:
        """
        核心能力：卦象解读
        真实版本接入 LLM + RAG 检索
        """
        # TODO: 接入 LiteLLM → Qwen/Claude + CorpusSearchTool
        # 当前示例展示完整的输出结构

        interpretations = {
            "乾卦": {
                "name": "乾卦 ䷀",
                "attribute": "健",
                "image": "天行健，君子以自强不息",
                "judgment": "乾：元，亨，利，贞",
                "modern_reading": (
                    "乾卦象征纯阳之气，代表创造、进取与领导力。"
                    "六爻皆阳，刚健不息，象天道运行之永恒。"
                    f"就「{question}」而言：此时宜积极进取，把握天时，"
                    "但须警惕亢龙之悔——过犹不及，知进退存亡。"
                ),
                "citations": [
                    "《彖传》：大哉乾元，万物资始，乃统天。",
                    "《象传》：天行健，君子以自强不息。",
                    "王弼注：健而无休者，天之德也。",
                ],
                "ai_guidance": (
                    "东方智慧提示：乾卦「用九」曰「见群龙无首，吉」，"
                    "领导者不执于一，顺势而为，方是大道。"
                ),
            }
        }

        result = interpretations.get(
            hexagram,
            {
                "name": hexagram,
                "modern_reading": f"正在检索「{hexagram}」的典籍资料……",
                "note": "TODO: 接入完整六十四卦数据集",
            },
        )

        if context:
            result["context_note"] = f"结合背景「{context}」综合分析"

        return {
            "hexagram": hexagram,
            "question": question,
            "interpretation": result,
            "model": "mock-v1 (TODO: qwen-max)",
            "rag_sources": len(result.get("citations", [])),
        }

    @uap_capability(
        capability_id="yijing.hexagram.full",
        name="完整卦象分析",
        description="包含本卦、变卦、互卦的完整分析报告，适合学术研究",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=4500,
        required_agents=["did:uap:openwen:classics-agent"],
    )
    async def hexagram_full(
        self,
        hexagram: str,
        changing_lines: list[int] = None,
        question: str = "",
    ) -> dict:
        """完整卦象分析（含变卦互卦）"""
        # 调用基础解读
        base = await self.interpret(hexagram=hexagram, question=question)

        return {
            "primary_hexagram": hexagram,
            "changing_lines": changing_lines or [],
            "derived_hexagrams": {
                "changed": "TODO: 根据变爻计算变卦",
                "nuclear": "TODO: 计算互卦（第2-4爻、第3-5爻）",
            },
            "base_interpretation": base,
            "full_analysis": "TODO: 接入 classics-agent 进行深度注疏分析",
        }


# ─────────────────────────────────────────────────────────────
# FastAPI 应用（如果 fastapi 已安装）
# ─────────────────────────────────────────────────────────────

if _FASTAPI_AVAILABLE:
    app = FastAPI(
        title="OpenWen · 易经解析 Agent",
        description="UAP 协议接入示例 — 万Agent互联协议参考实现",
        version="1.2.0",
    )

    # 获取注册信息并挂载 UAP 端点
    registration = get_agent("did:uap:openwen:yijing-agent")
    if registration:
        uap_server = UAPServer(app, registration)
        uap_server.mount()

        @app.get("/")
        async def root():
            return {
                "agent": "OpenWen 易经解析 Agent",
                "uap_version": "1.0",
                "well_known": "/.well-known/uap",
                "invoke": "/uap/invoke",
                "docs": "/docs",
            }

else:
    print("⚠️  FastAPI not installed. HTTP server not available.")
    print("   Install with: pip install fastapi uvicorn")


# ─────────────────────────────────────────────────────────────
# 纯 Python 测试（不需要 FastAPI）
# ─────────────────────────────────────────────────────────────

async def demo():
    """展示 UAP 消息构建的完整流程"""
    from uap import AgentDID, UAPMessage, Intent, Depth

    agent = YijingAgent()

    # 1. 查看 Agent 能力清单
    manifest = agent.get_manifest()
    print("=== 能力清单 ===")
    print(manifest.to_json())

    # 2. 直接调用能力（不走 HTTP）
    print("\n=== 直接调用 yijing.search ===")
    result = await agent.search(query="天行健", limit=2)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n=== 直接调用 yijing.interpret ===")
    result = await agent.interpret(
        hexagram="乾卦",
        question="创业第三年，是扩张还是守成？",
        context="科技创业公司，团队20人",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 3. 构建完整 UAP 消息信封（展示协议格式）
    print("\n=== UAP 消息信封 ===")
    msg = UAPMessage.create(
        from_did=AgentDID.parse("did:uap:personal:user-maolin"),
        to_did=AgentDID.parse("did:uap:openwen:yijing-agent"),
        intent=Intent.invoke(
            capability="yijing.interpret",
            input={"hexagram": "乾卦", "question": "创业方向"},
            depth=Depth.SCHOLARLY,
            extensions={"openwen:tradition": "王弼注本"},
        ),
        capability_token="eyJmYWtlX3Rva2VuIjp0cnVlfQ==",
    )
    print(msg.to_json())


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
