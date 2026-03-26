"""
core/config.py — OpenWen 核心配置
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field


@dataclass
class OpenWenConfig:
    """OpenWen 系统配置"""

    # LLM 配置（通过 LiteLLM 路由）
    llm_model: str = os.getenv("OPENWEN_MODEL", "qwen/qwen-max")
    llm_api_base: str = os.getenv("LITELLM_API_BASE", "http://localhost:4000")
    llm_api_key: str = os.getenv("LITELLM_API_KEY", "sk-openwen")
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.3

    # UAP 端点配置
    base_url: str = os.getenv("OPENWEN_BASE_URL", "http://localhost:8088")
    namespace: str = "openwen"

    # Agent 端口分配
    coordinator_port: int = 8088
    retrieval_port: int = 8089
    doctrine_port: int = 8090
    writing_port: int = 8091
    review_port: int = 8092

    # 知识库配置
    corpus_path: str = os.getenv("CORPUS_PATH", "./data/corpus.jsonl")
    vector_db_path: str = os.getenv("VECTOR_DB_PATH", "./data/chroma")

    # 追踪配置
    langfuse_enabled: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    def agent_endpoint(self, agent_name: str) -> str:
        port_map = {
            "coordinator": self.coordinator_port,
            "retrieval": self.retrieval_port,
            "doctrine": self.doctrine_port,
            "writing": self.writing_port,
            "review": self.review_port,
        }
        port = port_map.get(agent_name, 8088)
        return f"http://localhost:{port}"

    def agent_did(self, agent_name: str) -> str:
        return f"did:uap:{self.namespace}:{agent_name}-agent"


# 全局配置单例
config = OpenWenConfig()
