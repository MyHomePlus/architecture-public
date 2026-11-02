# 03 · 关键决策（v0.2）

> 只记录会改变架构形状的决策；实现细节不在这里。
> 每条都写：背景 → 决策 → 后果 → 备选。

---

## D1 · 三个部署单元 + 模块化单体

### 背景

v0.1 拆了 4 个核心服务 + 2 个网关 + 4 个 DB。对单家庭、单人开发来说，运维和联调成本过高；但用户明确要求“后续功能拓展不能受影响”。

### 决策

- 部署单元只有 3 个：`home-web`、`home-core`、`home-ai`。
- `home-ai` 内部按模块拆：`intake`、`knowledge`、`tools`、`agent`、`platform`。
- 模块之间只通过 `contracts.py` / `services.py` / in-process 事件交互。
- 一个 PostgreSQL，两个 schema（`core` / `ai`）；模块表前缀隔离。
- **不按实体拆服务**；需要拆时按模块搬走。

### 后果

正面：

- 3 个容器就能跑；Docker Compose 足够。
- 新功能 = 新模块 + 注册一行；很少改现有 domain。
- 模块边界可机械检查（禁止 import models / FK / JOIN）。
- 以后拆服务是“搬家”，不是重写。

负面：

- `home-ai` 是模块化单体，重依赖（LlamaIndex/视觉/pi-agent）在同一镜像。
- 需要纪律：code agent 必须遵守 public/internal 规则。
- 跨模块只读报表需要 `reporting` 例外。

### 备选

| 方案 | 不选原因 |
|---|---|
| 4 个核心服务 | 当前没有独立扩缩容/权限/生命周期需求；运维成本高 |
| 1 个 Django 单体 | FastAPI 的异步/流式/模型调用更合适；失败域不同 |
| 按实体拆微服务 | 分布式事务/联调/运维成本高，收益低 |

**什么时候改**：某个模块需要独立扩缩容、独立权限/失败域、或依赖重到影响其他模块时，按 `02-modules.md` 的拆分步骤搬走。

---

## D2 · Django 做 core，FastAPI 做 AI

### 背景

资源域是事务型 CRUD（物品/库存/菜谱/菜单/待办），需要 Admin、迁移、数据治理；AI 域是突发/异步/模型调用（识别、RAG、Agent），需要 async/流式/Pydantic。

### 决策

- `home-core`：Django 5 + DRF + drf-spectacular；Django Admin 做数据治理。
- `home-ai`：FastAPI + Pydantic v2；pi-agent 入口；LlamaIndex 知识模块。
- 只共享契约（OpenAPI / DTO），不共享 ORM/模型代码。

### 后果

正面：

- Admin/ORM/迁移/权限生态成熟；CRUD 快。
- FastAPI 的异步/流式/突发任务更适合 AI。
- 失败域隔离：AI 挂了 core 仍可用。

负面：

- 两套 Python 框架；部署/风格/依赖不同。
- 需要 OpenAPI 生成 client，避免类型漂移。
- Django Admin 是绕过 API 的写入口，必须限制+审计。

### 备选

| 方案 | 不选原因 |
|---|---|
| 全 Django | 异步/流式/模型调用不如 FastAPI 自然 |
| 全 FastAPI | Admin/ORM/迁移要自己搭；与学习目标不符 |
| Django + Django Ninja | 可行，但 DRF 生态/资料更多；不阻塞 |

---

## D3 · 单一写者：core API 是唯一业务写入口

### 背景

AI 有写能力（建待办、调库存、提交识别结果），最容易出事故的是绕过审批/审计直接写库。

### 决策

- `home-core` API 是业务数据唯一写入口。
- `home-ai` 只写自己的 `ai` schema；不直连 `core` schema。
- Intake 只产草稿；确认后经 core API 提交。
- Knowledge 只读；索引可重建。
- Agent 只写会话/run；写操作先确认。
- 跨模块/跨 schema 只存 ID；不建 FK、不 JOIN。

### 后果

正面：

- 审计/回滚/权限清晰；AI 不能绕过人。
- 模块/服务可独立演进。
- 事故爆炸半径小。

负面：

- 跨服务调用增多；延迟/失败面增加。
- 报表需要 `reporting` 只读视图。
- 草稿/提交需要幂等/重试。

### 备选

| 方案 | 不选原因 |
|---|---|
| AI 直连 core DB | 权限过大、无法审计/回滚 |
| Knowledge 可写业务 | 幻觉污染真相源 |
| 共享数据库各写各的 | 冲突/耦合/无法拆 |

---

## D4 · pi-agent 做入口；编排等真实任务再加

### 背景

用户明确：pi 指 **pi-agent** 框架。入口 Agent 偏任务识别/编排，适合轻量；多步子 Agent 适合 LangGraph/DSH。

### 决策

- 入口 Agent 用 **pi-agent**：意图/补槽/澄清/路由；最多 1–2 次工具调用；单步写先确认。
- 入口只通过 `tools` 访问 intake/knowledge/core；不直接 import 业务模块。
- 多步编排（LangGraph/DSH）先不做；等第一个真实多步任务出现，作为 `agent_runtime` 新模块加入。
- 不做子 Agent 服务、不做 Runtime Port、不做独立审批服务；先工具级确认。

### 后果

正面：

- 入口快、实现少；pi-agent 直接可用。
- 不提前背编排框架的复杂度。
- 工具/业务模块不被 Agent 框架绑定。
- 以后加编排是新增模块，不改 tools/业务模块。

负面：

- 多步任务要等；复杂场景需要手工操作。
- 以后加编排需要设计 run/checkpoint/审批（但那时有真实需求）。

### 备选

| 方案 | 不选原因 |
|---|---|
| 现在就上 LangGraph | 没有真实多步任务，空转 |
| 入口也用 LangGraph | 入口太重、延迟高 |
| 一个 Agent 全包 | 边界不清、工具权限难控 |

---

## D5 · PostgreSQL first；Redis / MinIO / Caddy 按需

### 背景

家庭规模数据量小、并发低；v0.1 一上来就 4 DB + Redis + MinIO + 网关，运维面过大。

### 决策

- 一个 PostgreSQL：`core` / `ai` 两个 schema；`pgvector` 放 `ai`。
- 图片/文档先放本地卷；需要远程/多实例再切 MinIO。
- 长任务先用 `jobs` 表 + worker（`FOR UPDATE SKIP LOCKED`）；队列压力大再上 Redis。
- 不设 API Gateway；需要 TLS/反代时加 Caddy；远程用 VPN。
- 不设独立 LLM Gateway；`platform/llm` 统一 provider 配置；多服务需要时再上 LiteLLM。

### 后果

正面：

- 运维面最小；备份/恢复简单。
- 本地开发接近生产。
- 需要时逐步加，不阻塞。

负面：

- Redis 队列/缓存能力后补；突发识别可能受限。
- 本地磁盘不适合多实例；以后要迁 MinIO。
- 没有统一网关时，认证/限流要各服务自己做（Phase 1 可接受）。

### 备选

| 方案 | 不选原因 |
|---|---|
| 一开始 Redis + MinIO + 网关 | 过度设计；家庭规模不需要 |
| 独立向量库 | pgvector 足够；少一个组件 |
| 独立 LLM Gateway | 只有一个 AI 服务；共享模块足够 |

---

## 决策之间的关系

- D1 是总形状；D2/D3 是边界；D4 是 Agent 演进；D5 是基础设施节奏；D6 是范围约束。
- 任何一条要改，先改 `docs` 与图，再改代码；不要只改代码。
- 触发拆分/升级时，回到 `02-modules.md` 的步骤，不临时发挥。

---

## D6 · 主动不做企业级能力

### 背景

这是单人开发的家庭项目，不是企业平台。企业级能力（多租户、RBAC、K8s、事件总线、正式审批流、SLA）会显著增加设计和运维成本，但不产生家庭价值。

### 决策

当前**不做**：

- 多租户 / SaaS / 计费 / 开放注册；
- RBAC / OIDC / JWT / 用户表（Phase 1 用局域网/VPN + 共享 token）；
- K8s / 服务网格 / 独立消息队列 / API Gateway / LLM Gateway；
- 正式审批流 / SLA / on-call / 大规模观测；
- 一开始就建十几个模块；先 3–4 个业务模块。

保留：测试、迁移、错误处理、备份/恢复、结构化日志、API 契约、模块边界、基础安全检查。

### 后果

正面：

- 更快跑通真实闭环；一个人能维护。
- 基础设施少，备份/恢复简单。
- 时间花在家庭场景，而不是平台能力。

负面：

- 不是多用户 SaaS；不能直接对外开放。
- 高并发/多实例能力弱；以后要补。
- 没有正式权限体系；靠网络边界 + 共享 token + 操作记录。

### 备选

| 方案 | 不选原因 |
|---|---|
| 先做企业级能力 | 家庭规模用不上；拖慢闭环 |
| 直接上 K8s/事件总线 | 运维成本高，收益低 |
| 完整 RBAC/OIDC | 单家庭不需要；以后有真实多用户再说 |

### 什么时候改

- 真的有第二个家庭/多用户 → 加 `household_id` + OIDC；
- 队列/缓存成为瓶颈 → 加 Redis；
- 多实例/远程对象存储 → 加 MinIO；
- 出现真实多步任务 → 加编排模块；
- 需要公网访问 → 加 Caddy/VPN + 更强的认证。

> 这些是“以后可以加”，不是“现在必须做”。


---

## D9 · Layered narrative, isolated domain assistants

### Background

The original diagrams were complete but scattered across deployment, modules, data ownership, and write-path views. The project is now positioned as a lightweight AI life assistant, so the architecture needs one narrative: capabilities → atomic capabilities → domain services → life skills → domain assistants.

### Decision

- Use a five-layer composition view as the primary narrative.
- Keep domain assistants isolated: inventory / meal / shopping / reminder. They do not call each other and do not share context or tool allowlists.
- Share data through domain read contracts; writes stay inside the owning domain and go through the core API.
- A thin channel router may route an entry to one assistant, but must not reason across domains.
- Skills are versioned workflows owned by one assistant; they do not own tables.
- Keep module, write-path, data-ownership, and deployment diagrams as supporting engineering views.

### Consequences

Positive: clear ownership, smaller context, safer tools, easier explanation.

Negative: some cross-domain requests need explicit user switches; shared read contracts must be designed; the layered view can hide runtime/data boundaries if used alone.

### When to revisit

Only when a real workflow requires cross-domain coordination; then introduce an explicit domain workflow, not assistant-to-assistant chatter.
