"""
uap.client — UAP HTTP 调用客户端
封装 UAP 协议的完整请求/响应流程
"""

from __future__ import annotations
import time
import json
import logging
from typing import Any, Optional

from .identity import AgentDID
from .intent import Intent, Depth, ResponseFormat
from .envelope import UAPMessage, UAPResponse, AccessTier
from .capability import CapabilityManifest

logger = logging.getLogger("uap.client")


class UAPClientError(Exception):
    """UAP 客户端异常基类"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class CapabilityNotFoundError(UAPClientError):
    pass


class AuthError(UAPClientError):
    pass


class UAPClient:
    """
    UAP 调用客户端

    Examples:
        >>> async with UAPClient(
        ...     caller_did=AgentDID.parse("did:uap:personal:user-maolin"),
        ...     capability_token="eyJ...",
        ... ) as client:
        ...
        ...     # 发现目标 Agent 的能力
        ...     manifest = await client.discover("https://api.openwen.io/agents/yijing")
        ...
        ...     # 调用易经解读
        ...     response = await client.invoke(
        ...         target_did=AgentDID.parse("did:uap:openwen:yijing-agent"),
        ...         endpoint="https://api.openwen.io/agents/yijing",
        ...         capability="yijing.interpret",
        ...         input={"hexagram": "乾卦", "question": "事业方向"},
        ...         depth=Depth.SCHOLARLY,
        ...     )
        ...     print(response.output)
    """

    def __init__(
        self,
        caller_did: AgentDID,
        capability_token: Optional[str] = None,
        access_tier: str = AccessTier.AUTHENTICATED,
        timeout: int = 30,
        http_client=None,
    ):
        self.caller_did = caller_did
        self.capability_token = capability_token
        self.access_tier = access_tier
        self.timeout = timeout
        self._http = http_client  # 注入 httpx.AsyncClient 或 requests.Session
        self._owns_client = http_client is None

    async def __aenter__(self) -> "UAPClient":
        if self._owns_client:
            try:
                import httpx
                self._http = httpx.AsyncClient(timeout=self.timeout)
            except ImportError:
                raise ImportError(
                    "httpx is required for async UAPClient. "
                    "Install with: pip install httpx"
                )
        return self

    async def __aexit__(self, *args):
        if self._owns_client and self._http:
            await self._http.aclose()

    async def discover(self, endpoint: str) -> CapabilityManifest:
        """
        发现 Agent 能力清单（无需鉴权）
        GET {endpoint}/.well-known/uap
        """
        well_known_url = endpoint.rstrip("/") + "/.well-known/uap"
        logger.debug(f"Discovering capabilities at {well_known_url}")

        resp = await self._http.get(well_known_url)
        resp.raise_for_status()
        data = resp.json()
        return CapabilityManifest.from_dict(data)

    async def invoke(
        self,
        target_did: AgentDID,
        endpoint: str,
        capability: str,
        input: Optional[dict[str, Any]] = None,
        version: str = "^1.0",
        depth: Depth = Depth.STANDARD,
        language: str = "zh-CN",
        response_format: ResponseFormat = ResponseFormat.STRUCTURED,
        extensions: Optional[dict] = None,
    ) -> UAPResponse:
        """
        调用目标 Agent 的指定能力

        Args:
            target_did: 目标 Agent 的 DID
            endpoint: 目标 Agent 的 HTTP 端点
            capability: 能力 ID，如 "yijing.interpret"
            input: 能力输入参数
            version: 能力版本约束
            depth: 分析深度
            language: 响应语言
            response_format: 响应格式
            extensions: 命名空间扩展字段

        Returns:
            UAPResponse 对象，通过 .output 访问结果
        """
        intent = Intent.invoke(
            capability=capability,
            input=input or {},
            version=version,
            depth=depth,
            language=language,
            response_format=response_format,
            extensions=extensions,
        )
        message = UAPMessage.create(
            from_did=self.caller_did,
            to_did=target_did,
            intent=intent,
            access_tier=self.access_tier,
            capability_token=self.capability_token,
        )

        invoke_url = endpoint.rstrip("/") + "/uap/invoke"
        logger.debug(
            f"Invoking {capability} on {target_did} "
            f"[trace={message.trace_id[:8]}]"
        )

        start_ms = int(time.time() * 1000)
        resp = await self._http.post(
            invoke_url,
            json=message.to_dict(),
            headers={
                "Content-Type": "application/json",
                "X-UAP-Version": "1.0",
                "X-Trace-Id": message.trace_id,
            },
        )
        elapsed_ms = int(time.time() * 1000) - start_ms

        if resp.status_code == 401:
            raise AuthError("Authentication required", status_code=401)
        if resp.status_code == 800:
            raise CapabilityNotFoundError(
                f"Capability '{capability}' not found", status_code=800
            )

        resp.raise_for_status()
        response_data = resp.json()
        uap_resp = UAPResponse(
            request_id=message.message_id,
            trace_id=message.trace_id,
            status_code=response_data.get("status", {}).get("code", 200),
            status_message=response_data.get("status", {}).get("message", ""),
            result=response_data.get("result"),
            error=response_data.get("error"),
            execution_ms=elapsed_ms,
        )

        logger.info(
            f"[{message.trace_id[:8]}] {capability} → "
            f"{uap_resp.status_code} ({elapsed_ms}ms)"
        )
        return uap_resp

    async def check_health(self, endpoint: str) -> bool:
        """健康检查"""
        try:
            resp = await self._http.get(endpoint.rstrip("/") + "/uap/health")
            return resp.status_code == 200
        except Exception:
            return False
