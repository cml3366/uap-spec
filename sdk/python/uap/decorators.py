"""
uap.decorators — @uap_agent 装饰器
用声明式方式把普通 Python 函数/类变成 UAP Agent

Usage:
    from uap.decorators import uap_agent, uap_capability
    from uap.capability import Capability, AccessTier

    @uap_agent(
        did="did:uap:openwen:yijing-agent",
        name="易经解析 Agent",
        version="1.2.0",
        endpoint="https://api.openwen.io/agents/yijing",
    )
    class YijingAgent:

        @uap_capability(
            capability_id="yijing.interpret",
            name="卦象解读",
            access_tier=AccessTier.AUTHENTICATED,
        )
        async def interpret(self, hexagram: str, question: str, **kwargs) -> dict:
            ...
"""

from __future__ import annotations
import functools
import inspect
from typing import Any, Callable, Optional, Type

from .identity import AgentDID
from .capability import Capability, CapabilityManifest, RateLimit, AccessTier


# 内部注册表：存储所有通过装饰器注册的 Agent
_AGENT_REGISTRY: dict[str, "AgentRegistration"] = {}


class AgentRegistration:
    """Agent 注册信息"""

    def __init__(
        self,
        did: AgentDID,
        name: str,
        version: str,
        endpoint: str,
        description: Optional[str],
        access_tier: str,
        tags: list[str],
    ):
        self.did = did
        self.name = name
        self.version = version
        self.endpoint = endpoint
        self.description = description
        self.access_tier = access_tier
        self.tags = tags
        self.capabilities: list[Capability] = []
        self.handlers: dict[str, Callable] = {}

    def add_capability(self, capability: Capability, handler: Callable):
        self.capabilities.append(capability)
        self.handlers[capability.id] = handler

    def to_manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            did=self.did,
            name=self.name,
            version=self.version,
            endpoint=self.endpoint,
            description=self.description,
            access_tier=self.access_tier,
            tags=self.tags,
            capabilities=self.capabilities,
        )

    async def dispatch(self, capability_id: str, input_data: dict, agent_instance=None) -> dict:
        """根据能力 ID 分发调用，agent_instance 为 Agent 类实例"""
        handler = self.handlers.get(capability_id)
        if not handler:
            raise ValueError(
                f"Capability '{capability_id}' not found. "
                f"Available: {list(self.handlers.keys())}"
            )
        # 如果传入实例，绑定方法；否则直接调用（已绑定场景）
        if agent_instance is not None:
            bound = handler.__get__(agent_instance, type(agent_instance))
        else:
            bound = handler
        if inspect.iscoroutinefunction(bound):
            return await bound(**input_data)
        return bound(**input_data)


def uap_agent(
    did: str,
    name: str,
    version: str,
    endpoint: str,
    description: Optional[str] = None,
    access_tier: str = AccessTier.AUTHENTICATED,
    tags: Optional[list[str]] = None,
):
    """
    类装饰器：将普通类声明为 UAP Agent

    Args:
        did: AgentDID 字符串，如 "did:uap:openwen:yijing-agent"
        name: Agent 显示名称
        version: 语义版本号，如 "1.2.0"
        endpoint: Agent 服务端点 URL
        description: Agent 功能描述
        access_tier: 默认接入层级（open/authenticated/private）
        tags: 标签列表

    Example:
        @uap_agent(
            did="did:uap:openwen:yijing-agent",
            name="易经解析 Agent",
            version="1.0.0",
            endpoint="https://api.openwen.io/agents/yijing",
        )
        class YijingAgent:
            ...
    """

    def decorator(cls: Type) -> Type:
        agent_did = AgentDID.parse(did)
        registration = AgentRegistration(
            did=agent_did,
            name=name,
            version=version,
            endpoint=endpoint,
            description=description,
            access_tier=access_tier,
            tags=tags or [],
        )

        # 扫描类中已用 @uap_capability 标记的方法
        # 注意：此时类尚未实例化，handler 先存原始函数
        # dispatch 时会绑定到实例
        for attr_name in dir(cls):
            method = getattr(cls, attr_name, None)
            if method and hasattr(method, "_uap_capability"):
                cap_meta: Capability = method._uap_capability
                registration.add_capability(cap_meta, method)

        # 把注册信息挂到类上，也存入全局注册表
        cls._uap_registration = registration
        cls._uap_did = agent_did
        _AGENT_REGISTRY[str(agent_did)] = registration

        # 注入快捷方法
        cls.get_manifest = lambda self: registration.to_manifest()
        cls.dispatch = lambda self, cap_id, inp: registration.dispatch(cap_id, inp)

        return cls

    return decorator


def uap_capability(
    capability_id: str,
    name: str,
    description: Optional[str] = None,
    version: str = "1.0.0",
    access_tier: str = AccessTier.AUTHENTICATED,
    rate_limit_rpm: Optional[int] = None,
    avg_latency_ms: Optional[int] = None,
    required_agents: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
):
    """
    方法装饰器：将方法声明为 UAP 可调用能力

    Args:
        capability_id: 能力唯一 ID，如 "yijing.interpret"
        name: 能力显示名称
        description: 能力描述
        version: 能力版本
        access_tier: 接入层级
        rate_limit_rpm: 每分钟请求限制
        avg_latency_ms: 平均响应时间（毫秒）
        required_agents: 依赖的其他 Agent DID 列表
        tags: 标签列表

    Example:
        @uap_capability(
            capability_id="yijing.interpret",
            name="卦象解读",
            access_tier=AccessTier.AUTHENTICATED,
            avg_latency_ms=2000,
        )
        async def interpret(self, hexagram: str, question: str) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        rate_limit = (
            RateLimit(requests_per_minute=rate_limit_rpm) if rate_limit_rpm else None
        )
        capability = Capability(
            id=capability_id,
            name=name,
            description=description,
            version=version,
            access_tier=access_tier,
            rate_limit=rate_limit,
            avg_latency_ms=avg_latency_ms,
            required_agents=required_agents or [],
            tags=tags or [],
        )
        # 将能力元数据挂到函数上，供 @uap_agent 扫描
        func._uap_capability = capability

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)

        wrapper._uap_capability = capability
        return wrapper

    return decorator


def get_registry() -> dict[str, AgentRegistration]:
    """获取全局 Agent 注册表"""
    return _AGENT_REGISTRY


def get_agent(did: str) -> Optional[AgentRegistration]:
    """按 DID 获取注册的 Agent"""
    return _AGENT_REGISTRY.get(did)
