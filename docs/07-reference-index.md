# 07 · 参考索引：官方规范 + 社区样板

> 借 `reference/peek` 里 PeekGo 的思路：**不靠模型记忆，靠可核对的一手资料**；按 module 提问，按 commit/版本取证。
> 这不是“书单”，是设计和编码时的**入口**：每读一个，记录“借什么 / 不借什么 / 为什么”。
> 已有软件的具体融合方式见 [`08-existing-software.md`](08-existing-software.md)；减法规则见 [`09-anti-overengineering.md`](09-anti-overengineering.md)。

---

## 1. 为什么需要这份索引

- AI 很会给出“看起来对”的答案；没有出处，就不知道是不是幻觉。
- 我们是自己生成需求，容易拍脑袋；成熟项目的**数据模型/边界/失败处理**可以对照。
- 但家庭项目不能照搬企业架构：参考的是**模式和取舍**，不是规模和流程。

三条规则：

1. **官方优先**：语言/框架/协议以官方文档为准。
2. **版本固定**：文档写版本；仓库写 `repo@commit/tag`，不读浮动 master。
3. **只借模式**：看它怎么建模、怎么分层、怎么处理失败；不复制业务、不复制复杂度。

---

## 2. 参考分级

| 级别 | 用途 | 例子 |
|---|---|---|
| **L1 规范/官方** | 必须遵守 | Django/DRF/FastAPI/OpenAPI/PostgreSQL 文档 |
| **L2 社区样板** | 借模式，需 pin commit | Mealie、Tandoor、Grocy、Paperless-ngx、NetBox |
| **L3 灵感** | 看交互/功能，不抄代码 | 产品截图、UI、文章 |
| **L4 不参考** | 家庭项目不适用 | 多租户 SaaS、K8s、事件溯源全家桶 |

> L2 的仓库通常比我们大。**只读相关模块**，不要“整仓膜拜”。

---

## 3. 按模块的参考入口

### 3.1 core 基础结构 / API

| 主题 | 官方/规范 | 社区样板（候选） | 看什么 | 不抄什么 |
|---|---|---|---|---|
| Django 模块划分 | [Django 5.2 docs](https://docs.djangoproject.com/en/5.2/)（apps / migrations / transactions / admin） | [NetBox](https://github.com/netbox-community/netbox)、[Pretix](https://github.com/pretix/pretix) | app 边界、迁移组织、admin 用法、事务边界 | 大型插件体系、复杂权限模型 |
| REST API | [DRF](https://www.django-rest-framework.org/)、[drf-spectacular](https://drf-spectacular.readthedocs.io/) | DRF 官方示例、[full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)（看契约/客户端生成） | viewset/serializer、分页、错误格式、OpenAPI | 复杂认证/多租户/巨大抽象层 |
| 契约 | [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0.html)、[JSON Schema](https://json-schema.org/) | — | schema-first、错误码、版本化 | 过度版本化/企业 API 治理 |
| FastAPI（AI 服务） | [FastAPI](https://fastapi.tiangolo.com/)、[Pydantic v2](https://docs.pydantic.dev/latest/) | [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)、[full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | 依赖注入、模块 router、Pydantic schema、测试 | 复杂 auth/队列/微服务拆分 |

### 3.2 数据与库存/菜谱/菜单

| 主题 | 官方/规范 | 社区样板（候选） | 看什么 | 不抄什么 |
|---|---|---|---|---|
| PostgreSQL | [PostgreSQL 16 docs](https://www.postgresql.org/docs/16/)（schema / constraints / transactions / `FOR UPDATE SKIP LOCKED` / FTS） | — | 约束、事务、锁、全文检索、备份 | 分区/分库/大规模调优（现在不需要） |
| 库存/批次/临期 | — | [Grocy](https://github.com/grocy/grocy) | stock/lot/location/expiry/shopping 的领域模型 | PHP 实现、完整 ERP 功能 |
| 菜谱/菜单/采购 | — | [Mealie](https://github.com/mealie-recipes/mealie)、[Tandoor Recipes](https://github.com/TandoorRecipes/recipes) | recipe/ingredient/meal plan/shopping list 的数据关系 | 多家庭/权限/大型食材库/复杂 UI |
| 数据导入导出 | [schema.org Recipe](https://schema.org/Recipe)（需要时） | Mealie 导入器 | 外部菜谱字段映射 | 为了标准而标准；先做 CSV/JSON |
| 条码/单位 | GS1 / 单位换算（以后） | — | 条码字段、单位换算边界 | 一开始做全量单位库/UCUM |

### 3.3 感知 / OCR / 知识 / Agent

| 主题 | 官方/规范 | 社区样板（候选） | 看什么 | 不抄什么 |
|---|---|---|---|---|
| OCR / 文档摄取 | — | [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | 上传、OCR、重试、文档元数据、任务状态 | 完整 DMS、复杂权限、超大索引 |
| RAG | [LlamaIndex docs](https://docs.llamaindex.ai/)、[pgvector](https://github.com/pgvector/pgvector) | 旧 `rag-service`（已归档） | 摄取、切分、混合检索、rerank、引用、评测 | 重型 Agent 平台、多租户、全自动知识图谱 |
| Agent 入口 | **pi-agent 官方文档/仓库（待你提供链接）** | — | 意图/工具调用/结构化输出、pi-agent 的边界 | 把 pi-agent 当多步编排/审批平台 |
| 多步编排（以后） | [LangGraph docs](https://langchain-ai.github.io/langgraph/) | — | state/checkpoint/interrupt/恢复 | 现在就上多 Agent/复杂审批 |
| 评测 | LlamaIndex evaluation 文档 | 旧 `rag-service` 的评测（已归档） | golden set、Recall@K、引用/拒答 | 用“感觉不错”代替评测 |

### 3.4 Web / 质量 / 安全 / 运维

| 主题 | 官方/规范 | 社区样板（候选） | 看什么 | 不抄什么 |
|---|---|---|---|---|
| Next.js | [Next.js docs](https://nextjs.org/docs) | Next.js examples | App Router、server/client 边界、数据获取 | 大型设计系统/复杂 SSR 架构 |
| 数据请求 | [TanStack Query](https://tanstack.com/query/latest) | — | cache、retry、loading/error | 把所有状态塞进全局 store |
| 测试 | [pytest](https://docs.pytest.org/)、[pytest-django](https://pytest-django.readthedocs.io/)、[Playwright](https://playwright.dev/) | — | 模块测试、API 测试、关键路径 E2E | 追求 100% 覆盖率 |
| 代码质量 | [ruff](https://docs.astral.sh/ruff/)、[mypy](https://mypy.readthedocs.io/)、[import-linter](https://import-linter.readthedocs.io/) | MoonCode 的“确定性检查 + 人工 review”思路 | 边界检查、类型、lint | 自建代码质量平台/复杂评分 |
| 安全 | [OWASP Top 10](https://owasp.org/www-project-top-ten/)、[Django security](https://docs.djangoproject.com/en/5.2/topics/security/) | — | 输入校验、密钥、依赖、基础 auth | 企业 IAM/ASVS 全量/合规流程 |
| 部署 | [Docker Compose](https://docs.docker.com/compose/)、[Caddy](https://caddyserver.com/docs/) | — | 单机 compose、TLS/反代、卷、健康检查 | K8s/服务网格/多集群 |
| 架构表达 | [PlantUML](https://plantuml.com/)、[C4](https://c4model.com/)、[ADR](https://adr.github.io/) | — | 文本图、边界图、决策记录 | 为了图而图、过度建模 |

---

## 4. 社区样板怎么用（PeekGo 规则）

1. **选 module，不要问“帮我写个家庭平台”**
   问题越具体，答案越像办案；越抽象，越像聊天。
2. **Pin 到 commit/tag**
   例如 `mealie-recipes/mealie@<commit>`；不读浮动 master。
3. **要文件路径/行号**
   “这个能力在哪个文件、怎么处理失败、为什么这么选。”
4. **对比，而不是照抄**
   至少看两个项目：一个轻、一个重；写清适用条件。
5. **记录“不借什么”**
   这比“借了什么”更能体现判断力。
6. **小实验验证**
   借来的模式先用一个 spike 验证，不直接进主分支。

### 提问模板（给 AI / 自己）

```text
在 <repo>@<commit> 中，<module> 如何处理 <problem>？
请给出：相关文件路径/行号、数据模型、失败处理、取舍。
只依据该 commit 的代码，不要用博客/记忆补充。
```

```text
只依据 <官方文档> <version>，实现 <feature> 的最小方案是什么？
列出：必须遵守的规范、可选的简化、不适用本项目的企业能力。
```

```text
对比 <repo A> 与 <repo B> 在 <pattern> 上的做法：
给表格（数据模型/边界/失败/复杂度），并说明家庭项目该借哪个、为什么。
```

---

## 5. 参考记录模板

每读一个关键参考，记一条（可以放模块 README 或 ADR）：

```markdown
## ref: <module> / <topic>
- 来源：official / repo / spec
- 链接：
- 版本/commit：
- 读了哪些文件：
- 借什么：
- 不借什么：
- 对项目的决定：
- 验证方式（spike/测试）：
```

---

## 6. 第一批要读的（P1/P2 前）

- [ ] Django 5.2：apps / migrations / transactions / admin
- [ ] DRF：viewsets / serializers / pagination / versioning
- [ ] drf-spectacular + OpenAPI 3.1
- [ ] PostgreSQL 16：schema / constraints / transactions / `SKIP LOCKED` / FTS
- [ ] Mealie 或 Tandoor：recipe / meal plan / shopping list 的数据关系
- [ ] Grocy：stock/lot/location/expiry 的领域模型
- [ ] Next.js App Router + TanStack Query
- [ ] pytest / Playwright / ruff / mypy / import-linter
- [ ] （P3 前）Paperless-ngx 的 OCR 任务/重试
- [ ] （P3 前）pi-agent 官方文档（待补链接）
- [ ] （P4 前）LlamaIndex / pgvector / 评测

> 不要一次读完；**做到哪个模块，读哪个模块**。

---

## 7. 不参考 / 不照抄

- 家庭项目不需要的：多租户、RBAC/OIDC、K8s、服务网格、事件溯源、CQRS 全家桶。
- “Awesome 列表”没有代码/版本，只能当索引，不能当证据。
- 博客 snippet 没有版本/上下文，容易过时。
- AI 生成的代码没有出处，不能当“官方用法”。
- 大厂架构文章：看取舍，不看规模；不要因为“他们这么做”就照搬。

---

## 8. 维护

- 版本升级时更新链接与“看什么”；过时参考标记 `deprecated`。
- 重要参考的结论写进 ADR 或模块 README，不留在聊天记录里。
- 以后如果参考条目很多，可以做一个很小的 `reference-index` CLI/MCP（类似 PeekGo 的 `find_projects_using_module`），但**现在先手工维护**。

> 参考索引的目标不是“读得多”，而是**少踩坑、能解释、能验证**。
