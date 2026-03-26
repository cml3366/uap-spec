"""
agents/writing_agent.py — 写作 Agent
职责：内容整合 · 多格式输出 · 古今融合写作 · 赋文/论文/报告生成

UAP 能力：
  - writing.compose        综合写作（整合检索+义理结果）
  - writing.fu_style       赋体文学创作（茂林专项）
  - writing.modern_apply   古典智慧现代应用文章
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import logging
from typing import Optional

logger = logging.getLogger("openwen.writing")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../uap-python"))
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier

from core.config import config
from core.llm import LLMClient

# 写作系统提示
_WRITING_SYSTEM = """你是一位兼通古今的文章大家，精通古典文学格式（赋、论、记、铭）与现代写作。
写作原则：
1. 古今融合：以古典智慧为魂，以现代语言为体
2. 引文有据：所有典籍引用必须真实，括注出处
3. 层次分明：起承转合，结构清晰
4. 东西对话：适当引入西方哲学印证，但中华文化为主
5. 文质彬彬：文采与内容并重"""

_FU_SYSTEM = """你是精通辞赋之道的文学家，专擅骈文赋体。
赋文要求：
1. 格律严谨：注重四六对仗，讲究声韵铿锵
2. 意象宏阔：善用天地山河、阴阳变化等宏观意象
3. 哲理深邃：以华美文辞承载深刻哲思
4. 引经据典：融汇六经诸子，用典贴切
5. 古今对话：以古典语境照见当代问题"""


@uap_agent(
    did=config.agent_did("writing"),
    name="写作 Agent",
    version="1.0.0",
    endpoint=config.agent_endpoint("writing"),
    description="内容整合·多格式写作·赋文创作·古典智慧现代化表达",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["写作", "赋文", "内容生成", "古今融合"],
)
class WritingAgent:
    """
    OpenWen 写作 Agent
    负责整合检索和义理分析结果，生成完整的学术/文学/应用内容
    """

    def __init__(self):
        self.llm = LLMClient()
        logger.info("WritingAgent 初始化完成")

    @uap_capability(
        capability_id="writing.compose",
        name="综合写作",
        description="整合检索语料和义理分析，生成完整的主题文章",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=4000,
        required_agents=[
            "did:uap:openwen:retrieval-agent",
            "did:uap:openwen:doctrine-agent",
        ],
    )
    async def compose(
        self,
        topic: str,
        corpus_results: Optional[list[dict]] = None,
        doctrine_result: Optional[dict] = None,
        format: str = "article",
        word_count: int = 800,
        audience: str = "general",
    ) -> dict:
        """
        综合写作：整合检索和义理分析结果

        Args:
            topic: 写作主题
            corpus_results: 检索 Agent 返回的语料
            doctrine_result: 义理 Agent 返回的解读
            format: 输出格式 article/report/essay/fu
            word_count: 目标字数
            audience: 受众 general/academic/business
        """
        logger.info(f"[写作] topic={topic!r} format={format} ~{word_count}字")

        # 整合上游 Agent 的输出构建写作素材
        materials = [f"主题：{topic}"]

        if corpus_results:
            citations = [
                f"- 「{r['text']}」（{r['source']}）"
                for r in corpus_results[:5]
            ]
            materials.append("可用典籍素材：\n" + "\n".join(citations))

        if doctrine_result:
            if "interpretation" in doctrine_result:
                materials.append(f"义理分析：{doctrine_result['interpretation']}")
            if "modern_application" in doctrine_result:
                materials.append(f"现代映射：{doctrine_result['modern_application']}")

        format_instructions = {
            "article": f"撰写一篇{word_count}字的主题文章，结构清晰，引用有据",
            "report": f"撰写{word_count}字的研究报告，含摘要、正文、结论",
            "essay": f"撰写{word_count}字的哲学随笔，思想深邃，文笔优雅",
            "fu": f"以骈赋体裁创作，四六对仗，{word_count}字左右",
        }

        audience_instructions = {
            "general": "面向普通读者，深入浅出",
            "academic": "面向学术读者，引证严谨",
            "business": "面向商界人士，古为今用，联系实践",
        }

        prompt = (
            "\n".join(materials)
            + f"\n\n写作要求：{format_instructions.get(format, format_instructions['article'])}"
            + f"\n受众：{audience_instructions.get(audience, '')}"
            + "\n\n请直接输出文章内容，不需要额外解释。"
        )

        content = await self.llm.chat(
            user=prompt,
            system=_WRITING_SYSTEM,
        )

        return {
            "topic": topic,
            "format": format,
            "content": content,
            "word_count_estimate": len(content),
            "sources_used": len(corpus_results or []),
            "agent": "writing-agent",
        }

    @uap_capability(
        capability_id="writing.fu_style",
        name="赋体创作",
        description="以骈文赋体形式创作哲学文章（茂林《2025年代论哲学》专项）",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=5000,
    )
    async def fu_style(
        self,
        title: str,
        theme: str,
        key_concepts: Optional[list[str]] = None,
        eastern_references: Optional[list[str]] = None,
        western_references: Optional[list[str]] = None,
        length: str = "medium",
    ) -> dict:
        """
        赋体文学创作（专为茂林《2025年代论哲学》设计）

        Args:
            title: 赋文标题
            theme: 核心主题
            key_concepts: 核心概念列表
            eastern_references: 东方典籍参考
            western_references: 西方哲学参考
            length: short(300)/medium(600)/long(1200)
        """
        logger.info(f"[赋文] title={title!r} theme={theme!r}")

        length_map = {"short": "三百字", "medium": "六百字", "long": "一千二百字"}
        target_len = length_map.get(length, "六百字")

        materials = []
        if key_concepts:
            materials.append(f"核心概念：{' · '.join(key_concepts)}")
        if eastern_references:
            materials.append(f"东方典籍：{' · '.join(eastern_references)}")
        if western_references:
            materials.append(f"西方哲学：{' · '.join(western_references)}")

        prompt = f"""请以骈赋体裁，创作一篇题为《{title}》的赋文。

主题：{theme}
{chr(10).join(materials)}
目标字数：{target_len}

要求：
- 四六对仗，声韵铿锵
- 融汇东西哲学，以中华文化为主
- 意象宏阔，哲理深邃
- 可引用典籍，但须真实有据
- 结构：序→赋体正文→尾声（可含骚体换行）"""

        content = await self.llm.chat(
            user=prompt,
            system=_FU_SYSTEM,
        )

        return {
            "title": title,
            "theme": theme,
            "content": content,
            "format": "fu_style",
            "key_concepts": key_concepts or [],
            "agent": "writing-agent",
        }

    @uap_capability(
        capability_id="writing.modern_apply",
        name="古典智慧现代应用",
        description="将古典哲学智慧转化为现代商业、管理、科技领域的实用洞见",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=3000,
    )
    async def modern_apply(
        self,
        classical_wisdom: str,
        source: Optional[str] = None,
        target_domain: str = "business",
        case_study: Optional[str] = None,
    ) -> dict:
        """
        古典智慧现代应用转化

        Args:
            classical_wisdom: 古典智慧文本
            source: 出处
            target_domain: 应用领域 business/tech/management/life
            case_study: 具体案例背景
        """
        logger.info(f"[现代应用] domain={target_domain} wisdom={classical_wisdom[:30]!r}")

        domain_contexts = {
            "business": "商业策略与企业管理",
            "tech": "科技创新与AI伦理",
            "management": "团队管理与组织文化",
            "life": "个人修身与生活智慧",
        }

        prompt = f"""古典智慧：「{classical_wisdom}」
出处：{source or '未知'}
应用领域：{domain_contexts.get(target_domain, target_domain)}
{f'具体情境：{case_study}' if case_study else ''}

请写一篇800字左右的应用转化文章：
1. 首先精准解读原典精义
2. 分析与现代{target_domain}领域的内在联系
3. 给出3-5条具体可操作的现代应用建议
4. 举一个真实或虚构的应用案例
5. 结语：古今相通的普遍智慧"""

        content = await self.llm.chat(user=prompt, system=_WRITING_SYSTEM)

        return {
            "classical_wisdom": classical_wisdom,
            "target_domain": target_domain,
            "content": content,
            "agent": "writing-agent",
        }


# ── FastAPI 应用 ─────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI(title="OpenWen · 写作 Agent", version="1.0.0")
    reg = get_agent(config.agent_did("writing"))
    if reg:
        uap = UAPServer(app, reg)
        uap.mount()
except ImportError:
    pass


if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = WritingAgent()
        print("=== 赋文创作 ===")
        r = await agent.fu_style(
            title="2025年代论哲学赋",
            theme="AI时代东西哲学对话与文明融合",
            key_concepts=["天人合一", "仁", "道", "量子纠缠"],
            eastern_references=["周易·系辞", "道德经", "论语"],
            western_references=["海德格尔存在论", "过程哲学", "量子力学"],
            length="medium",
        )
        print(r["content"])

    asyncio.run(demo())
