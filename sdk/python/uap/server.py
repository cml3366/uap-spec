"""
uap.server — UAP FastAPI 服务端 Mixin
把标准 UAP 端点自动注册到 FastAPI 应用

Usage:
    from fastapi import FastAPI
    from uap.server import UAPServer
    from uap.decorators import get_agent

    app = FastAPI()
    registration = get_agent("did:uap:openwen:yijing-agent")
    uap = UAPServer(app, registration)
    uap.mount()  # 注册所有 UAP 标准端点
"""

from __future__ import annotations
import time
import logging
from typing import Any, Optional

logger = logging.getLogger("uap.server")

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


class UAPServer:
    """
    UAP 标准端点 FastAPI 挂载器

    自动注册以下端点：
        GET  /.well-known/uap         能力清单（无需鉴权）
        GET  /uap/health              健康检查
        POST /uap/invoke              能力调用
        GET  /uap/status/{task_id}    异步任务状态（预留）

    Args:
        app: FastAPI 应用实例
        registration: 通过 @uap_agent 注册的 AgentRegistration 对象
        prefix: 路由前缀（默认无前缀）
        auth_validator: 可选的 token 校验函数 (token: str) -> bool

    Example:
        app = FastAPI(title="OpenWen Yijing Agent")
        reg = get_agent("did:uap:openwen:yijing-agent")
        uap = UAPServer(app, reg)
        uap.mount()
    """

    def __init__(
        self,
        app,
        registration,
        prefix: str = "",
        auth_validator=None,
    ):
        if not _FASTAPI_AVAILABLE:
            raise ImportError(
                "fastapi is required for UAPServer. "
                "Install with: pip install fastapi uvicorn"
            )
        self.app = app
        self.reg = registration
        self.prefix = prefix.rstrip("/")
        self.auth_validator = auth_validator or (lambda token: True)

    def mount(self):
        """注册所有 UAP 标准端点"""
        self._mount_well_known()
        self._mount_health()
        self._mount_invoke()
        logger.info(
            f"UAP endpoints mounted for {self.reg.did}\n"
            f"  GET  {self.prefix}/.well-known/uap\n"
            f"  GET  {self.prefix}/uap/health\n"
            f"  POST {self.prefix}/uap/invoke"
        )

    def _mount_well_known(self):
        path = self.prefix + "/.well-known/uap"

        @self.app.get(path, tags=["UAP"])
        async def well_known():
            """UAP 能力清单（无需鉴权）"""
            manifest = self.reg.to_manifest()
            return JSONResponse(content=manifest.to_dict())

    def _mount_health(self):
        path = self.prefix + "/uap/health"

        @self.app.get(path, tags=["UAP"])
        async def health():
            """UAP 健康检查"""
            return {
                "status": "ok",
                "agent": str(self.reg.did),
                "capabilities": len(self.reg.capabilities),
            }

    def _mount_invoke(self):
        path = self.prefix + "/uap/invoke"

        @self.app.post(path, tags=["UAP"])
        async def invoke(request: Request):
            """UAP 能力调用"""
            start_ms = int(time.time() * 1000)
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON body")

            # 提取路由和意图信息
            routing = body.get("routing", {})
            intent = body.get("intent", {})
            auth = body.get("auth", {})
            meta = body.get("envelope", {})

            capability_id = intent.get("capability")
            access_tier = routing.get("access_tier", "authenticated")
            trace_id = meta.get("trace_id", "unknown")
            message_id = meta.get("message_id", "unknown")

            logger.info(f"[{trace_id[:8]}] invoke: {capability_id}")

            # 鉴权检查（开放层跳过）
            if access_tier != "open":
                token = auth.get("capability_token")
                if not token or not self.auth_validator(token):
                    return JSONResponse(
                        status_code=401,
                        content={
                            "uap_version": "1.0",
                            "envelope": {"message_id": "resp-" + message_id, "request_id": message_id, "trace_id": trace_id},
                            "status": {"code": 401, "message": "Authentication required"},
                            "error": {"type": "AuthError", "detail": "Valid capability_token required"},
                        },
                    )

            # 能力检查
            if not capability_id:
                return _error_response(message_id, trace_id, 400, "Missing capability in intent")

            handler = self.reg.handlers.get(capability_id)
            if not handler:
                available = list(self.reg.handlers.keys())
                return JSONResponse(
                    status_code=200,
                    content={
                        "uap_version": "1.0",
                        "envelope": {"message_id": "resp-" + message_id, "request_id": message_id, "trace_id": trace_id},
                        "status": {"code": 800, "message": "Capability Not Found"},
                        "error": {
                            "type": "CapabilityNotFoundError",
                            "detail": f"'{capability_id}' is not registered",
                            "available_capabilities": available,
                        },
                    },
                )

            # 执行能力
            try:
                import inspect
                input_data = intent.get("input", {})
                if inspect.iscoroutinefunction(handler):
                    result = await handler(**input_data)
                else:
                    result = handler(**input_data)

                elapsed_ms = int(time.time() * 1000) - start_ms
                return JSONResponse(
                    content={
                        "uap_version": "1.0",
                        "envelope": {
                            "message_id": "resp-" + message_id,
                            "request_id": message_id,
                            "trace_id": trace_id,
                        },
                        "status": {
                            "code": 200,
                            "message": "success",
                            "execution_ms": elapsed_ms,
                        },
                        "result": {
                            "capability": capability_id,
                            "output": result,
                            "metadata": {"agent": str(self.reg.did)},
                        },
                    }
                )
            except TypeError as e:
                return _error_response(message_id, trace_id, 400, f"Invalid input parameters: {e}")
            except Exception as e:
                logger.exception(f"Capability execution error: {capability_id}")
                return _error_response(message_id, trace_id, 500, f"Agent internal error: {type(e).__name__}")


def _error_response(message_id: str, trace_id: str, code: int, detail: str) -> "JSONResponse":
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=200,
        content={
            "uap_version": "1.0",
            "envelope": {"message_id": "resp-" + message_id, "request_id": message_id, "trace_id": trace_id},
            "status": {"code": code, "message": detail},
            "error": {"type": "UAPError", "detail": detail},
        },
    )
