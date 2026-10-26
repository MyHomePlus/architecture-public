# 01 · 总体设计

> 目标、原则、三个单元、模块目录、数据归属、契约与路线。
> 名词解释见 [`00-glossary.md`](00-glossary.md)；模块化细节见 [`02-modules.md`](02-modules.md)；家庭场景见 [`05-family-scenarios.md`](05-family-scenarios.md)；决策见 [`03-decisions.md`](03-decisions.md)。

---

## 1. 目标

1. **单人可维护**：一个家庭、一个人开发，家里真的会用，能长期跑、能改、能恢复。
2. **模块能生长**：新功能是一个新模块，不是改一堆现有文件。
3. **边界可拆分**：先模块化单体；真需要时，把模块搬走即可，不改其他模块 domain。
4. **AI 可维护**：Code agent 能按明确规则加模块、表、工具、页面。
5. **数据可信**：业务数据单一写入口；知识只读；草稿不等于事实。

### 非目标

- 不做多租户 SaaS、计费、开放注册。
- 不做完整 ERP/医疗/安防系统。
- 不做 RBAC/OIDC/JWT、K8s、服务网格、事件总线、正式审批流、SLA/on-call。
- 不提前上 API/LLM 网关、Redis/MinIO（有真实需求再加）。
- 不按“每张表一个服务”拆微服务。

---

## 2. 约束

| 约束 | 影响 |
|---|---|
| 单人开发 + code agent | 模块必须自包含、规则必须可机械检查；少跨模块改动 |
| 单家庭、低并发 | 一个 PostgreSQL 足够；不需要分库分表 |
| 家庭数据敏感 | 本地优先；外部模型最小外发；写操作可审计 |
| 预算有限 | 先 3 个容器；Redis/MinIO/Caddy 按需 |
| 技术学习 | Django 练后端/Admin；FastAPI 练异步/AI；pi-agent 练入口 Agent |

---

## 3. 原则

1. **模块化单体优先**：3 个部署单元；模块是 vertical slice。
2. **单一写者**：每类数据只有一个 owner；业务写只经 core API。
3. **public / internal 分离**：模块只暴露 `contracts.py` + `services.py`。
4. **不共享数据库细节**：跨模块只传 DTO/ID；不跨模块 FK/JOIN。
5. **先同步后异步**：跨服务直接 API；服务内长任务用 jobs 表 + worker。
6. **先文件后对象存储**：本地磁盘起步；需要远程/多实例再上 MinIO。
7. **先入口后编排**：pi-agent 先做识别/路由；多步编排等真实任务。
8. **一次只长一个闭环**：P1/P2 不同时开；先让家里用起来，再抽象。

---

## 4. 三个部署单元

| 单元 | 技术 | 职责 | 失败影响 |
|---|---|---|---|
| `home-web` | Next.js / TS | 页面、表单、草稿审核、对话、确认 | 页面不可用；API 仍可调 |
| `home-core` | Django + DRF | 业务真相源、Admin、数据对接 | 业务写不可用；读可缓存 |
| `home-ai` | FastAPI + pi-agent + LlamaIndex | 识别、知识、工具、入口 Agent | AI 功能降级；core 仍可用 |

**为什么不是 4 个服务**：intake / knowledge / agent 现在都没有独立扩缩容/权限/生命周期需求；先作为 `home-ai` 模块，边界按可拆分设计。

**为什么不是 1 个后端**：Django 适合事务 CRUD/Admin；FastAPI 适合异步/流式/模型调用。两者失败域不同，保留两个后端是合理的最小拆分。

---

## 5. 模块目录

### 5.1 home-core

| 模块 | 职责 | 拥有表（前缀） | 依赖 | 公开接口（示例） |
|---|---|---|---|---|
| `shared` | ids/time/errors/pagination/events/actor/audit | `audit_*` | 无 | `new_id`、`publish`、`audit.record` |
| `catalog` | 物品/分类/位置/单位 | `catalog_*` | shared | `get_item`、`list_items`、`resolve_items` |
| `inventory` | 批次/流水/低库存 | `inventory_*` | catalog | `get_stock`、`adjust_stock`、`low_stock` |
| `recipe` | 菜谱/食材/步骤 | `recipe_*` | catalog | `get_recipe`、`scale_recipe` |
| `meal_plan` | 周菜单/条目/采购清单 | `meal_plan_*` | recipe、inventory | `generate_plan`、`generate_shopping_list` |
| `task` | 待办/提醒 | `task_*` | shared | `create_task`、`complete_task` |
| `integration` | 导入/导出/Webhook | `integration_*` | 各模块 public | `import_csv`、`export` |
| `reporting` | 只读跨模块查询（可选） | 无（只读） | 各模块表（只读） | `dashboard`、`low_stock_view` |

规则：catalog 是叶子；inventory/recipe 依赖 catalog；meal_plan 依赖 recipe/inventory；task 独立；integration/reporting 在外围。

### 5.2 home-ai

| 模块 | 职责 | 拥有表（前缀） | 依赖 | 公开接口（示例） |
|---|---|---|---|---|
| `platform` | llm / storage / jobs / core_client | `jobs`、`llm_usage` | 无业务依赖 | `llm.chat`、`storage.put`、`jobs.enqueue` |
| `intake` | 上传/识别/草稿/提交 | `intake_*` | platform、core_client | `create_job`、`get_draft`、`confirm` |
| `knowledge` | 摄取/检索/回答/引用 | `knowledge_*`（含 vector） | platform、core_client | `ingest`、`search`、`ask` |
| `tools` | 工具注册表/适配器 | 无 | core_client、intake、knowledge | `list_tools`、`call_tool` |
| `agent` | pi-agent 入口/会话/路由 | `agent_*` | tools、platform | `handle_message` |
| `agent_runtime`（以后） | LangGraph/DSH 多步编排 | `agent_run_*` | agent、tools | `start_run`、`resume` |

规则：`agent` 只能通过 `tools` 访问 intake/knowledge/core；`intake`/`knowledge` 只经 `core_client` 读写 core；`platform` 不依赖业务模块。

### 5.3 home-web

| feature | 职责 |
|---|---|
| `inventory` | 物品/库存/批次/低库存 |
| `recipes` | 菜谱/食材/步骤 |
| `meal-plan` | 周菜单/采购清单 |
| `tasks` | 待办/提醒 |
| `intake` | 上传/草稿审核/确认 |
| `knowledge` | 检索/问答/引用 |
| `agent` | 对话/工具结果/确认 |

规则：feature 自包含；API 调用走生成的 client；不写业务规则。

---

## 6. 数据归属

一个 PostgreSQL，两个 schema：

| schema | owner | 内容 | 写入 |
|---|---|---|---|
| `core` | home-core | `catalog_*`、`inventory_*`、`recipe_*`、`meal_plan_*`、`task_*`、`audit_*` | 只经 core API / Admin（审计） |
| `ai` | home-ai | `intake_*`、`knowledge_*`（vector）、`agent_*`、`jobs`、`llm_usage` | 各 AI 模块自己 |

- 模块表前缀 = 模块名；迁移归模块。
- core 与 ai 之间只存 ID；不建外键、不 JOIN。
- 本地磁盘存原图/文档；需要时切 MinIO。
- Redis 可选：先 jobs 表 + worker，队列压力大再加。
- `reporting` 是唯一允许跨模块只读 JOIN 的模块；不参与写事务。

图：[`05-data-ownership`](../diagrams/05-data-ownership.puml)、[`04-write-path`](../diagrams/04-write-path.puml)。

---

## 7. 契约

| 契约 | 形式 | 说明 |
|---|---|---|
| core API | OpenAPI 3.1 | 业务唯一写入口；生成 web/ai client |
| ai API | OpenAPI 3.1 | 识别/知识/agent；web 调用 |
| 模块间 | `contracts.py` + `services.py` | in-process；只传 DTO/ID |
| 工具 | Pydantic `ToolSpec` | 输入/输出、风险、幂等、确认 |
| 事件 | in-process | 只做副作用；跨服务暂不用事件总线 |

- 版本：`/api/v1`；破坏性变更升 `/v2`。
- 错误：统一 `{error: {code, message, trace_id}}`。
- 写：`Idempotency-Key` + `version`；高风险写带确认/diff。
- 认证 Phase 1：局域网/VPN + 共享 token（需要 TLS/反代时加 Caddy）；`X-Actor-Id` 审计；不做用户表。
- 跨服务调用：超时、重试仅幂等读；写不盲目重试。

---

## 8. 部署

- `home-web`、`home-core`、`home-ai` 三个应用容器。
- 一个 PostgreSQL（core/ai schema）。
- 本地卷存 uploads/knowledge。
- 可选：`home-ai worker`（同镜像）、Redis（队列）、MinIO（对象存储）、Caddy（TLS/反代）。
- 远程：Tailscale/WireGuard；不直接暴露端口。
- 备份：每日 `pg_dump`（两个 schema 分开）+ 本地卷快照；季度恢复演练。

图：[`06-deployment`](../diagrams/06-deployment.puml)。

---

## 9. 非功能目标（初始）

| 维度 | 目标 |
|---|---|
| CRUD p95 | < 300ms（局域网，不含外部模型） |
| 入口 Agent 首响 | < 2s（意图/路由） |
| RAG 回答 | < 8s（含重排/生成） |
| 图片识别 | 异步；p95 < 30s（取决于模型） |
| 可用性 | 家庭级 best effort；AI 挂了 core 仍可用 |
| 恢复 | 每日备份；季度恢复演练 |
| 成本 | 每 run/月预算；超限中止 |
| 隐私 | 本地优先；外部最小外发；日志不存原文 |

---

## 10. 路线

| 阶段 | 内容 | 出口 |
|---|---|---|
| P0 | 3 仓库骨架、模块模板、shared kernel、OpenAPI、Compose | 能启动、能测试、图能渲染 |
| P1 | 库存闭环：catalog / inventory + Web + quick add | 能记库存、查库存、低库存；录入快；备份恢复 |
| P2 | 菜单闭环：recipe / meal_plan / 采购清单 + daily digest | 能排一周菜单、生成采购清单；低库存/临期摘要；家人试用 |
| P3 | 拍照入库：intake 图片 → 草稿 → 确认 | 一张小票/食材能入库；失败可重试 |
| P4 | 知识单域：knowledge 检索 / 引用 / 拒答 | 一个领域真的有用、有边界 |
| P5 | 入口 Agent：pi-agent + tools | 自然语言能查/记；写操作先确认 |
| P6 | 按需编排 + 加固：LangGraph/DSH；备份/认证/观测 | 真实多步任务才上；可持续运行 |

> P1/P2 是家庭真正会用的两条闭环；先做 P1，再 P2。P3–P5 依次长，不要并行。
> P1 只跑 `home-web` + `home-core` + PG；`home-ai` 到 P3 再启动。

---

## 11. 主要风险

| 风险 | 表现 | 缓解 |
|---|---|---|
| 模块边界被破 | 跨模块 import models、JOIN | AGENTS 规则 + code review + 测试 |
| AI 模块变巨石 | intake/knowledge/agent 互相 import | tools 唯一桥；contracts 隔离 |
| 过早拆服务 | 运维复杂度上升 | 只在触发条件满足时拆 |
| RAG 幻觉 | 高风险域错误建议 | 引用、低置信拒答、单域先跑 |
| Agent 越权 | 未确认写 | 工具风险分级 + 确认/diff |
| 单人节奏 | 多模块并行烂尾 | 一次只长一个闭环；阶段门禁 |
| 过度设计 | 模块/文档先于使用 | 先 3–4 个业务模块；家里不用就不加 |
| 备份不可用 | 磁盘/配置错误 | 每日备份 + 季度恢复演练 |

---

## 12. 相关

- [`02-modules.md`](02-modules.md) — 模块模板、增长手册、拆服务
- [`03-decisions.md`](03-decisions.md) — 6 个决策（含“不做什么”）
- [`04-highlights.md`](04-highlights.md) — 设计亮点与取舍
- [`05-family-scenarios.md`](05-family-scenarios.md) — 家庭场景、MVP、后续想象与不做什么
- [`06-module-topics.md`](06-module-topics.md) — 模块 topic 地图与开发方向
- [`07-reference-index.md`](07-reference-index.md) — 官方/社区参考入口
- [`08-existing-software.md`](08-existing-software.md) — 已有软件与融合方式
- [`09-anti-overengineering.md`](09-anti-overengineering.md) — 复杂度预算与 AI coding 规则
- [`../AGENTS.md`](../AGENTS.md) — code agent 硬规则
- [`../diagrams/`](../diagrams/) — PlantUML 架构图
