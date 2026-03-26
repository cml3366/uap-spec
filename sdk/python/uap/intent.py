"""
uap.intent — 意图类型系统
UAP 定义的标准意图类型，实现跨框架语义互通
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional


class IntentType(str, Enum):
    """UAP 标准意图类型"""

    # 能力操作
    CAPABILITY_INVOKE = "capability.invoke"
    CAPABILITY_DISCOVER = "capability.discover"
    CAPABILITY_NEGOTIATE = "capability.negotiate"

    # 任务管理
    TASK_DELEGATE = "task.delegate"
    TASK_STATUS = "task.status"
    TASK_CANCEL = "task.cancel"

    # 会话管理
    SESSION_OPEN = "session.open"
    SESSION_CLOSE = "session.close"

    # 事件
    EVENT_SUBSCRIBE = "event.subscribe"
    EVENT_PUBLISH = "event.publish"


class ResponseFormat(str, Enum):
    STRUCTURED = "structured"
    TEXT = "text"
    STREAM = "stream"


class Depth(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    SCHOLARLY = "scholarly"


@dataclass
class IntentOptions:
    """意图调用选项"""

    response_format: ResponseFormat = ResponseFormat.STRUCTURED
    language: str = "zh-CN"
    depth: Depth = Depth.STANDARD
    async_mode: bool = False

    def to_dict(self) -> dict:
        return {
            "response_format": self.response_format.value,
            "language": self.language,
            "depth": self.depth.value,
            "async": self.async_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntentOptions":
        return cls(
            response_format=ResponseFormat(data.get("response_format", "structured")),
            language=data.get("language", "zh-CN"),
            depth=Depth(data.get("depth", "standard")),
            async_mode=data.get("async", False),
        )


@dataclass
class Intent:
    """
    UAP 结构化意图

    Examples:
        >>> intent = Intent.invoke(
        ...     capability="yijing.interpret",
        ...     input={"hexagram": "乾卦", "question": "事业方向"},
        ...     depth=Depth.SCHOLARLY,
        ... )
    """

    type: IntentType
    capability: Optional[str] = None
    version: Optional[str] = None
    input: Optional[dict[str, Any]] = None
    options: IntentOptions = field(default_factory=IntentOptions)
    extensions: dict[str, Any] = field(default_factory=dict)

    # 额外字段（task/session 用）
    task_id: Optional[str] = None
    session_id: Optional[str] = None

    # ── 工厂方法 ──────────────────────────────────────────────

    @classmethod
    def invoke(
        cls,
        capability: str,
        input: Optional[dict] = None,
        version: str = "^1.0",
        depth: Depth = Depth.STANDARD,
        language: str = "zh-CN",
        response_format: ResponseFormat = ResponseFormat.STRUCTURED,
        extensions: Optional[dict] = None,
    ) -> "Intent":
        """创建能力调用意图（最常用）"""
        return cls(
            type=IntentType.CAPABILITY_INVOKE,
            capability=capability,
            version=version,
            input=input or {},
            options=IntentOptions(
                depth=depth,
                language=language,
                response_format=response_format,
            ),
            extensions=extensions or {},
        )

    @classmethod
    def discover(cls) -> "Intent":
        """发现 Agent 所有可用能力"""
        return cls(type=IntentType.CAPABILITY_DISCOVER)

    @classmethod
    def task_status(cls, task_id: str) -> "Intent":
        """查询异步任务状态"""
        return cls(type=IntentType.TASK_STATUS, task_id=task_id)

    @classmethod
    def task_cancel(cls, task_id: str) -> "Intent":
        """取消异步任务"""
        return cls(type=IntentType.TASK_CANCEL, task_id=task_id)

    # ── 序列化 ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type.value}
        if self.capability:
            d["capability"] = self.capability
        if self.version:
            d["version"] = self.version
        if self.input is not None:
            d["input"] = self.input
        if self.task_id:
            d["task_id"] = self.task_id
        if self.session_id:
            d["session_id"] = self.session_id
        d["options"] = self.options.to_dict()
        if self.extensions:
            d["extensions"] = self.extensions
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Intent":
        return cls(
            type=IntentType(data["type"]),
            capability=data.get("capability"),
            version=data.get("version"),
            input=data.get("input"),
            options=IntentOptions.from_dict(data.get("options", {})),
            extensions=data.get("extensions", {}),
            task_id=data.get("task_id"),
            session_id=data.get("session_id"),
        )
