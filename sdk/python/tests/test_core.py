"""
tests/test_core.py — UAP SDK 核心单元测试
"""

import pytest
import json
from uap import (
    AgentDID,
    UAPMessage,
    UAPResponse,
    Intent,
    IntentType,
    Depth,
    AccessTier,
    Capability,
    CapabilityManifest,
)


# ─────────────────────────────────────────────────────────────
# AgentDID 测试
# ─────────────────────────────────────────────────────────────

class TestAgentDID:

    def test_create(self):
        did = AgentDID("openwen", "yijing-agent")
        assert str(did) == "did:uap:openwen:yijing-agent"

    def test_parse(self):
        did = AgentDID.parse("did:uap:openwen:yijing-agent")
        assert did.namespace == "openwen"
        assert did.agent_id == "yijing-agent"
        assert did.sub is None

    def test_parse_with_sub(self):
        did = AgentDID.parse("did:uap:personal:alice:home")
        assert did.namespace == "personal"
        assert did.agent_id == "alice"
        assert did.sub == "home"
        assert str(did) == "did:uap:personal:alice:home"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            AgentDID.parse("invalid-did")

    def test_invalid_namespace_raises(self):
        with pytest.raises(ValueError):
            AgentDID("Open_Wen", "agent")  # 大写不允许

    def test_equality(self):
        a = AgentDID.parse("did:uap:openwen:yijing-agent")
        b = AgentDID.parse("did:uap:openwen:yijing-agent")
        assert a == b

    def test_with_sub(self):
        did = AgentDID.parse("did:uap:openwen:yijing-agent")
        sub_did = did.with_sub("callback")
        assert str(sub_did) == "did:uap:openwen:yijing-agent:callback"


# ─────────────────────────────────────────────────────────────
# Intent 测试
# ─────────────────────────────────────────────────────────────

class TestIntent:

    def test_invoke_factory(self):
        intent = Intent.invoke(
            capability="yijing.interpret",
            input={"hexagram": "乾卦", "question": "事业方向"},
            depth=Depth.SCHOLARLY,
        )
        assert intent.type == IntentType.CAPABILITY_INVOKE
        assert intent.capability == "yijing.interpret"
        assert intent.input["hexagram"] == "乾卦"
        assert intent.options.depth == Depth.SCHOLARLY

    def test_discover_factory(self):
        intent = Intent.discover()
        assert intent.type == IntentType.CAPABILITY_DISCOVER

    def test_serialization_roundtrip(self):
        original = Intent.invoke(
            capability="yijing.interpret",
            input={"hexagram": "坤卦"},
        )
        restored = Intent.from_dict(original.to_dict())
        assert restored.type == original.type
        assert restored.capability == original.capability
        assert restored.input == original.input


# ─────────────────────────────────────────────────────────────
# UAPMessage 测试
# ─────────────────────────────────────────────────────────────

class TestUAPMessage:

    def setup_method(self):
        self.caller = AgentDID.parse("did:uap:personal:user-maolin")
        self.target = AgentDID.parse("did:uap:openwen:yijing-agent")
        self.intent = Intent.invoke(
            capability="yijing.interpret",
            input={"hexagram": "乾卦", "question": "事业"},
        )

    def test_create(self):
        msg = UAPMessage.create(
            from_did=self.caller,
            to_did=self.target,
            intent=self.intent,
            capability_token="test-token",
        )
        assert msg.uap_version == "1.0"
        assert msg.routing.from_did == self.caller
        assert msg.routing.to_did == self.target
        assert msg.auth.capability_token == "test-token"

    def test_to_dict_structure(self):
        msg = UAPMessage.create(
            from_did=self.caller,
            to_did=self.target,
            intent=self.intent,
        )
        d = msg.to_dict()
        assert "uap_version" in d
        assert "envelope" in d
        assert "routing" in d
        assert "intent" in d
        assert d["routing"]["from"] == "did:uap:personal:user-maolin"
        assert d["routing"]["to"] == "did:uap:openwen:yijing-agent"

    def test_json_roundtrip(self):
        msg = UAPMessage.create(
            from_did=self.caller,
            to_did=self.target,
            intent=self.intent,
        )
        json_str = msg.to_json()
        restored = UAPMessage.from_json(json_str)
        assert restored.routing.from_did == msg.routing.from_did
        assert restored.intent.capability == msg.intent.capability
        assert restored.trace_id == msg.trace_id

    def test_not_expired(self):
        msg = UAPMessage.create(
            from_did=self.caller,
            to_did=self.target,
            intent=self.intent,
            ttl=30,
        )
        assert not msg.is_expired


# ─────────────────────────────────────────────────────────────
# Capability 测试
# ─────────────────────────────────────────────────────────────

class TestCapability:

    def test_valid_id(self):
        cap = Capability(id="yijing.interpret", name="卦象解读", version="1.0.0")
        assert cap.id == "yijing.interpret"

    def test_invalid_id_raises(self):
        with pytest.raises(ValueError):
            Capability(id="InvalidFormat", name="Test", version="1.0.0")

    def test_to_dict(self):
        cap = Capability(
            id="yijing.interpret",
            name="卦象解读",
            description="深度解读",
            version="1.0.0",
            access_tier=AccessTier.AUTHENTICATED,
        )
        d = cap.to_dict()
        assert d["id"] == "yijing.interpret"
        assert d["access_tier"] == "authenticated"


# ─────────────────────────────────────────────────────────────
# UAPResponse 测试
# ─────────────────────────────────────────────────────────────

class TestUAPResponse:

    def test_success_response(self):
        caller = AgentDID.parse("did:uap:personal:user")
        target = AgentDID.parse("did:uap:openwen:yijing-agent")
        intent = Intent.invoke("yijing.interpret", {"hexagram": "乾卦"})
        msg = UAPMessage.create(from_did=caller, to_did=target, intent=intent)

        resp = UAPResponse.success(
            request=msg,
            output={"interpretation": "乾为天，健也"},
            execution_ms=1500,
        )
        assert resp.ok
        assert resp.status_code == 200
        assert resp.output["interpretation"] == "乾为天，健也"
        assert resp.execution_ms == 1500

    def test_error_response(self):
        caller = AgentDID.parse("did:uap:personal:user")
        target = AgentDID.parse("did:uap:openwen:yijing-agent")
        intent = Intent.invoke("unknown.cap")
        msg = UAPMessage.create(from_did=caller, to_did=target, intent=intent)

        resp = UAPResponse.error(msg, 800, "Capability Not Found")
        assert not resp.ok
        assert resp.status_code == 800


# ─────────────────────────────────────────────────────────────
# 装饰器测试
# ─────────────────────────────────────────────────────────────

class TestDecorators:

    def test_uap_agent_decorator(self):
        from uap.decorators import uap_agent, uap_capability, get_agent

        @uap_agent(
            did="did:uap:test:demo-agent",
            name="Demo Agent",
            version="1.0.0",
            endpoint="http://localhost:9999",
        )
        class DemoAgent:

            @uap_capability(capability_id="demo.hello", name="打招呼")
            async def hello(self, name: str = "World") -> dict:
                return {"message": f"Hello, {name}!"}

        reg = get_agent("did:uap:test:demo-agent")
        assert reg is not None
        assert reg.name == "Demo Agent"
        assert "demo.hello" in reg.handlers

        manifest = reg.to_manifest()
        assert len(manifest.capabilities) == 1
        assert manifest.capabilities[0].id == "demo.hello"

    @pytest.mark.asyncio
    async def test_dispatch(self):
        from uap.decorators import get_agent

        reg = get_agent("did:uap:test:demo-agent")
        if reg:
            # 创建实例并绑定调用
            from tests.test_core import TestDecorators
            # 直接实例化 DemoAgent（需要重新注册）
            from uap.decorators import uap_agent, uap_capability
            @uap_agent(did="did:uap:test:demo2", name="Demo2", version="1.0.0", endpoint="http://localhost")
            class Demo2:
                @uap_capability(capability_id="demo2.hello", name="hello")
                async def hello(self, name: str = "World") -> dict:
                    return {"message": f"Hello, {name}!"}
            reg2 = get_agent("did:uap:test:demo2")
            instance = Demo2()
            result = await reg2.dispatch("demo2.hello", {"name": "UAP"}, agent_instance=instance)
            assert result["message"] == "Hello, UAP!"
