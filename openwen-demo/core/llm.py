"""
core/llm.py — LLM 调用封装
通过 LiteLLM 代理实现模型无关性
Qwen / Claude / OpenAI 三键切换
"""
from __future__ import annotations
import os
import json
import logging
from typing import Optional, AsyncIterator

logger = logging.getLogger("openwen.llm")


class LLMClient:
    """
    LLM 调用客户端
    底层通过 LiteLLM Proxy 路由到 Qwen/Claude/OpenAI

    用法:
        llm = LLMClient()
        response = await llm.chat(
            system="你是易经专家",
            user="解读乾卦",
        )
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ):
        from .config import config
        self.model = model or config.llm_model
        self.api_base = api_base or config.llm_api_base
        self.api_key = api_key or config.llm_api_key
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def chat(
        self,
        user: str,
        system: Optional[str] = None,
        history: Optional[list[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        单次对话调用

        Args:
            user: 用户消息
            system: 系统提示
            history: 历史消息列表 [{"role": "user/assistant", "content": "..."}]
            json_mode: 是否强制 JSON 输出
        Returns:
            模型回复文本
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        try:
            import httpx
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.api_base}/v1/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.debug(
                    f"LLM [{self.model}] "
                    f"in={data['usage']['prompt_tokens']} "
                    f"out={data['usage']['completion_tokens']}"
                )
                return content

        except ImportError:
            # httpx 未安装时返回 mock 响应（开发用）
            logger.warning("httpx not installed, returning mock LLM response")
            return self._mock_response(user, system)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _mock_response(self, user: str, system: Optional[str]) -> str:
        """Mock 响应（LiteLLM 未启动时的开发占位）"""
        if "检索" in (system or "") or "search" in user.lower():
            return json.dumps({
                "results": [
                    {"text": "天行健，君子以自强不息", "source": "周易·乾卦·象辞", "score": 0.95},
                    {"text": "地势坤，君子以厚德载物", "source": "周易·坤卦·象辞", "score": 0.88},
                ],
                "query": user[:50],
            }, ensure_ascii=False)
        elif "义理" in (system or "") or "解读" in user:
            return json.dumps({
                "interpretation": "乾卦象征纯阳之气，代表创造力与领导力。天道刚健，运行不息，君子效法天道，自强不息，永不懈怠。",
                "citations": ["《彖传》：大哉乾元，万物资始", "《象传》：天行健，君子以自强不息"],
                "philosophical_depth": "乾卦六爻皆阳，纯阳之卦，象征创始、开拓之力",
                "modern_application": "事业当积极进取，把握天时，但须警惕「亢龙有悔」——盛极必衰，知进退方是大道",
            }, ensure_ascii=False)
        elif "写作" in (system or "") or "撰写" in user:
            return "【乾卦解析】\n\n乾为天，健也。乾卦六爻皆阳，象征纯粹的创造力与生命力……\n\n**核心启示**：天道刚健，周流不息。君子效法天道，当自强不息，积极进取。"
        elif "审校" in (system or "") or "润色" in user:
            return json.dumps({
                "quality_score": 0.88,
                "issues": ["第二段引文需核实出处", "建议增加现代案例"],
                "suggestions": ["引文格式统一为【典籍·章节】格式"],
                "revised_content": "【已优化版本】\n乾为天，健也。象曰：天行健，君子以自强不息……",
                "approved": True,
            }, ensure_ascii=False)
        return f"[Mock LLM] 处理请求：{user[:80]}"

    async def chat_json(self, user: str, system: Optional[str] = None, **kwargs) -> dict:
        """调用 LLM 并解析 JSON 输出"""
        response = await self.chat(user=user, system=system, json_mode=True, **kwargs)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"raw_response": response}


# 全局 LLM 客户端
llm = LLMClient()
