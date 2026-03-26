"""
agents/coordinator_agent.py — 协调 Agent
职责：任务拆解 · 链路规划 · 5个核心Agent编排 · 结果聚合

这是 OpenWen 的大脑：接收用户请求，自动拆解为子任务，
按 DAG 顺序调度 检索→义理→写作→审校，汇聚最终输出。

UAP 能力：
  - coordinator.run_pipeline   完整五Agent协作流水线
  - coordinator.route          智能意图路由（单Agent直调）
  - coordinator.status         任务状态查询
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import time
import uuid
import asyncio
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("openwen.coordinator")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../uap-python"))
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier

from core.config import config
from core.llm import LLMClient

# 导入其他 Agent
from agents.retrieval_agent import RetrievalAgent
from agents.doctrine_agent import DoctrineAgent
from agents.writing_agent import WritingAgent
from agents.review_agent import ReviewAgent


@dataclass
class PipelineTask:
    """流水线任务追踪"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    request: str = ""
    status: str = "pending"   # pending/running/done/failed
    steps: list[dict] = field(default_factory=list)
    result: Optional[dict] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def add_step(self, name: str, status: str, data: Any = None, elapsed_ms: int = 0):
        self.steps.append({
            "step": name,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "data_keys": list(data.keys()) if isinstance(data, dict) else None,
        })

    def to_dict(self) -> dict:
        elapsed = (self.finished_at or time.time()) - self.started_at
        return {
            "task_id": self.task_id,
            "request": self.request[:100],
            "status": self.status,
            "total_elapsed_ms": int(elapsed * 1000),
            "steps": self.steps,
            "step_count": len(self.steps),
        }


# ── 协调 Agent ────────────────────────────────────────────────

@uap_agent(
    did=config.agent_did("coordinator"),
    name="协调 Agent",
    version="1.0.0",
    endpoint=config.agent_endpoint("coordinator"),
    description="OpenWen 大脑·任务拆解·五Agent流水线编排·结果聚合输出",
    access_tier=AccessTier.AUTHENTICATED,
    tags=["协调", "编排", "流水线", "主控"],
)
class CoordinatorAgent:
    """
    OpenWen 协调 Agent — 五Agent协作的总指挥

    流水线架构：
    用户请求
        ↓
    [协调Agent] 意图解析 + 任务拆解
        ↓
    [检索Agent] 语料检索 + 引文预检
        ↓
    [义理Agent] 经义解读 + 哲学映射
        ↓
    [写作Agent] 内容整合 + 格式生成
        ↓
    [审校Agent] 质量把关 + 润色输出
        ↓
    最终结果
    """

    def __init__(self):
        self.llm = LLMClient()
        # 直接实例化各 Agent（生产环境改为 UAP HTTP 调用）
        self.retrieval = RetrievalAgent()
        self.doctrine = DoctrineAgent()
        self.writing = WritingAgent()
        self.review = ReviewAgent()
        self._tasks: dict[str, PipelineTask] = {}
        logger.info("CoordinatorAgent 初始化完成 — 5个核心Agent就绪")

    async def _parse_intent(self, request: str) -> dict:
        """解析用户请求意图，规划流水线参数"""
        result = await self.llm.chat_json(
            user=f"分析以下请求，提取关键信息：\n\n{request}\n\n返回JSON：{{\"topic\": \"主题\", \"question\": \"核心问题\", \"search_query\": \"检索关键词\", \"output_format\": \"article/fu_style/report\", \"depth\": \"brief/standard/scholarly\", \"domain\": \"business/academic/general\"}}",
            system="你是任务分析专家，准确提取请求的核心意图",
        )
        return result

    # ── 核心能力：五Agent流水线 ────────────────────────────────

    @uap_capability(
        capability_id="coordinator.run_pipeline",
        name="五Agent协作流水线",
        description="接收用户请求，自动编排检索→义理→写作→审校全流程",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=12000,
        required_agents=[
            "did:uap:openwen:retrieval-agent",
            "did:uap:openwen:doctrine-agent",
            "did:uap:openwen:writing-agent",
            "did:uap:openwen:review-agent",
        ],
    )
    async def run_pipeline(
        self,
        request: str,
        output_format: str = "article",
        depth: str = "standard",
        auto_review: bool = True,
    ) -> dict:
        """
        完整五Agent协作流水线

        Args:
            request: 用户自然语言请求
            output_format: 输出格式 article/fu_style/report
            depth: 分析深度 brief/standard/scholarly
            auto_review: 是否自动审校

        Returns:
            完整的流水线输出，含每步结果和最终内容
        """
        task = PipelineTask(request=request)
        self._tasks[task.task_id] = task
        task.status = "running"

        logger.info(f"[协调] 任务 {task.task_id} 启动 | {request[:60]!r}")
        pipeline_start = time.time()

        try:
            # ── STEP 0: 意图解析 ──────────────────────────────
            step_start = time.time()
            logger.info(f"[{task.task_id}] ⟶ Step 0: 意图解析")
            intent = await self._parse_intent(request)

            topic = intent.get("topic", request[:50])
            question = intent.get("question", request)
            search_query = intent.get("search_query", topic)
            fmt = intent.get("output_format", output_format)
            dep = intent.get("depth", depth)

            task.add_step(
                "intent_parse", "done",
                intent, int((time.time() - step_start) * 1000),
            )
            logger.info(f"[{task.task_id}] ✓ 意图解析 | topic={topic!r}")

            # ── STEP 1: 检索 ──────────────────────────────────
            step_start = time.time()
            logger.info(f"[{task.task_id}] ⟶ Step 1: 检索 Agent")
            corpus_result = await self.retrieval.search(
                query=search_query, top_k=6
            )
            elapsed = int((time.time() - step_start) * 1000)
            task.add_step("retrieval", "done", corpus_result, elapsed)
            logger.info(
                f"[{task.task_id}] ✓ 检索完成 | "
                f"{corpus_result['total_found']} 条 | {elapsed}ms"
            )

            # ── STEP 2: 义理解读 ──────────────────────────────
            step_start = time.time()
            logger.info(f"[{task.task_id}] ⟶ Step 2: 义理 Agent")

            # 取最相关的一条典籍文本做义理解读
            top_text = corpus_result["results"][0] if corpus_result["results"] else {}
            doctrine_result = await self.doctrine.interpret(
                text=top_text.get("text", topic),
                source=top_text.get("source"),
                question=question,
                depth=dep,
            )
            elapsed = int((time.time() - step_start) * 1000)
            task.add_step("doctrine", "done", doctrine_result, elapsed)
            logger.info(f"[{task.task_id}] ✓ 义理解读完成 | {elapsed}ms")

            # ── STEP 3: 写作 ──────────────────────────────────
            step_start = time.time()
            logger.info(f"[{task.task_id}] ⟶ Step 3: 写作 Agent")

            if fmt == "fu_style":
                writing_result = await self.writing.fu_style(
                    title=f"{topic}赋",
                    theme=question,
                    key_concepts=doctrine_result.get("key_concepts", []),
                    eastern_references=[r["source"] for r in corpus_result["results"][:3]],
                    length="medium" if dep == "standard" else "long",
                )
            else:
                writing_result = await self.writing.compose(
                    topic=topic,
                    corpus_results=corpus_result["results"],
                    doctrine_result=doctrine_result,
                    format=fmt,
                    audience=intent.get("domain", "general"),
                )

            elapsed = int((time.time() - step_start) * 1000)
            task.add_step("writing", "done", writing_result, elapsed)
            logger.info(f"[{task.task_id}] ✓ 写作完成 | {elapsed}ms")

            # ── STEP 4: 审校（可选）──────────────────────────
            review_result = None
            if auto_review:
                step_start = time.time()
                logger.info(f"[{task.task_id}] ⟶ Step 4: 审校 Agent")

                review_result = await self.review.check(
                    content=writing_result.get("content", ""),
                    content_type=fmt,
                )
                elapsed = int((time.time() - step_start) * 1000)
                task.add_step("review", "done", review_result, elapsed)
                logger.info(
                    f"[{task.task_id}] ✓ 审校完成 | "
                    f"评分={review_result.get('quality_score', 'N/A')} | {elapsed}ms"
                )

            # ── 汇聚输出 ──────────────────────────────────────
            total_ms = int((time.time() - pipeline_start) * 1000)
            task.status = "done"
            task.finished_at = time.time()

            final_output = {
                # 核心内容
                "content": writing_result.get("content", ""),
                "topic": topic,
                "format": fmt,

                # 流水线元数据
                "pipeline": {
                    "task_id": task.task_id,
                    "total_elapsed_ms": total_ms,
                    "steps_completed": len(task.steps),
                    "agents_used": ["coordinator", "retrieval", "doctrine", "writing"]
                    + (["review"] if auto_review else []),
                },

                # 各 Agent 详细输出
                "details": {
                    "intent": intent,
                    "corpus": {
                        "total_found": corpus_result["total_found"],
                        "top_sources": [r["source"] for r in corpus_result["results"][:3]],
                    },
                    "doctrine": {
                        "interpretation_preview": str(
                            doctrine_result.get("interpretation", "")
                        )[:200],
                        "citations": doctrine_result.get("citations", []),
                    },
                    "writing": {
                        "word_count": writing_result.get("word_count_estimate", 0),
                    },
                    "review": {
                        "quality_score": review_result.get("quality_score") if review_result else None,
                        "approved": review_result.get("approved") if review_result else None,
                        "overall_comment": review_result.get("overall_comment") if review_result else None,
                    } if auto_review else None,
                },
            }

            task.result = final_output
            logger.info(
                f"[{task.task_id}] 🎉 流水线完成 | 总耗时 {total_ms}ms"
            )
            return final_output

        except Exception as e:
            task.status = "failed"
            task.finished_at = time.time()
            logger.error(f"[{task.task_id}] ❌ 流水线失败: {e}", exc_info=True)
            raise

    # ── 智能路由（单Agent直调）──────────────────────────────

    @uap_capability(
        capability_id="coordinator.route",
        name="智能意图路由",
        description="解析请求意图，路由到最合适的单个Agent直接处理",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=500,
    )
    async def route(self, request: str) -> dict:
        """
        智能路由：判断请求应交给哪个 Agent 处理

        简单请求不走完整流水线，直接路由到对应 Agent
        """
        intent = await self.llm.chat_json(
            user=f"判断以下请求最适合哪个处理步骤：\n{request}\n\n返回JSON：{{\"agent\": \"retrieval/doctrine/writing/review/pipeline\", \"reason\": \"原因\", \"capability\": \"对应能力ID\"}}",
            system="你是任务路由专家",
        )

        agent_map = {
            "retrieval": self.retrieval,
            "doctrine": self.doctrine,
            "writing": self.writing,
            "review": self.review,
        }

        recommended = intent.get("agent", "pipeline")
        return {
            "request": request,
            "recommended_agent": recommended,
            "recommended_capability": intent.get("capability"),
            "reason": intent.get("reason"),
            "agent_did": config.agent_did(recommended) if recommended != "pipeline" else config.agent_did("coordinator"),
            "use_pipeline": recommended == "pipeline",
        }

    @uap_capability(
        capability_id="coordinator.status",
        name="任务状态查询",
        description="查询异步流水线任务的执行状态",
        access_tier=AccessTier.AUTHENTICATED,
        avg_latency_ms=50,
    )
    async def status(self, task_id: str) -> dict:
        """查询任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found", "known_tasks": list(self._tasks.keys())}
        return task.to_dict()


# ── FastAPI 应用 ─────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI(
        title="OpenWen · 协调 Agent",
        description="五Agent协作流水线总控 — OpenWen 核心入口",
        version="1.0.0",
    )
    reg = get_agent(config.agent_did("coordinator"))
    if reg:
        uap = UAPServer(app, reg)
        uap.mount()

        @app.get("/")
        async def root():
            return {
                "agent": "OpenWen 协调 Agent",
                "pipeline": "检索→义理→写作→审校",
                "invoke": "/uap/invoke",
                "capability": "coordinator.run_pipeline",
            }

except ImportError:
    pass


if __name__ == "__main__":
    import asyncio

    async def demo():
        print("=" * 60)
        print("OpenWen 五Agent协作流水线 Demo")
        print("=" * 60)

        coordinator = CoordinatorAgent()

        # ── Demo 1: 标准文章流水线 ────────────────────────────
        print("\n【Demo 1】乾卦现代管理学解读")
        print("-" * 40)
        result = await coordinator.run_pipeline(
            request="解读乾卦对现代创业者的启示，结合天行健自强不息的精神",
            output_format="article",
            depth="standard",
            auto_review=True,
        )

        print(f"\n📄 最终内容（节选）：")
        print(result["content"][:500] + "...\n")
        print(f"⏱  总耗时：{result['pipeline']['total_elapsed_ms']}ms")
        print(f"🤖 使用Agent：{' → '.join(result['pipeline']['agents_used'])}")
        print(f"📚 引用典籍：{result['details']['corpus']['top_sources']}")
        if result['details']['review']:
            print(f"✅ 审校评分：{result['details']['review']['quality_score']}")

        # ── Demo 2: 赋文流水线 ───────────────────────────────
        print("\n\n【Demo 2】2025年代论哲学赋")
        print("-" * 40)
        result2 = await coordinator.run_pipeline(
            request="以赋文形式论述2025年AI时代东西哲学的融合与对话，"
                    "涵盖量子力学与易经、人工智能伦理与儒家仁义",
            output_format="fu_style",
            depth="scholarly",
            auto_review=False,
        )
        print(f"\n📜 赋文（节选）：")
        print(result2["content"][:600] + "...\n")
        print(f"⏱  总耗时：{result2['pipeline']['total_elapsed_ms']}ms")

        # ── Demo 3: 智能路由 ─────────────────────────────────
        print("\n\n【Demo 3】智能路由测试")
        print("-" * 40)
        requests = [
            "帮我检索道德经中关于水的句子",
            "解读中庸之道与亚里士多德中道的哲学异同",
            "写一篇关于易经变通思想的现代商业应用文章",
        ]
        for req in requests:
            route = await coordinator.route(req)
            print(f"请求：{req[:40]}")
            print(f"路由→ {route['recommended_agent']} | {route['recommended_capability']}")
            print(f"原因：{route['reason']}\n")

    asyncio.run(demo())
