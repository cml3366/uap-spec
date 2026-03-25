# RFC-0001: Universal Agent Protocol (UAP) Core Specification

```
标题:    UAP 核心协议规范 v1.0
状态:    草案 (DRAFT)
类型:    标准协议 (Standards Track)
作者:    OpenWen Project
创建日期: 2025-03-24
最后更新: 2026-03-25
讨论:    https://github.com/cml3366/uap-spec/discussions
```

---

## 目录

1. [摘要](#1-摘要)
2. [动机与背景](#2-动机与背景)
3. [术语定义](#3-术语定义)
4. [协议架构概览](#4-协议架构概览)
5. [AgentDID 身份规范](#5-agentdid-身份规范)
6. [三层接入体系](#6-三层接入体系)
7. [消息信封规范](#7-消息信封规范)
8. [意图类型系统](#8-意图类型系统)
9. [能力声明规范](#9-能力声明规范)
10. [握手与会话协议](#10-握手与会话协议)
11. [错误处理规范](#11-错误处理规范)
12. [安全要求](#12-安全要求)
13. [扩展机制](#13-扩展机制)
14. [参考实现](#14-参考实现)
15. [附录](#15-附录)

---

## 1. 摘要

Universal Agent Protocol (UAP) 是一个面向 AI Agent 互联互通的开放标准协议。UAP 定义了 Agent 之间建立信任、交换意图、协作执行任务的完整规范，填补了当前 AI 生态中 Agent 互联层协议的空白。

UAP 的核心设计目标：

- **协议中立**：不绑定任何特定 LLM 提供商或 Agent 框架
- **三层接入**：开放层、鉴权层、私有层，覆盖全部安全场景
- **万物互联**：人、设备、服务、AI 均可作为 Agent 节点接入
- **语义互通**：结构化意图描述，实现跨框架能力调用
- **可观测性**：全链路 trace，每次 Agent 调用留有审计证据

---

## 2. 动机与背景

### 2.1 当前问题

2025 年，AI Agent 框架进入爆发期。LangGraph、AutoGen、CrewAI、OpenWen 等框架各自为政，形成孤岛生态：

```
现状（碎片化）:
  LangGraph Agent  ──────────────────────  仅框架内互通
  AutoGen Agent    ──────────────────────  仅框架内互通
  OpenWen Agent    ──────────────────────  仅框架内互通
  IoT 设备          ──────────────────────  REST API，无Agent语义
  个人服务          ──────────────────────  无统一身份，无信任模型
```

现有协议的局限性：

| 协议 | 局限 |
|------|------|
| MCP (Anthropic) | 单向 LLM→工具，无 Agent-to-Agent |
| A2A (Google) | 绑定 Google 生态，非中立 |
| OpenAI Function Calling | 仅函数调用，无身份无信任 |
| REST/gRPC | 传输层协议，无 Agent 语义 |

### 2.2 UAP 的定位

UAP 不替代上述任何协议，而是作为**互联粘合层**存在：

```
UAP 愿景（互联网络）:

  个人Agent ◄──── UAP ────► 企业Agent
      ▲                         ▲
      │           UAP           │
      ▼                         ▼
  设备Agent ◄──── UAP ────► 知识Agent
                  ▲
                  │
              AI Model Agent
```

### 2.3 设计哲学

> "HTTP 解决了文档互联，TCP/IP 解决了设备互联，UAP 解决 Agent 互联。"

UAP 遵循以下设计哲学：

1. **最小化核心**：核心规范只定义必要的互操作契约，不规定实现细节
2. **渐进增强**：只实现 L1-L3 即可基础互联，逐层解锁高级能力
3. **人在回路**：私有层任何高风险操作默认需要人工确认
4. **数据主权**：私有数据不得在未授权情况下离开所有者域

---

## 3. 术语定义

| 术语 | 定义 |
|------|------|
| **Agent** | 能够接收意图、执行能力、返回结果的自治软件实体 |
| **AgentDID** | Agent 的去中心化唯一标识符，遵循 W3C DID 规范 |
| **Capability** | Agent 对外声明的可调用能力单元，如 `yijing.interpret` |
| **Intent** | 调用方传递给 Agent 的结构化任务描述 |
| **CapabilityToken** | 授予特定 Agent 调用特定能力的时效性令牌 |
| **AgentMesh** | 多个 Agent 通过 UAP 协议形成的互联拓扑网络 |
| **CapabilityMarket** | Agent 能力的注册、发现、供需匹配服务 |
| **AgentDNS** | Agent 命名空间的全局寻址与解析服务 |
| **TrustChain** | 从人类委托者到 Agent 的授权信任传递链 |
| **UAP-Lite** | 面向 IoT/嵌入式设备的轻量级 UAP 子集 |

关键字约定（遵循 RFC 2119）：
- **必须 (MUST)**：强制要求
- **不得 (MUST NOT)**：明确禁止
- **应当 (SHOULD)**：强烈推荐
- **可以 (MAY)**：可选实现

---

## 4. 协议架构概览

UAP 采用六层协议栈设计：

```
┌─────────────────────────────────────────────────┐
│  L6  应用层 (Application)                        │
│      Agent 业务逻辑 · 多 Agent 协同工作流          │
├─────────────────────────────────────────────────┤
│  L5  编排层 (Orchestration)                      │
│      意图路由 · DAG 任务调度 · 结果聚合            │
├─────────────────────────────────────────────────┤
│  L4  能力层 (Capability)                         │
│      能力声明 · 版本管理 · 参数校验                │
├─────────────────────────────────────────────────┤
│  L3  信任层 (Trust)                              │
│      DID 身份 · 能力令牌 · 访问控制                │
├─────────────────────────────────────────────────┤
│  L2  消息层 (Message)                            │
│      信封格式 · 序列化 · 压缩 · 加密               │
├─────────────────────────────────────────────────┤
│  L1  传输层 (Transport)                          │
│      HTTP/2 · WebSocket · gRPC · MQTT (IoT)      │
└─────────────────────────────────────────────────┘
```

最小实现（MVP）只需实现 L1-L3 即可完成基础 Agent 互联。

---

## 5. AgentDID 身份规范

### 5.1 DID 格式

每个 Agent 必须拥有一个唯一的 AgentDID：

```
did:uap:<namespace>:<agent-id>[:<sub-capability>]
```

示例：

```
did:uap:openwen:yijing-agent              # OpenWen 易经解析 Agent
did:uap:openwen:coordinator               # OpenWen 协调 Agent
did:uap:personal:alice:home-assistant     # 个人私有 Agent
did:uap:iot:sensor-node-7f2a             # IoT 设备 Agent
did:uap:enterprise:acme:invoice-agent    # 企业私有 Agent
```

### 5.2 DID 文档

每个 AgentDID 必须对应一个可解析的 DID Document：

```json
{
  "@context": ["https://www.w3.org/ns/did/v1", "https://uap-spec.io/context/v1"],
  "id": "did:uap:openwen:yijing-agent",
  "created": "2025-03-24T00:00:00Z",
  "updated": "2026-03-25T00:00:00Z",
  "controller": "did:uap:openwen:coordinator",
  "service": [
    {
      "id": "#uap-endpoint",
      "type": "UAPEndpoint",
      "serviceEndpoint": "https://api.openwen.io/agents/yijing",
      "transportProtocols": ["http2", "websocket"]
    }
  ],
  "verificationMethod": [
    {
      "id": "#key-1",
      "type": "Ed25519VerificationKey2020",
      "publicKeyMultibase": "z6Mkt..."
    }
  ],
  "authentication": ["#key-1"],
  "capabilityDelegation": ["#key-1"]
}
```

### 5.3 AgentDNS 解析

AgentDNS 是 UAP 网络的命名解析服务，类比 DNS 对 IP 的作用：

```
查询: did:uap:openwen:yijing-agent
  ↓
AgentDNS 解析
  ↓
返回: {
  endpoint: "https://api.openwen.io/agents/yijing",
  public_key: "z6Mkt...",
  capabilities: ["yijing.interpret", "yijing.hexagram"],
  access_tier: "authenticated"
}
```

---

## 6. 三层接入体系

UAP 定义三种接入层级，覆盖全部安全场景：

### L1 · 开放层 (Open Tier)

```
特征: 无需任何鉴权，公开能力，任何 Agent 可直接调用
适用: 公共知识查询、开放数据、演示能力
风险: 低（只读，无副作用）
```

示例能力：`openwen.classics.search`、`openwen.poetry.generate`

请求头：无需特殊头部，直接携带 Intent 消息

### L2 · 鉴权层 (Authenticated Tier)

```
特征: 需要 AgentDID + CapabilityToken 鉴权
适用: 个性化服务、有状态操作、资源消耗型能力
鉴权: DID Challenge-Response + JWT CapabilityToken
```

Token 结构：

```json
{
  "iss": "did:uap:openwen:coordinator",
  "sub": "did:uap:client:user-123",
  "aud": "did:uap:openwen:yijing-agent",
  "cap": ["yijing.interpret", "yijing.hexagram.full"],
  "iat": 1711324800,
  "exp": 1711411200,
  "jti": "cap-token-uuid-v4"
}
```

### L3 · 私有层 (Private Tier)

```
特征: 端到端加密，数据主权归所有者，不出域
适用: 个人命理/八字、医疗健康数据、企业机密
加密: X25519 ECDH 密钥协商 + ChaCha20-Poly1305 对称加密
审计: 本地 Audit Log，不上传
```

私有层协议要求：
- **必须** 使用端到端加密
- **必须** 在数据所有者域内处理计算
- **不得** 将原始数据发送至第三方服务
- **应当** 保留本地操作日志

---

## 7. 消息信封规范

### 7.1 标准信封格式

所有 UAP 消息使用统一信封格式（JSON）：

```json
{
  "uap_version": "1.0",
  "envelope": {
    "message_id": "msg-uuid-v4",
    "timestamp": "2026-03-25T10:00:00Z",
    "ttl": 30,
    "trace_id": "trace-uuid-v4",
    "span_id": "span-uuid-v4"
  },
  "routing": {
    "from": "did:uap:client:user-123",
    "to": "did:uap:openwen:yijing-agent",
    "reply_to": "did:uap:client:user-123:callback",
    "access_tier": "authenticated"
  },
  "auth": {
    "capability_token": "eyJ...",
    "signature": "Ed25519:base64..."
  },
  "intent": {
    "type": "capability.invoke",
    "capability": "yijing.interpret",
    "version": "^1.0",
    "input": {
      "hexagram": "乾卦",
      "question": "事业发展方向"
    },
    "options": {
      "response_format": "structured",
      "language": "zh-CN",
      "depth": "scholarly"
    }
  }
}
```

### 7.2 响应信封格式

```json
{
  "uap_version": "1.0",
  "envelope": {
    "message_id": "msg-response-uuid",
    "request_id": "msg-uuid-v4",
    "timestamp": "2026-03-25T10:00:02Z",
    "trace_id": "trace-uuid-v4"
  },
  "status": {
    "code": 200,
    "message": "success",
    "execution_ms": 1842
  },
  "result": {
    "capability": "yijing.interpret",
    "output": {
      "interpretation": "乾为天，健也...",
      "citations": ["《周易·乾卦》彖曰：大哉乾元"],
      "confidence": 0.95
    },
    "metadata": {
      "model_used": "qwen-max",
      "tokens_consumed": 1240,
      "rag_sources": 3
    }
  }
}
```

---

## 8. 意图类型系统

UAP 定义标准意图类型，实现跨框架语义互通：

| 意图类型 | 说明 | 示例 |
|----------|------|------|
| `capability.invoke` | 调用特定能力 | 调用易经解读 |
| `capability.discover` | 发现可用能力 | 列出 Agent 所有能力 |
| `capability.negotiate` | 协商调用参数 | 协商输出格式 |
| `task.delegate` | 委托子任务 | 协调 Agent 分发任务 |
| `task.status` | 查询任务状态 | 异步任务进度 |
| `task.cancel` | 取消任务 | 中止长时任务 |
| `session.open` | 建立会话 | 多轮对话初始化 |
| `session.close` | 关闭会话 | 释放资源 |
| `event.subscribe` | 订阅事件 | 监听 Agent 状态变化 |
| `event.publish` | 发布事件 | 推送通知 |

自定义意图必须使用命名空间前缀：`openwen.intent.custom_type`

---

## 9. 能力声明规范

### 9.1 能力清单格式 (capability-manifest.json)

每个 Agent 必须提供能力清单文件：

```json
{
  "uap_version": "1.0",
  "agent": {
    "did": "did:uap:openwen:yijing-agent",
    "name": "易经解析 Agent",
    "description": "基于完整周易典籍的六十四卦深度解读",
    "version": "1.2.0",
    "access_tier": "authenticated",
    "endpoint": "https://api.openwen.io/agents/yijing"
  },
  "capabilities": [
    {
      "id": "yijing.interpret",
      "name": "卦象解读",
      "description": "输入卦名或爻辞，返回深度义理解读",
      "version": "1.0.0",
      "access_tier": "authenticated",
      "input_schema": "$ref:schema/yijing-interpret-input.json",
      "output_schema": "$ref:schema/yijing-interpret-output.json",
      "rate_limit": {"requests_per_minute": 20},
      "avg_latency_ms": 2000,
      "required_agents": []
    },
    {
      "id": "yijing.hexagram.full",
      "name": "完整卦象分析",
      "description": "包含本卦、变卦、互卦的完整分析报告",
      "version": "1.0.0",
      "access_tier": "authenticated",
      "required_agents": ["did:uap:openwen:classics-agent"]
    }
  ],
  "trust": {
    "public_key": "z6Mkt...",
    "cert_fingerprint": "sha256:abc123..."
  }
}
```

---

## 10. 握手与会话协议

### 10.1 鉴权层握手流程

```
调用方                          UAP服务方
  │                                │
  │  1. GET /.well-known/uap       │
  │ ──────────────────────────────►│
  │  ← capability-manifest.json    │
  │                                │
  │  2. POST /uap/auth/challenge   │
  │     {caller_did, nonce}        │
  │ ──────────────────────────────►│
  │  ← {challenge, server_nonce}   │
  │                                │
  │  3. POST /uap/auth/token       │
  │     {signed_challenge, ...}    │
  │ ──────────────────────────────►│
  │  ← {capability_token, ttl}     │
  │                                │
  │  4. POST /uap/invoke           │
  │     {envelope + intent}        │
  │ ──────────────────────────────►│
  │  ← {result envelope}           │
  │                                │
```

### 10.2 Well-Known 端点

每个 UAP Agent 必须暴露以下标准端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/.well-known/uap` | GET | 能力清单（无需鉴权） |
| `/uap/auth/challenge` | POST | 获取认证挑战 |
| `/uap/auth/token` | POST | 获取能力令牌 |
| `/uap/invoke` | POST | 调用能力（需鉴权） |
| `/uap/invoke/stream` | WebSocket | 流式调用 |
| `/uap/status/{task_id}` | GET | 异步任务状态 |
| `/uap/health` | GET | 健康检查 |

---

## 11. 错误处理规范

### 11.1 标准错误码

| 码段 | 类型 | 示例 |
|------|------|------|
| 4xx | 客户端错误 | 400 Bad Intent, 401 Auth Required |
| 5xx | 服务端错误 | 500 Agent Internal Error |
| 6xx | UAP 协议错误 | 600 Version Mismatch |
| 7xx | 信任/安全错误 | 700 Invalid Token, 701 Capability Denied |
| 8xx | 能力错误 | 800 Capability Not Found, 801 Rate Limited |

### 11.2 错误响应格式

```json
{
  "uap_version": "1.0",
  "envelope": {"message_id": "...", "request_id": "..."},
  "status": {
    "code": 800,
    "message": "Capability Not Found",
    "detail": "yijing.predict_future is not a registered capability",
    "suggestion": "Use yijing.interpret or yijing.hexagram.full"
  },
  "error": {
    "type": "CapabilityNotFoundError",
    "available_capabilities": ["yijing.interpret", "yijing.hexagram.full"]
  }
}
```

---

## 12. 安全要求

### 12.1 传输安全

- **必须** 在生产环境使用 TLS 1.3+
- **应当** 启用 HSTS（HTTP Strict Transport Security）
- **不得** 在 URL 中传递 CapabilityToken

### 12.2 消息完整性

- **必须** 对所有 L2/L3 层消息进行数字签名
- **应当** 在签名中包含时间戳防止重放攻击
- **必须** 验证签名后再处理任何 Intent

### 12.3 私有层额外要求

- **必须** 使用端到端加密（E2EE）
- **不得** 在服务端日志中记录原始 payload
- **必须** 实现密钥前向安全（Forward Secrecy）

### 12.4 注入攻击防护

- **必须** 对所有 Intent 参数进行严格 Schema 验证
- **不得** 将 Intent 内容直接拼接为 LLM prompt
- **应当** 实现 Intent 参数的沙箱隔离

---

## 13. 扩展机制

UAP 通过命名空间扩展支持特定领域能力：

```json
{
  "intent": {
    "type": "capability.invoke",
    "capability": "openwen.yijing.interpret",
    "extensions": {
      "openwen:tradition": "王弼注本",
      "openwen:depth": "scholarly",
      "openwen:cite_sources": true
    }
  }
}
```

扩展规则：
- 扩展字段必须以命名空间前缀标识
- 接收方不识别的扩展字段应当忽略（不报错）
- 核心规范字段不得被扩展字段覆盖

---

## 14. 参考实现

| 实现 | 语言 | 地址 | 状态 |
|------|------|------|------|
| uap-python | Python | github.com/cml3366/uap-python | 规划中 |
| OpenWen Core | Python/FastAPI | github.com/cml3366/openwen | 开发中 |
| uap-js | TypeScript | github.com/cml3366/uap-js | 规划中 |

---

## 15. 附录

### 附录 A：UAP vs 现有协议对比

| 特性 | MCP | A2A | OpenAI FC | **UAP** |
|------|-----|-----|-----------|---------|
| Agent-to-Agent | ✗ | ✓ | ✗ | **✓** |
| 协议中立 | 部分 | ✗ | ✗ | **✓** |
| 三层接入 | ✗ | ✗ | ✗ | **✓** |
| 端到端加密 | ✗ | 部分 | ✗ | **✓** |
| IoT 支持 | ✗ | ✗ | ✗ | **✓ (UAP-Lite)** |
| 去中心身份 | ✗ | ✗ | ✗ | **✓ (DID)** |
| 开源标准 | ✓ | 部分 | ✗ | **✓** |

### 附录 B：版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0-draft | 2025-03-24 | 初始草案 |
| 1.0-draft.2 | 2026-03-25 | 完善信封格式，补充安全要求 |

---

*UAP 规范遵循 Apache 2.0 开源协议。欢迎通过 GitHub Issues 和 Discussions 参与标准讨论。*
