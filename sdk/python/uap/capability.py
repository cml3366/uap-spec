"""
uap.capability — 能力声明系统
Agent 通过能力清单对外声明可调用的功能单元
暴露于 /.well-known/uap 端点
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Optional, Any

from .identity import AgentDID
from .envelope import AccessTier


@dataclass
class RateLimit:
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None

    def to_dict(self) -> dict:
        d = {}
        if self.requests_per_minute:
            d["requests_per_minute"] = self.requests_per_minute
        if self.requests_per_day:
            d["requests_per_day"] = self.requests_per_day
        return d


@dataclass
class Capability:
    """
    单个能力声明

    Examples:
        >>> cap = Capability(
        ...     id="yijing.interpret",
        ...     name="卦象解读",
        ...     description="六十四卦深度义理解读",
        ...     version="1.0.0",
        ...     access_tier=AccessTier.AUTHENTICATED,
        ...     avg_latency_ms=2000,
        ... )
    """

    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    access_tier: str = AccessTier.AUTHENTICATED
    rate_limit: Optional[RateLimit] = None
    avg_latency_ms: Optional[int] = None
    required_agents: list[str] = field(default_factory=list)
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    deprecated: bool = False
    deprecated_message: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        # 能力 ID 格式: domain.name 或 domain.sub.name
        import re
        if not re.match(r"^[a-z][a-z0-9]*\.[a-z][a-z0-9._]*$", self.id):
            raise ValueError(
                f"Invalid capability id: {self.id!r}\n"
                f"Expected format: domain.capability_name (e.g. yijing.interpret)"
            )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "access_tier": self.access_tier,
        }
        if self.description:
            d["description"] = self.description
        if self.rate_limit:
            d["rate_limit"] = self.rate_limit.to_dict()
        if self.avg_latency_ms:
            d["avg_latency_ms"] = self.avg_latency_ms
        if self.required_agents:
            d["required_agents"] = self.required_agents
        if self.deprecated:
            d["deprecated"] = True
            if self.deprecated_message:
                d["deprecated_message"] = self.deprecated_message
        if self.tags:
            d["tags"] = self.tags
        return d


@dataclass
class CapabilityManifest:
    """
    Agent 能力清单 — 完整的 /.well-known/uap 响应

    Examples:
        >>> manifest = CapabilityManifest(
        ...     did=AgentDID.parse("did:uap:openwen:yijing-agent"),
        ...     name="易经解析 Agent",
        ...     version="1.2.0",
        ...     endpoint="https://api.openwen.io/agents/yijing",
        ...     capabilities=[
        ...         Capability(id="yijing.interpret", name="卦象解读"),
        ...         Capability(
        ...             id="yijing.search", name="典籍检索",
        ...             access_tier=AccessTier.OPEN,
        ...         ),
        ...     ],
        ... )
        >>> print(manifest.to_json())
    """

    did: AgentDID
    name: str
    version: str
    endpoint: str
    capabilities: list[Capability]
    description: Optional[str] = None
    access_tier: str = AccessTier.AUTHENTICATED
    icon_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    public_key: Optional[str] = None
    uap_version: str = "1.0"

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "uap_version": self.uap_version,
            "agent": {
                "did": str(self.did),
                "name": self.name,
                "version": self.version,
                "access_tier": self.access_tier,
                "endpoint": self.endpoint,
            },
            "capabilities": [cap.to_dict() for cap in self.capabilities],
        }
        if self.description:
            d["agent"]["description"] = self.description
        if self.icon_url:
            d["agent"]["icon_url"] = self.icon_url
        if self.tags:
            d["agent"]["tags"] = self.tags
        if self.public_key:
            d["trust"] = {"public_key": self.public_key}
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """按 ID 查找能力"""
        return next(
            (cap for cap in self.capabilities if cap.id == capability_id), None
        )

    def list_open_capabilities(self) -> list[Capability]:
        """列出所有开放层能力"""
        return [cap for cap in self.capabilities if cap.access_tier == AccessTier.OPEN]

    @classmethod
    def from_dict(cls, data: dict) -> "CapabilityManifest":
        agent = data["agent"]
        caps = [
            Capability(
                id=c["id"],
                name=c["name"],
                version=c.get("version", "1.0.0"),
                description=c.get("description"),
                access_tier=c.get("access_tier", AccessTier.AUTHENTICATED),
                avg_latency_ms=c.get("avg_latency_ms"),
                required_agents=c.get("required_agents", []),
                deprecated=c.get("deprecated", False),
            )
            for c in data.get("capabilities", [])
        ]
        return cls(
            did=AgentDID.parse(agent["did"]),
            name=agent["name"],
            version=agent["version"],
            endpoint=agent["endpoint"],
            access_tier=agent.get("access_tier", AccessTier.AUTHENTICATED),
            description=agent.get("description"),
            tags=agent.get("tags", []),
            capabilities=caps,
            public_key=data.get("trust", {}).get("public_key"),
        )
