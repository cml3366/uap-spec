"""
uap.envelope — UAP 消息信封
所有 UAP 消息使用统一信封格式，包含路由、鉴权、意图三层信息
"""

from __future__ import annotations
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .identity import AgentDID
from .intent import Intent

# 接入层级
class AccessTier:
    OPEN = "open"
    AUTHENTICATED = "authenticated"
    PRIVATE = "private"


@dataclass
class EnvelopeMeta:
    """消息元信息 — 唯一ID、时间戳、链路追踪"""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = 30  # 秒
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    def __post_init__(self):
        if self.trace_id is None:
            self.trace_id = str(uuid.uuid4())
        if self.span_id is None:
            self.span_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }
        if self.parent_span_id:
            d["parent_span_id"] = self.parent_span_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EnvelopeMeta":
        return cls(
            message_id=data["message_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl=data.get("ttl", 30),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            parent_span_id=data.get("parent_span_id"),
        )


@dataclass
class Routing:
    """消息路由信息"""

    from_did: AgentDID
    to_did: AgentDID
    access_tier: str = AccessTier.AUTHENTICATED
    reply_to: Optional[AgentDID] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "from": str(self.from_did),
            "to": str(self.to_did),
            "access_tier": self.access_tier,
        }
        if self.reply_to:
            d["reply_to"] = str(self.reply_to)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Routing":
        return cls(
            from_did=AgentDID.parse(data["from"]),
            to_did=AgentDID.parse(data["to"]),
            access_tier=data.get("access_tier", AccessTier.AUTHENTICATED),
            reply_to=AgentDID.parse(data["reply_to"]) if data.get("reply_to") else None,
        )


@dataclass
class Auth:
    """鉴权信息 — 鉴权层和私有层必须提供"""

    capability_token: Optional[str] = None
    signature: Optional[str] = None
    nonce: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {}
        if self.capability_token:
            d["capability_token"] = self.capability_token
        if self.signature:
            d["signature"] = self.signature
        if self.nonce:
            d["nonce"] = self.nonce
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Auth":
        return cls(
            capability_token=data.get("capability_token"),
            signature=data.get("signature"),
            nonce=data.get("nonce"),
        )


@dataclass
class UAPMessage:
    """
    UAP 完整消息信封

    Examples:
        >>> from uap.identity import AgentDID
        >>> from uap.intent import Intent, Depth
        >>>
        >>> msg = UAPMessage.create(
        ...     from_did=AgentDID.parse("did:uap:personal:user-maolin"),
        ...     to_did=AgentDID.parse("did:uap:openwen:yijing-agent"),
        ...     intent=Intent.invoke(
        ...         capability="yijing.interpret",
        ...         input={"hexagram": "乾卦", "question": "事业方向"},
        ...         depth=Depth.SCHOLARLY,
        ...     ),
        ...     capability_token="eyJ...",
        ... )
        >>> print(msg.to_json())
    """

    meta: EnvelopeMeta
    routing: Routing
    intent: Intent
    auth: Auth = field(default_factory=Auth)
    uap_version: str = "1.0"

    # ── 工厂方法 ──────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        from_did: AgentDID,
        to_did: AgentDID,
        intent: Intent,
        access_tier: str = AccessTier.AUTHENTICATED,
        capability_token: Optional[str] = None,
        reply_to: Optional[AgentDID] = None,
        trace_id: Optional[str] = None,
        ttl: int = 30,
    ) -> "UAPMessage":
        meta = EnvelopeMeta(ttl=ttl, trace_id=trace_id)
        routing = Routing(
            from_did=from_did,
            to_did=to_did,
            access_tier=access_tier,
            reply_to=reply_to,
        )
        auth = Auth(capability_token=capability_token)
        return cls(meta=meta, routing=routing, intent=intent, auth=auth)

    # ── 序列化 ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "uap_version": self.uap_version,
            "envelope": self.meta.to_dict(),
            "routing": self.routing.to_dict(),
            "intent": self.intent.to_dict(),
        }
        auth_dict = self.auth.to_dict()
        if auth_dict:
            d["auth"] = auth_dict
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "UAPMessage":
        return cls(
            uap_version=data.get("uap_version", "1.0"),
            meta=EnvelopeMeta.from_dict(data["envelope"]),
            routing=Routing.from_dict(data["routing"]),
            intent=Intent.from_dict(data["intent"]),
            auth=Auth.from_dict(data.get("auth", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "UAPMessage":
        return cls.from_dict(json.loads(json_str))

    # ── 属性快捷访问 ──────────────────────────────────────────

    @property
    def trace_id(self) -> str:
        return self.meta.trace_id or ""

    @property
    def message_id(self) -> str:
        return self.meta.message_id

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.meta.timestamp).total_seconds()
        return elapsed > self.meta.ttl


@dataclass
class UAPResponse:
    """
    UAP 响应信封

    Examples:
        >>> response = UAPResponse.success(
        ...     request=msg,
        ...     output={"interpretation": "乾为天，健也..."},
        ...     execution_ms=1842,
        ... )
    """

    request_id: str
    trace_id: str
    status_code: int
    status_message: str
    result: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    execution_ms: Optional[int] = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uap_version: str = "1.0"

    @classmethod
    def success(
        cls,
        request: UAPMessage,
        output: dict[str, Any],
        execution_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> "UAPResponse":
        return cls(
            request_id=request.message_id,
            trace_id=request.trace_id,
            status_code=200,
            status_message="success",
            result={
                "capability": request.intent.capability,
                "output": output,
                "metadata": metadata or {},
            },
            execution_ms=execution_ms,
        )

    @classmethod
    def error(
        cls,
        request: UAPMessage,
        code: int,
        message: str,
        detail: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> "UAPResponse":
        return cls(
            request_id=request.message_id,
            trace_id=request.trace_id,
            status_code=code,
            status_message=message,
            error={
                "type": error_type or "UAPError",
                "detail": detail or message,
            },
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "uap_version": self.uap_version,
            "envelope": {
                "message_id": self.message_id,
                "request_id": self.request_id,
                "timestamp": self.timestamp.isoformat(),
                "trace_id": self.trace_id,
            },
            "status": {
                "code": self.status_code,
                "message": self.status_message,
            },
        }
        if self.execution_ms is not None:
            d["status"]["execution_ms"] = self.execution_ms
        if self.result is not None:
            d["result"] = self.result
        if self.error is not None:
            d["error"] = self.error
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @property
    def ok(self) -> bool:
        return self.status_code == 200

    @property
    def output(self) -> Optional[dict]:
        return self.result.get("output") if self.result else None
