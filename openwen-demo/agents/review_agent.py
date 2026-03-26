"""
agents/review_agent.py — 审校 Agent
职责：内容润色 · 引文核实 · 质量评分 · 终审输出

UAP 能力：
  - review.check          全面内容审校（引文+逻辑+文采）
  - review.cite_audit     引文专项审查
  - review.score          内容质量评分
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from typing import Optional

logger = logging.getLogger("openwen.review")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../uap-python"))
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier

from core.config import config
from core.llm import LLMClient

_REVIEW_SYSTEM = """你是一位严谨的国学学术编辑，负责对文章进行全面审校。
审校标准：
1. 引文准确性：所有引文必须与原典相符，伪造或错误引文必须指出
2. 逻辑严密性：论证链路是否清晰，是否存在逻辑跳跃
3. 文采质量：语言是否优雅，是否达到预期文体要求
4. 东西融合度：中西哲学对比是否贴切，是否流于表面
5. 实用价值：古典智慧的现代转化是否有说服力
以JSON格式返回审校报告"""


@uap_agent(
    did=config.agent_did("review"),
    name="审校 Agent",
    version="1.0.0",
    endpoint=config.agent_endpoint("review"),
    description="内容润色·引文核实·质量评分·终审把关",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["审校", "质控", "引文核实", "润色"],
)
class ReviewAgent:
    """
    OpenWen 审校 Agent
    流水线最后一关，负责质量把关和内容优化
    """

    def __init__(self):
        self.llm = LLMClient()
        logger.info("ReviewAgent 初始化完成")

    @uap_capability(
        capability_id="review.check",
        name="全面审校",
        description="对内容进行引文、逻辑、文采的全面审查和优化",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=3000,
    )
    async def check(
        self,
        content: str,
        content_type: str = "article",
        strict_mode: bool = False,
    ) -> dict:
        """
        全面内容审校

        Args:
            content: 待审校的内容
            content_type: article/fu_style/report
            strict_mode: 严格模式，更细致地核查引文
        """
        logger.info(f"[审校] type={content_type} strict={strict_mode} len={len(content)}")

        mode_note = "（严格模式：对每条引文进行逐一核查）" if strict_mode else ""

        result = await self.llm.chat_json(
            user=f"""请对以下{content_type}进行全面审校{mode_note}：

---
{content[:3000]}
---

请返回JSON审校报告，包含：
- quality_score: 综合评分 0-1.0
- citation_issues: 引文问题列表（每条含 text, issue, suggestion）
- logic_issues: 逻辑问题列表
- style_suggestions: 文采优化建议列表
- approved: 是否通过审校（bool）
- revised_paragraphs: 需要修改的段落（原文→修改建议）
- overall_comment: 总体评语（50字以内）""",
            system=_REVIEW_SYSTEM,
        )

        # 补充元信息
        result["content_length"] = len(content)
        result["content_type"] = content_type
        result["agent"] = "review-agent"

        approved = result.get("approved", False)
        score = result.get("quality_score", 0)
        logger.info(f"[审校] 评分={score:.2f} 通过={approved}")

        return result

    @uap_capability(
        capability_id="review.cite_audit",
        name="引文专项审查",
        description="专门对文章中的所有引文进行逐一核查，防止AI幻觉",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=2000,
        required_agents=["did:uap:openwen:retrieval-agent"],
    )
    async def cite_audit(
        self,
        content: str,
    ) -> dict:
        """
        引文专项审查
        提取文章中所有引文并验证真实性
        """
        logger.info(f"[引文审查] content_len={len(content)}")

        # 提取所有引文
        extract_result = await self.llm.chat_json(
            user=f"请提取以下文章中所有的典籍引文，返回JSON数组：\n\n{content[:2000]}\n\n格式：{{\"citations\": [{{\"text\": \"引文内容\", \"claimed_source\": \"声称出处\"}}]}}",
            system="你是引文提取专家，只提取引文，不做解读",
        )

        citations = extract_result.get("citations", [])
        logger.info(f"[引文审查] 提取到 {len(citations)} 条引文")

        # 对每条引文做简单校验
        audit_results = []
        for cite in citations:
            text = cite.get("text", "")
            source = cite.get("claimed_source", "")
            # 简单规则校验（Phase 3 接入真实检索）
            suspicious = (
                len(text) > 30 and "。" not in text  # 过长且无标点
                or "人工智能" in text  # 现代词汇出现在古籍引文
                or "科技" in text
            )
            audit_results.append({
                "text": text,
                "claimed_source": source,
                "status": "suspicious" if suspicious else "likely_valid",
                "note": "含现代词汇，需核实" if suspicious else "格式正常，建议人工抽查",
            })

        issues = [r for r in audit_results if r["status"] == "suspicious"]
        return {
            "total_citations": len(citations),
            "suspicious_count": len(issues),
            "audit_results": audit_results,
            "passed": len(issues) == 0,
            "recommendation": "建议人工核查以上可疑引文" if issues else "引文格式均符合规范",
            "agent": "review-agent",
        }

    @uap_capability(
        capability_id="review.score",
        name="内容质量评分",
        description="对内容进行多维度质量评分，生成可视化评分报告",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=1500,
    )
    async def score(
        self,
        content: str,
        dimensions: Optional[list[str]] = None,
    ) -> dict:
        """
        多维度内容质量评分

        Args:
            content: 待评分内容
            dimensions: 评分维度，默认全维度
        """
        default_dimensions = [
            "引文准确性", "义理深度", "文采质量",
            "东西融合", "逻辑严密", "实用价值"
        ]
        dims = dimensions or default_dimensions

        result = await self.llm.chat_json(
            user=f"""请对以下内容按以下维度评分（每项0-10分）：
维度：{' · '.join(dims)}

内容：
{content[:2000]}

返回JSON：{{
  "scores": {{"维度名": 分数, ...}},
  "total": 综合得分,
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["不足1", "不足2"],
  "grade": "A/B/C/D"
}}""",
            system="你是严格的学术内容评审专家",
        )

        result["dimensions_evaluated"] = dims
        result["agent"] = "review-agent"
        return result


# ── FastAPI 应用 ─────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI(title="OpenWen · 审校 Agent", version="1.0.0")
    reg = get_agent(config.agent_did("review"))
    if reg:
        uap = UAPServer(app, reg)
        uap.mount()
except ImportError:
    pass


if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = ReviewAgent()
        test_content = """乾为天，健也。天行健，君子以自强不息。
此句出自《周易·乾卦·象辞》，王弼注云：「健而无休者，天之德也。」
乾卦六爻皆阳，纯阳之气，象征创造力与领导力。
正如亚里士多德在《尼各马可伦理学》中论及德性时所言，
中道之美在于不偏不倚，中华「中庸」与此有异曲同工之妙。"""

        print("=== 全面审校 ===")
        r = await agent.check(test_content)
        print(json.dumps(r, ensure_ascii=False, indent=2))

        print("\n=== 质量评分 ===")
        r = await agent.score(test_content)
        print(json.dumps(r, ensure_ascii=False, indent=2))

    asyncio.run(demo())
