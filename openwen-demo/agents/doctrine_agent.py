"""
agents/doctrine_agent.py — 义理 Agent
职责：经义解读 · 哲学诠释 · 东西方映射 · 学术深度分析

UAP 能力：
  - doctrine.interpret       经典义理深度解读
  - doctrine.east_west_map   东西方哲学对应映射
  - doctrine.concept_explain 核心概念解释
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from typing import Optional

logger = logging.getLogger("openwen.doctrine")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../uap-python"))
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier

from core.config import config
from core.llm import LLMClient

# 义理解读系统提示
_DOCTRINE_SYSTEM = """你是一位精通中国传统哲学的学者，专门研究儒道佛三家及易学。
你的任务是对古典文本进行深度义理解读，要求：
1. 引用原文时必须准确，标注出处（典籍·章节）
2. 阐释时兼顾原典精义与当代理解
3. 可以适当融合东西方哲学对比，但不得牵强附会
4. 输出格式为 JSON，包含 interpretation, citations, philosophical_depth, modern_application
5. citations 数组中每条引用必须是真实典籍文本"""

# 东西方哲学映射知识库
_EAST_WEST_MAP = {
    "仁": {
        "western": ["美德伦理学 (Virtue Ethics · 亚里士多德)", "利他主义 (Altruism)", "仁爱 (Benevolence · 康德)"],
        "insight": "儒家「仁」强调关系中的爱，西方美德论强调个体品格，两者皆以道德完善为目标，路径不同",
    },
    "道": {
        "western": ["存在本身 (Being Itself · 海德格尔)", "逻各斯 (Logos · 赫拉克利特)", "绝对精神 (Absolute Spirit · 黑格尔)"],
        "insight": "「道」与赫拉克利特的「逻各斯」最为接近，皆视宇宙为动态流变的统一体",
    },
    "无为": {
        "western": ["消极能力 (Negative Capability · 济慈)", "非强制性权力 (Non-coercive Power)", "自发秩序 (Spontaneous Order · 哈耶克)"],
        "insight": "「无为」并非不作为，而是顺应自然规律，与哈耶克的自发秩序论有深刻共鸣",
    },
    "易": {
        "western": ["辩证法 (Dialectics · 黑格尔)", "过程哲学 (Process Philosophy · 怀特海)", "量子不确定性原理 (Quantum Uncertainty)"],
        "insight": "「变」是《易经》的核心，与过程哲学「现实即过程」高度契合，阴阳互动亦呼应量子叠加态",
    },
    "中庸": {
        "western": ["中道 (Mesotes · 亚里士多德)", "辩证综合 (Dialectical Synthesis)", "实用主义 (Pragmatism · 杜威)"],
        "insight": "「中庸」与亚里士多德「中道」惊人相似，皆强调德性在两极端之间的平衡点",
    },
    "天人合一": {
        "western": ["自然主义 (Naturalism)", "生态哲学 (Ecophilosophy)", "斯多葛派宇宙论 (Stoic Cosmology)"],
        "insight": "「天人合一」是中华哲学独特贡献，强调人与自然的有机统一，超越西方主客二分传统",
    },
}


@uap_agent(
    did=config.agent_did("doctrine"),
    name="义理 Agent",
    version="1.0.0",
    endpoint=config.agent_endpoint("doctrine"),
    description="经义深度解读·哲学诠释·东西方思想映射·学术级分析",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["义理", "哲学", "易学", "儒道佛", "东西比较"],
)
class DoctrineAgent:
    """
    OpenWen 义理 Agent
    负责对检索到的典籍文本进行深度哲学解读
    是 OpenWen 智慧层的核心
    """

    def __init__(self):
        self.llm = LLMClient()
        self.east_west_map = _EAST_WEST_MAP
        logger.info("DoctrineAgent 初始化完成")

    @uap_capability(
        capability_id="doctrine.interpret",
        name="义理解读",
        description="对古典文本进行深度义理诠释，含历代注疏精华与现代映射",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=3000,
    )
    async def interpret(
        self,
        text: str,
        source: Optional[str] = None,
        question: Optional[str] = None,
        context: Optional[str] = None,
        depth: str = "standard",
    ) -> dict:
        """
        经典文本义理深度解读

        Args:
            text: 待解读的古典文本
            source: 文本出处，如"周易·乾卦"
            question: 围绕什么问题解读（可选）
            context: 使用者背景（可选，用于个性化解读）
            depth: 解读深度 brief/standard/scholarly
        """
        logger.info(f"[义理] text={text[:30]!r} depth={depth}")

        prompt_parts = [f"请对以下古典文本进行深度义理解读：\n\n原文：{text}"]
        if source:
            prompt_parts.append(f"出处：{source}")
        if question:
            prompt_parts.append(f"围绕问题：{question}")
        if context:
            prompt_parts.append(f"使用者背景：{context}")

        depth_instructions = {
            "brief": "简洁解读，200字以内，重点突出",
            "standard": "标准解读，400-600字，兼顾义理与实用",
            "scholarly": "学术深度，800字以上，含历代注疏对比、东西哲学映射",
        }
        prompt_parts.append(f"\n解读深度要求：{depth_instructions.get(depth, depth_instructions['standard'])}")
        prompt_parts.append("\n请以JSON格式返回，包含字段：interpretation, citations, philosophical_depth, modern_application, key_concepts")

        result = await self.llm.chat_json(
            user="\n".join(prompt_parts),
            system=_DOCTRINE_SYSTEM,
        )

        # 补充元信息
        result.update({
            "input_text": text,
            "source": source,
            "depth_level": depth,
            "agent": "doctrine-agent",
        })

        logger.info(f"[义理] 解读完成，引文 {len(result.get('citations', []))} 条")
        return result

    @uap_capability(
        capability_id="doctrine.east_west_map",
        name="东西方哲学映射",
        description="把国学核心概念映射到西方哲学体系，建立跨文明对话",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=500,
    )
    async def east_west_map(
        self,
        concept: str,
        direction: str = "both",
    ) -> dict:
        """
        东西方哲学概念映射

        Args:
            concept: 国学概念，如「仁」「道」「无为」「中庸」
            direction: east_to_west / west_to_east / both
        """
        logger.info(f"[东西映射] concept={concept!r}")

        # 先查本地知识库
        if concept in self.east_west_map:
            mapping = self.east_west_map[concept]
            return {
                "concept": concept,
                "western_equivalents": mapping["western"],
                "philosophical_insight": mapping["insight"],
                "source": "openwen_knowledge_base",
                "confidence": "high",
            }

        # 本地没有则调用 LLM
        result = await self.llm.chat_json(
            user=f"请将国学概念「{concept}」映射到西方哲学体系，说明最接近的西方哲学概念及异同",
            system="你是东西方哲学比较研究专家，请以JSON格式返回：concept, western_equivalents(数组), philosophical_insight, key_differences",
        )
        result["source"] = "llm_generated"
        result["confidence"] = "medium"
        return result

    @uap_capability(
        capability_id="doctrine.concept_explain",
        name="核心概念解释",
        description="解释国学核心概念的内涵、外延与历史演变",
        access_tier=AccessTier.OPEN,
        avg_latency_ms=1000,
    )
    async def concept_explain(
        self,
        concept: str,
        tradition: str = "all",
    ) -> dict:
        """
        国学核心概念解释

        Args:
            concept: 待解释的概念
            tradition: 所属传统 confucian/taoist/buddhist/yijing/all
        """
        logger.info(f"[概念解释] concept={concept!r} tradition={tradition}")

        result = await self.llm.chat_json(
            user=f"请解释国学概念「{concept}」在{tradition}传统中的含义、历史演变和当代价值",
            system="你是国学概念专家，以JSON返回：concept, tradition, core_meaning, historical_evolution(数组), modern_value, related_concepts(数组)",
        )
        return result


# ── FastAPI 应用 ─────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI(title="OpenWen · 义理 Agent", version="1.0.0")
    reg = get_agent(config.agent_did("doctrine"))
    if reg:
        uap = UAPServer(app, reg)
        uap.mount()
except ImportError:
    pass


if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = DoctrineAgent()

        print("=== 义理解读：乾卦 ===")
        r = await agent.interpret(
            text="天行健，君子以自强不息",
            source="周易·乾卦·象辞",
            question="创业者如何把握进退之道",
            depth="scholarly",
        )
        print(json.dumps(r, ensure_ascii=False, indent=2))

        print("\n=== 东西映射：无为 ===")
        r = await agent.east_west_map("无为")
        print(json.dumps(r, ensure_ascii=False, indent=2))

    asyncio.run(demo())
