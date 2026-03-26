"""
uap — Universal Agent Protocol Python SDK

万Agent互联协议 Python 实现

Quick Start:
    from uap import AgentDID, UAPMessage, Intent, UAPClient
    from uap.decorators import uap_agent, uap_capability

    # 1. 声明 Agent
    @uap_agent(
        did="did:uap:myns:my-agent",
        name="My Agent",
        version="1.0.0",
        endpoint="https://my-api.example.com",
    )
    class MyAgent:

        @uap_capability(capability_id="my.greet", name="打招呼")
        async def greet(self, name: str) -> dict:
            return {"message": f"你好，{name}！"}

    # 2. 调用远程 Agent
    async with UAPClient(
        caller_did=AgentDID.parse("did:uap:caller:agent"),
        capability_token="your-token",
    ) as client:
        resp = await client.invoke(
            target_did=AgentDID.parse("did:uap:myns:my-agent"),
            endpoint="https://my-api.example.com",
            capability="my.greet",
            input={"name": "茂林"},
        )
        print(resp.output)
"""

from .identity import AgentDID, DIDDocument
from .intent import Intent, IntentType, IntentOptions, Depth, ResponseFormat
from .envelope import UAPMessage, UAPResponse, AccessTier, Routing, Auth, EnvelopeMeta
from .capability import Capability, CapabilityManifest, RateLimit
from .client import UAPClient, UAPClientError, CapabilityNotFoundError, AuthError
from .decorators import uap_agent, uap_capability, get_registry, get_agent

__version__ = "0.1.0"
__all__ = [
    # 身份
    "AgentDID",
    "DIDDocument",
    # 意图
    "Intent",
    "IntentType",
    "IntentOptions",
    "Depth",
    "ResponseFormat",
    # 信封
    "UAPMessage",
    "UAPResponse",
    "AccessTier",
    "Routing",
    "Auth",
    "EnvelopeMeta",
    # 能力
    "Capability",
    "CapabilityManifest",
    "RateLimit",
    # 客户端
    "UAPClient",
    "UAPClientError",
    "CapabilityNotFoundError",
    "AuthError",
    # 装饰器
    "uap_agent",
    "uap_capability",
    "get_registry",
    "get_agent",
]
