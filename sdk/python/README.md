# uap-python · UAP Python SDK

[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](../../LICENSE)
[![Tests: 21 passed](https://img.shields.io/badge/tests-21%20passed-brightgreen)](#测试)

> Universal Agent Protocol Python SDK — 用三行代码把任意 Python 函数变成 UAP Agent

---

## 安装

```bash
# 最小安装（仅核心，无依赖）
pip install uap-python

# 含 HTTP 客户端
pip install "uap-python[client]"

# 含 FastAPI 服务端
pip install "uap-python[server]"

# 完整安装
pip install "uap-python[full]"
```

---

## 快速开始

### 1. 声明 Agent（服务端）

```python
from uap.decorators import uap_agent, uap_capability
from uap.capability import AccessTier
from uap.server import UAPServer
from fastapi import FastAPI

@uap_agent(
    did="did:uap:openwen:yijing-agent",
    name="易经解析 Agent",
    version="1.0.0",
    endpoint="https://api.openwen.io/agents/yijing",
)
class YijingAgent:

    @uap_capability(
        capability_id="yijing.search",
        name="典籍检索",
        access_tier=AccessTier.OPEN,       # 无需鉴权
    )
    async def search(self, query: str) -> dict:
        return {"results": [...]}           # 接入 RAG 检索

    @uap_capability(
        capability_id="yijing.interpret",
        name="卦象解读",
        access_tier=AccessTier.AUTHENTICATED,
    )
    async def interpret(self, hexagram: str, question: str = "") -> dict:
        return {"interpretation": "..."}    # 接入 LLM

# 挂载 UAP 标准端点到 FastAPI
app = FastAPI()
from uap.decorators import get_agent
uap = UAPServer(app, get_agent("did:uap:openwen:yijing-agent"))
uap.mount()
# 自动注册:
#   GET  /.well-known/uap   → 能力清单
#   GET  /uap/health        → 健康检查
#   POST /uap/invoke        → 能力调用
```

启动：
```bash
uvicorn main:app --reload --port 8088
```

### 2. 调用 Agent（客户端）

```python
from uap import AgentDID, UAPClient, Depth

async with UAPClient(
    caller_did=AgentDID.parse("did:uap:personal:user-maolin"),
    capability_token="your-token",
) as client:

    # 发现能力
    manifest = await client.discover("http://localhost:8088")
    print(manifest.to_json())

    # 调用易经解读
    resp = await client.invoke(
        target_did=AgentDID.parse("did:uap:openwen:yijing-agent"),
        endpoint="http://localhost:8088",
        capability="yijing.interpret",
        input={"hexagram": "乾卦", "question": "事业方向"},
        depth=Depth.SCHOLARLY,
    )

    if resp.ok:
        print(resp.output["interpretation"])
```

### 3. 构建 UAP 消息（底层 API）

```python
from uap import AgentDID, UAPMessage, Intent, Depth

msg = UAPMessage.create(
    from_did=AgentDID.parse("did:uap:personal:user-maolin"),
    to_did=AgentDID.parse("did:uap:openwen:yijing-agent"),
    intent=Intent.invoke(
        capability="yijing.interpret",
        input={"hexagram": "乾卦", "question": "创业方向"},
        depth=Depth.SCHOLARLY,
        extensions={"openwen:tradition": "王弼注本"},
    ),
    capability_token="eyJ...",
)

print(msg.to_json())   # 标准 UAP 信封格式
```

---

## 模块结构

```
uap/
├── identity.py      AgentDID — 去中心化身份标识符
├── intent.py        Intent — 结构化意图类型系统
├── envelope.py      UAPMessage / UAPResponse — 消息信封
├── capability.py    Capability / CapabilityManifest — 能力声明
├── decorators.py    @uap_agent / @uap_capability — 声明式装饰器
├── client.py        UAPClient — 异步 HTTP 调用客户端
└── server.py        UAPServer — FastAPI 服务端 Mixin
```

---

## AgentDID 格式

```
did:uap:<namespace>:<agent-id>[:<sub>]

did:uap:openwen:yijing-agent          # OpenWen 易经 Agent
did:uap:personal:alice:assistant      # 个人私有 Agent
did:uap:iot:sensor-node-7f2a          # IoT 设备 Agent
did:uap:enterprise:acme:invoice       # 企业服务 Agent
```

---

## 三层接入体系

| 层级 | `access_tier` | 鉴权要求 | 适用场景 |
|------|--------------|----------|----------|
| 开放层 | `open` | 无需鉴权 | 公开检索、演示能力 |
| 鉴权层 | `authenticated` | CapabilityToken | 个性化服务、有状态操作 |
| 私有层 | `private` | E2EE + Token | 命理数据、企业机密 |

---

## 测试

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
# 21 passed ✓
```

---

## 与 OpenWen 集成

本 SDK 是 [OpenWen 文枢](https://github.com/cml3366/openwen) 的官方 UAP 接入层。
查看完整示例：[examples/openwen_yijing.py](examples/openwen_yijing.py)

---

## License

Apache 2.0 · © 2025-2026 OpenWen Project
