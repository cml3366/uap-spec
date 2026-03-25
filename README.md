# UAP · Universal Agent Protocol

[![Status: Draft](https://img.shields.io/badge/status-draft-orange)](RFC-0001-UAP-CORE.md)
[![Version: 1.0](https://img.shields.io/badge/version-1.0-blue)](RFC-0001-UAP-CORE.md)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

> **万Agent互联协议** · 产品 · 服务 · 人 · 设备 · AI，私有Agent作为身份载体，万物皆可互联

---

## 为什么需要 UAP？

2025年，AI Agent爆发式增长，但**互联互通**依然是最大的空白：

- MCP 解决了 LLM→工具的连接，但不是 Agent-to-Agent
- A2A 绑定 Google 生态，非中立
- REST/gRPC 是传输层，没有 Agent 语义

**UAP 是 Agent 时代的 TCP/IP**——定义最小互操作契约，让任意框架、任意语言的 Agent 彼此发现、信任、协作。

---

## 核心特性

| 特性 | 说明 |
|------|------|
| 🆔 **AgentDID 身份** | 每个 Agent/设备/人拥有去中心化唯一身份 |
| 🔐 **三层接入体系** | 开放层·鉴权层·私有层，覆盖全部安全场景 |
| 📨 **标准消息信封** | 统一的请求/响应格式，跨框架语义互通 |
| 🔍 **能力发现** | `/.well-known/uap` 标准端点，自动发现 Agent 能力 |
| 📡 **多传输层** | HTTP/2 · WebSocket · gRPC · MQTT (IoT) |
| 👁 **可观测性** | 全链路 trace_id/span_id，每次调用可审计 |
| 🔌 **协议中立** | 不绑定任何 LLM 或 Agent 框架 |

---

## 协议栈

```
┌─────────────────────────────┐
│  L6  应用层  Agent业务逻辑   │
├─────────────────────────────┤
│  L5  编排层  意图路由·调度   │
├─────────────────────────────┤
│  L4  能力层  声明·版本·校验  │
├─────────────────────────────┤
│  L3  信任层  DID·令牌·访控  │
├─────────────────────────────┤
│  L2  消息层  信封·加密·压缩  │
├─────────────────────────────┤
│  L1  传输层  HTTP2·WS·gRPC  │
└─────────────────────────────┘
```

MVP 只需实现 **L1-L3**，即可完成基础 Agent 互联。

---

## 仓库结构

```
uap-spec/
├── RFC-0001-UAP-CORE.md          # 核心协议规范
├── schema/
│   ├── agent-did-document.json   # AgentDID 文档 Schema
│   ├── message-envelope.json     # 消息信封 Schema
│   └── capability-manifest.json  # 能力清单 Schema
├── examples/
│   ├── openwen-yijing-agent-manifest.json  # OpenWen 示例
│   └── invoke-yijing-request.json          # 调用示例
└── docs/
```

---

## 快速开始

### 1. 声明 Agent 身份（/.well-known/uap）

```json
{
  "uap_version": "1.0",
  "agent": {
    "did": "did:uap:yourns:your-agent",
    "name": "Your Agent Name",
    "access_tier": "authenticated",
    "endpoint": "https://your-api.example.com/uap"
  },
  "capabilities": [
    { "id": "domain.capability", "name": "Your Cap", "version": "1.0.0" }
  ]
}
```

### 2. 发起 UAP 调用

```json
POST /uap/invoke  Authorization: Bearer <capability_token>

{
  "uap_version": "1.0",
  "envelope": { "message_id": "uuid-v4", "timestamp": "2026-03-25T10:00:00Z" },
  "routing": {
    "from": "did:uap:caller:agent",
    "to": "did:uap:target:agent",
    "access_tier": "authenticated"
  },
  "intent": { "type": "capability.invoke", "capability": "domain.cap", "input": {} }
}
```

---

## 参考实现

| 实现 | 语言 | 状态 |
|------|------|------|
| [OpenWen](https://github.com/cml3366/openwen) | Python/FastAPI | 开发中（首个参考实现） |
| uap-python SDK | Python | 规划中 |
| uap-js SDK | TypeScript | 规划中 |

---

## 参与贡献

UAP 是开放标准：[Issues](https://github.com/cml3366/uap-spec/issues) · [Discussions](https://github.com/cml3366/uap-spec/discussions) · PR 欢迎

## License

Apache 2.0 · © 2025-2026 OpenWen Project

---

*知古今之变，通东西之道——OpenWen 是 UAP 的第一个完整实现。*
