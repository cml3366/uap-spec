"""
uap.identity — AgentDID 身份体系
每个 Agent/设备/人拥有唯一的去中心化标识符
格式: did:uap:<namespace>:<agent-id>[:<sub>]
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

# did:uap:namespace:agent-id 或 did:uap:namespace:agent-id:sub
_DID_PATTERN = re.compile(r"^did:uap:[a-z0-9-]+:[a-z0-9-]+(:[a-z0-9-]+)?$")


@dataclass
class AgentDID:
    """
    UAP Agent 去中心化身份标识符

    Examples:
        >>> did = AgentDID("openwen", "yijing-agent")
        >>> str(did)
        'did:uap:openwen:yijing-agent'

        >>> did = AgentDID.parse("did:uap:openwen:yijing-agent")
    """

    namespace: str
    agent_id: str
    sub: Optional[str] = None

    def __post_init__(self):
        if not re.match(r"^[a-z0-9-]+$", self.namespace):
            raise ValueError(f"Invalid namespace: {self.namespace!r}")
        if not re.match(r"^[a-z0-9-]+$", self.agent_id):
            raise ValueError(f"Invalid agent_id: {self.agent_id!r}")
        if self.sub and not re.match(r"^[a-z0-9-]+$", self.sub):
            raise ValueError(f"Invalid sub: {self.sub!r}")

    def __str__(self) -> str:
        base = f"did:uap:{self.namespace}:{self.agent_id}"
        return f"{base}:{self.sub}" if self.sub else base

    def __repr__(self) -> str:
        return f"AgentDID({str(self)!r})"

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    @classmethod
    def parse(cls, did_string: str) -> "AgentDID":
        """从字符串解析 AgentDID"""
        if not _DID_PATTERN.match(did_string):
            raise ValueError(
                f"Invalid AgentDID format: {did_string!r}\n"
                f"Expected: did:uap:<namespace>:<agent-id>[:<sub>]"
            )
        parts = did_string.split(":")
        # parts = ["did", "uap", namespace, agent_id, (sub)?]
        namespace = parts[2]
        agent_id = parts[3]
        sub = parts[4] if len(parts) > 4 else None
        return cls(namespace=namespace, agent_id=agent_id, sub=sub)

    def with_sub(self, sub: str) -> "AgentDID":
        """生成带子路径的 DID"""
        return AgentDID(self.namespace, self.agent_id, sub)


@dataclass
class DIDDocument:
    """
    AgentDID 文档 — 描述 Agent 的端点、公钥、能力等元信息
    暴露于 /.well-known/uap 的扩展字段
    """

    did: AgentDID
    endpoint: str
    public_key: Optional[str] = None
    controller: Optional[AgentDID] = None
    transport_protocols: list[str] = field(default_factory=lambda: ["http2", "websocket"])
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://uap-spec.io/context/v1",
            ],
            "id": str(self.did),
            "created": self.created.isoformat(),
            "updated": (self.updated or self.created).isoformat(),
            "controller": str(self.controller) if self.controller else None,
            "service": [
                {
                    "id": "#uap-endpoint",
                    "type": "UAPEndpoint",
                    "serviceEndpoint": self.endpoint,
                    "transportProtocols": self.transport_protocols,
                }
            ],
            "verificationMethod": (
                [
                    {
                        "id": "#key-1",
                        "type": "Ed25519VerificationKey2020",
                        "publicKeyMultibase": self.public_key,
                    }
                ]
                if self.public_key
                else []
            ),
            "authentication": ["#key-1"] if self.public_key else [],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "DIDDocument":
        did = AgentDID.parse(data["id"])
        endpoint = data["service"][0]["serviceEndpoint"]
        public_key = None
        if data.get("verificationMethod"):
            public_key = data["verificationMethod"][0].get("publicKeyMultibase")
        controller = (
            AgentDID.parse(data["controller"]) if data.get("controller") else None
        )
        return cls(
            did=did,
            endpoint=endpoint,
            public_key=public_key,
            controller=controller,
        )
