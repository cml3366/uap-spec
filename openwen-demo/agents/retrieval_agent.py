"""
agents/retrieval_agent.py — 检索 Agent
职责：语料检索 · 向量语义搜索 · BM25混合检索 · 引文溯源

UAP 能力：
  - retrieval.search         关键词 + 语义混合检索
  - retrieval.cite_verify    引文真实性校验
  - retrieval.corpus_stats   语料库统计
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from typing import Optional

logger = logging.getLogger("openwen.retrieval")

# ── UAP 装饰器 ──────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../uap-python"))
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier

# ── 核心配置 ────────────────────────────────────────────────
from core.config import config
from core.llm import LLMClient


# ── Mock 语料库（Phase 1 占位，Phase 3 换 ChromaDB）──────────
_MOCK_CORPUS = [
    {"id": "qian-001", "text": "天行健，君子以自强不息", "source": "周易·乾卦·象辞", "dynasty": "先秦"},
    {"id": "qian-002", "text": "大哉乾元，万物资始，乃统天", "source": "周易·彖传·乾", "dynasty": "先秦"},
    {"id": "qian-003", "text": "元亨利贞，乾之四德也", "source": "周易·文言传", "dynasty": "先秦"},
    {"id": "kun-001", "text": "地势坤，君子以厚德载物", "source": "周易·坤卦·象辞", "dynasty": "先秦"},
    {"id": "kun-002", "text": "坤厚载物，德合无疆", "source": "周易·彖传·坤", "dynasty": "先秦"},
    {"id": "lun-001", "text": "仁者爱人，智者知人", "source": "论语·颜渊", "dynasty": "先秦"},
    {"id": "lun-002", "text": "己所不欲，勿施于人", "source": "论语·颜渊", "dynasty": "先秦"},
    {"id": "lun-003", "text": "学而时习之，不亦说乎", "source": "论语·学而", "dynasty": "先秦"},
    {"id": "dao-001", "text": "道可道，非常道；名可名，非常名", "source": "道德经·第一章", "dynasty": "先秦"},
    {"id": "dao-002", "text": "上善若水，水善利万物而不争", "source": "道德经·第八章", "dynasty": "先秦"},
    {"id": "dao-003", "text": "知人者智，自知者明；胜人者有力，自胜者强", "source": "道德经·第三十三章", "dynasty": "先秦"},
    {"id": "meng-001", "text": "得道多助，失道寡助", "source": "孟子·公孙丑下", "dynasty": "先秦"},
    {"id": "meng-002", "text": "天时不如地利，地利不如人和", "source": "孟子·公孙丑下", "dynasty": "先秦"},
    {"id": "xici-001", "text": "一阴一阳之谓道，继之者善也，成之者性也", "source": "周易·系辞上传", "dynasty": "先秦"},
    {"id": "xici-002", "text": "穷则变，变则通，通则久", "source": "周易·系辞下传", "dynasty": "先秦"},
    {"id": "xici-003", "text": "易有太极，是生两仪，两仪生四象，四象生八卦", "source": "周易·系辞上传", "dynasty": "先秦"},
    {"id": "zhong-001", "text": "中也者，天下之大本也；和也者，天下之达道也", "source": "中庸·第一章", "dynasty": "先秦"},
    {"id": "daxue-001", "text": "大学之道，在明明德，在亲民，在止于至善", "source": "大学·第一章", "dynasty": "先秦"},
]


def _simple_search(query: str, corpus: list[dict], top_k: int = 5) -> list[dict]:
    """
    简单关键词匹配检索（Phase 1 占位实现）
    Phase 3 替换为 BM25 + 向量混合检索
    """
    query_terms = set(query.lower().replace(" ", ""))
    scored = []
    for doc in corpus:
        text = doc["text"] + doc["source"]
        # 字符级匹配打分
        matches = sum(1 for ch in query_terms if ch in text)
        score = matches / max(len(query_terms), 1)
        # 额外加权：完整短语匹配
        if query[:4] in text:
            score += 0.3
        if score > 0:
            scored.append({**doc, "score": round(min(score, 1.0), 3)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ── UAP Agent 声明 ───────────────────────────────────────────

@uap_agent(
    did=config.agent_did("retrieval"),
    name="检索 Agent",
    version="1.0.0",
    endpoint=config.agent_endpoint("retrieval"),
    description="语料检索·向量语义搜索·BM25混合检索·引文溯源核实",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["检索", "RAG", "典籍", "引文"],
)
class RetrievalAgent:
    """
    OpenWen 检索 Agent
    负责从知识库中检索相关典籍文本，为义理分析和写作提供语料支撑
    """

    def __init__(self):
        self.llm = LLMClient()
        self.corpus = _MOCK_CORPUS
        logger.info(f"RetrievalAgent 初始化，语料库 {len(self.corpus)} 条")

    @uap_capability(
        capability_id="retrieval.search",
        name="语料检索",
        description="输入查询词，返回相关典籍文本及出处（混合检索）",
        access_tier=AccessTier.AUTHENTICATED,
        rate_limit_rpm=60,
        avg_latency_ms=800,
    )
    async def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None,
        dynasty_filter: Optional[str] = None,
    ) -> dict:
        """
        语料混合检索

        Args:
            query: 检索查询词（支持古文关键词和现代语义）
            top_k: 返回条目数量
            source_filter: 限定典籍来源，如"周易"
            dynasty_filter: 限定朝代，如"先秦"
        """
        logger.info(f"[检索] query={query!r} top_k={top_k}")

        # 过滤语料
        corpus = self.corpus
        if source_filter:
            corpus = [d for d in corpus if source_filter in d["source"]]
        if dynasty_filter:
            corpus = [d for d in corpus if d.get("dynasty") == dynasty_filter]

        # 检索
        results = _simple_search(query, corpus, top_k)

        # TODO Phase 3: 替换为真实向量检索
        # from tools.vector_search import hybrid_search
        # results = await hybrid_search(query, top_k, filters=...)

        logger.info(f"[检索] 返回 {len(results)} 条结果")
        return {
            "query": query,
            "results": results,
            "total_found": len(results),
            "corpus_size": len(self.corpus),
            "search_method": "keyword_match_v1",  # Phase 3 改为 hybrid_bm25_vector
        }

    @uap_capability(
        capability_id="retrieval.cite_verify",
        name="引文校验",
        description="验证引文是否真实存在于典籍中，防止 LLM 幻觉伪造引文",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=500,
    )
    async def cite_verify(
        self,
        citation: str,
        source: Optional[str] = None,
    ) -> dict:
        """
        引文真实性校验
        检查给定引文是否能在语料库中找到匹配

        Args:
            citation: 待校验的引文文本
            source: 声称的出处（可选）
        """
        logger.info(f"[引文校验] citation={citation!r}")

        # 在语料库中查找精确或高度相似的匹配
        results = _simple_search(citation, self.corpus, top_k=3)

        if results and results[0]["score"] > 0.7:
            best = results[0]
            return {
                "verified": True,
                "citation": citation,
                "matched_text": best["text"],
                "source": best["source"],
                "claimed_source": source,
                "source_match": source in best["source"] if source else None,
                "confidence": best["score"],
            }
        else:
            return {
                "verified": False,
                "citation": citation,
                "claimed_source": source,
                "confidence": results[0]["score"] if results else 0.0,
                "warning": "⚠️ 未在语料库中找到该引文，请核实来源",
                "suggestion": "建议查阅原典或调整引文措辞",
            }

    @uap_capability(
        capability_id="retrieval.corpus_stats",
        name="语料库统计",
        description="返回当前知识库的统计信息",
        access_tier=AccessTier.OPEN,
        avg_latency_ms=100,
    )
    async def corpus_stats(self) -> dict:
        """返回语料库统计信息"""
        from collections import Counter
        sources = Counter(d["source"].split("·")[0] for d in self.corpus)
        return {
            "total_entries": len(self.corpus),
            "source_distribution": dict(sources.most_common(10)),
            "status": "mock_v1",
            "note": "Phase 3 将升级为 ChromaDB + Milvus 向量库",
        }


# ── FastAPI 应用 ─────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI(title="OpenWen · 检索 Agent", version="1.0.0")
    reg = get_agent(config.agent_did("retrieval"))
    if reg:
        uap = UAPServer(app, reg)
        uap.mount()

        @app.get("/")
        async def root():
            return {"agent": "检索 Agent", "did": config.agent_did("retrieval")}

except ImportError:
    pass


if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = RetrievalAgent()
        print("=== 检索：乾卦 ===")
        r = await agent.search(query="乾卦 天行健", top_k=3)
        print(json.dumps(r, ensure_ascii=False, indent=2))

        print("\n=== 引文校验 ===")
        r = await agent.cite_verify("天行健，君子以自强不息", source="周易·乾卦")
        print(json.dumps(r, ensure_ascii=False, indent=2))

        print("\n=== 虚假引文校验 ===")
        r = await agent.cite_verify("天道酬勤，君子当自强", source="论语")
        print(json.dumps(r, ensure_ascii=False, indent=2))

    asyncio.run(demo())
