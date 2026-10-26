# AGENTS.md · v0.2 架构与模块化规则

这页是给 code agent（GPT / Copilot / Claude / pi-agent 等）看的硬性规则。
人类读者从 [`README.md`](README.md) 开始。

---

## 1. 先读什么

1. [`README.md`](README.md) — 3 个单元、模块规则、路线。
2. [`docs/01-overview.md`](docs/01-overview.md) — 目标、模块目录、数据归属、契约。
3. [`docs/02-modules.md`](docs/02-modules.md) — 模块模板、增长手册、拆服务路径。
4. [`docs/03-decisions.md`](docs/03-decisions.md) — 为什么是 3 单元、为什么 Django + FastAPI。
5. [`docs/06-module-topics.md`](docs/06-module-topics.md) — 模块 topic 与优先级。
6. [`docs/07-reference-index.md`](docs/07-reference-index.md) — 官方/社区参考入口。
7. [`docs/08-existing-software.md`](docs/08-existing-software.md) — 已有软件：学什么/能不能直接用。
8. [`docs/09-anti-overengineering.md`](docs/09-anti-overengineering.md) — 复杂度预算与 AI coding 规则。
9. 图：`01-overall` → `02-core-modules` / `03-ai-modules` → `04-write-path` → `07-module-anatomy`。

---

## 2. 仓库与部署单元

| 仓库 | 技术 | 职责 |
|---|---|---|
| `home-web` | Next.js + TypeScript | UI、确认、草稿审核、API client |
| `home-core` | Django + DRF | 业务真相源、Admin、数据对接 |
| `home-ai` | FastAPI + pi-agent + LlamaIndex | intake / knowledge / tools / agent |

- 三个仓库可以独立开发/测试，但**部署单元只有这三个**。
- `home-ai` 的 worker 与 API 同代码、不同命令；不要为 worker 再建一个仓库。
- 不要新增 API Gateway / LLM Gateway / 独立消息队列；需要时先写决策记录。

---

## 3. 模块化硬规则

### 3.1 模块边界

1. 一个模块 = 一个目录，拥有自己的表、迁移、测试、README。
2. 其他模块只能依赖 **`contracts.py`（DTO/接口）** 和 **`services.py`（应用服务）**。
3. **禁止** `from <other_module>.models import ...`。
4. **禁止**跨模块外键、跨模块 JOIN、跨模块事务。
5. 跨模块只传 **DTO / ID**；不把 ORM 对象传过边界。
6. 唯一例外：`reporting` 模块可以只读 JOIN 多个模块的表，但不得写。
7. `integration` 是 adapter：只调各模块 public service，不直接写表。

### 3.2 事件

- 模块内可以用轻量 **in-process 事件**（`events.py` + 注册 handler）。
- 事件用于副作用（通知、建提醒、更新投影），不用于替代核心写流程。
- 跨服务暂不上 outbox / CloudEvents / Streams；直接调 API。
- 事件 handler 必须幂等；失败不影响主事务。

### 3.3 数据库

- 一个 PostgreSQL，两个 schema：`core`、`ai`。
- 表前缀 = 模块名，例如 `catalog_item`、`inventory_stock_lot`、`intake_job`。
- 迁移归模块自己；不要在别的模块迁移里改别人的表。
- `core` 与 `ai` 之间只存 ID，不建外键、不 JOIN。
- 所有表：`created_at / updated_at / version`；软删除用 `deleted_at`。
- 写操作记录 `actor_id`；高风险写记录原因。

### 3.4 写入

- `home-core` API 是**唯一业务写入口**。
- `home-ai` 只写 `ai` schema；不直连 `core` schema。
- Intake 只产草稿；确认后经 core API 提交。
- Knowledge 只读；索引可重建。
- Agent 只写自己的会话/run；不持有 core DB 凭据。

---

## 4. 模块长什么样

### 4.1 home-core（Django）

```
home-core/
├── manage.py
├── config/                 # settings / urls / composition root
├── app/
│   ├── shared/             # ids/time/errors/pagination/events/actor/audit
│   └── modules/
│       ├── catalog/
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── contracts.py     # public DTO + interfaces
│       │   ├── services.py      # public application service
│       │   ├── api.py           # DRF views/router
│       │   ├── admin.py
│       │   ├── events.py
│       │   ├── migrations/
│       │   ├── tests/
│       │   └── README.md        # 职责/表/公开接口/事件/依赖
│       ├── inventory/
│       ├── recipe/
│       ├── meal_plan/
│       ├── task/
│       ├── integration/
│       └── reporting/           # 只读；可选
└── pyproject.toml
```

规则：

- `api.py` 只做参数校验、调 `services.py`、返回 DTO；不写业务逻辑。
- `services.py` 是模块的事务边界；可以调自己的 models + 其他模块的 public service。
- `contracts.py` 不 import models；只放 dataclass/Pydantic DTO 与 Protocol。
- `models.py` 只属于本模块；不 import 其他模块 models。
- `admin.py` 只注册本模块 models；写操作要审计。
- 模块间依赖方向：catalog 是叶子；inventory/recipe 依赖 catalog；meal_plan 依赖 recipe/inventory；task 独立；integration/reporting 在外围。

### 4.2 home-ai（FastAPI）

```
home-ai/
├── app/
│   ├── main.py             # composition root: routers + startup
│   ├── worker.py           # 同一镜像的 worker 入口
│   ├── shared/             # config/errors/logging/ids/events
│   ├── platform/           # llm / storage / jobs / core_client
│   └── modules/
│       ├── intake/
│       │   ├── router.py
│       │   ├── contracts.py
│       │   ├── services.py
│       │   ├── models.py
│       │   ├── events.py
│       │   ├── tests/
│       │   └── README.md
│       ├── knowledge/
│       ├── tools/
│       └── agent/
└── pyproject.toml
```

规则：

- `agent` 只能通过 `tools` 访问 intake/knowledge/core；不直接 import 它们的 models。
- `tools` 是唯一桥；每个工具声明输入/输出、风险、是否幂等、是否需要确认。
- `intake` / `knowledge` 通过 `core_client` 调 core API；不直连 core DB。
- `platform` 只提供能力（llm/storage/jobs），不依赖业务模块。
- `worker` 只消费 jobs；与 API 共用 services，不复制业务逻辑。

### 4.3 home-web

```
home-web/
├── src/
│   ├── app/                # routes
│   ├── features/           # inventory / recipes / meal-plan / tasks / intake / knowledge / agent
│   ├── components/         # shared UI
│   └── lib/                # generated api client / query client
└── package.json
```

- 一个 feature 一个目录；不跨 feature 直接 import 内部组件（用 shared 或 public index）。
- 所有 API 调用走生成的 client；不手写重复类型。
- 不在前端做业务规则；只做展示/校验/确认。

---

## 5. 新增功能怎么做

### 5.1 新增 core 模块

1. 复制 `app/modules/_template/` 为 `app/modules/<name>/`（若还没有 `_template`，先按 4.1 的目录建空壳）。
2. 定义 `models.py`（表前缀 `<name>_`）、`contracts.py`、`services.py`、`api.py`。
3. 在 `config/settings.py` 的 `INSTALLED_APPS` 注册；在 `config/urls.py` 注册 router。
4. 生成迁移；只改自己的表。
5. 写模块测试 + 模块 README（职责/表/公开接口/事件/依赖）。
6. 更新 `docs/01-overview.md` 的模块目录与数据归属。
7. 不修改其他模块的 domain；需要别的模块能力时，调它的 public service。

### 5.2 新增 AI 模块

1. 复制 `app/modules/_template/`。
2. 实现 `router.py` / `services.py` / `contracts.py`；需要异步任务就注册 worker handler。
3. 在 `app/main.py` 注册 router；在 `worker.py` 注册 job handler。
4. 通过 `core_client` 访问 core；不直连 core DB。
5. 写模块测试 + README。
6. 如果要给 agent 用，新增 `tools`，不要在 agent 里直接 import 新模块。

### 5.3 新增工具（给 agent）

1. 在 `tools/` 定义 `ToolSpec` + Pydantic 输入/输出。
2. 声明：`name`、`description`、`risk`（read/write/irreversible）、`idempotent`、`requires_confirmation`、`timeout`。
3. 工具只调 public service / core_client；不写 SQL。
4. 写工具测试：成功、参数错误、权限拒绝、重复调用。
5. Agent 不需要改；注册后自动可见。

### 5.4 新增表

1. 先确定 owner 模块；只能在该模块的 `models.py` / migrations 里加。
2. 表前缀 `<module>_`；不建跨模块外键。
3. 加 `created_at / updated_at / version`；软删用 `deleted_at`。
4. 评估是否含 PII；更新数据归属文档。
5. 如果 reporting 需要 JOIN，只读视图/查询放 `reporting`，不要污染 domain。

### 5.5 新增 Web feature

1. `src/features/<name>/`：`api.ts`（生成 client）、`components/`、`pages`/route。
2. 类型从 OpenAPI 生成；不手写重复类型。
3. 写操作必须展示确认/diff；失败可重试。
4. 更新导航；不跨 feature import 内部实现。

### 5.6 拆一个模块为独立服务（以后）

触发条件（满足任一）：

- 需要独立扩缩容（如 OCR 高负载）。
- 需要独立权限/失败域（如 knowledge 只读、独立升级）。
- 迭代节奏/依赖明显不同（LlamaIndex 重依赖）。
- 团队/维护边界变化（单人项目通常最后才考虑）。

步骤：

1. 模块目录搬到新仓库；保留 `contracts`。
2. 原调用方从 in-process `services.py` 换成 HTTP adapter（实现同一个 Protocol）。
3. 加 OpenAPI/客户端；契约不变。
4. 数据迁移：模块表独立 schema/DB；只迁自己的表。
5. 其他模块**不改 domain**；只改 composition root 的依赖注入。

---

## 6. 完工检查清单（DoD）

一个改动完成前必须：

- [ ] 模块边界未破：没有跨模块 `models` import / FK / JOIN（reporting 除外）。
- [ ] 新增/修改表有迁移；只动自己的表。
- [ ] 公开接口在 `contracts.py` / `services.py`，没有泄漏 ORM。
- [ ] 写操作有 `actor_id`、幂等/版本策略；高风险写有确认。
- [ ] 测试：模块单元 + 至少一个集成/契约测试。
- [ ] `import-linter` / 模块边界检查通过；OpenAPI diff 无未声明的破坏性变更。
- [ ] 模块 `README.md` 更新（职责/表/公开接口/事件/依赖）。
- [ ] OpenAPI / 生成 client 更新（如有 API 变更）。
- [ ] `docs/01-overview.md` 或 `docs/02-modules.md` 更新（如有边界/数据变更）。
- [ ] 架构图更新并 `make check` 通过（如有结构变更）。

### 常用命令（示意）

```bash
# home-core
uv run pytest app/modules/<name>
uv run ruff check .
uv run mypy app

# home-ai
uv run pytest app/modules/<name>
uv run ruff check .
uv run mypy app

# home-web
pnpm lint
pnpm typecheck
pnpm test

# architecture
cd architecture && make check
```

---

## 7. 架构不变量

1. 三个部署单元：`home-web` / `home-core` / `home-ai`；不再按实体拆服务。
2. `home-core` API 是业务数据唯一写入口；AI 不直连 core schema。
3. `home-ai` 只写自己的 `ai` schema；草稿/索引/会话不是业务真相。
4. Knowledge 只读；Intake 只产草稿；Agent 写操作先确认。
5. 模块只通过 contracts/services/events 交互；不跨模块 import models。
6. 跨模块/跨 schema 只传 ID；不建外键、不 JOIN。
7. pi-agent 只做入口；多步编排等真实任务出现再加（LangGraph/DSH）。
8. 不提前加 API Gateway / LLM Gateway / Redis / MinIO / K8s；有需求再写决策记录。

---

## 8. 不要做

- 不要为了“以后可能拆”给每个模块加抽象层/接口/消息总线。
- 不要为了架构图加模块；先做 P1 库存闭环，模块由真实家庭场景驱动。
- 不要用模块数量/图数量当成果；先让家里用起来。
- 不要把 intake/knowledge/agent 又拆成三个服务。
- 不要跨模块 JOIN 图省事；需要跨模块视图就放 `reporting`。
- 不要把业务规则塞进 `api.py` 或前端。
- 不要让 agent 直接调 SQL / 直连 DB。
- 不要让 knowledge 写库存/菜单/待办。
- 不要在同步请求里跑长任务；用 jobs 表 + worker。
- 不要引入远程 PlantUML include；图必须能离线渲染（Kroki 会展开本地 include）。

---

## 8.5 复杂度预算

- 默认 **0 新服务、0 新依赖、0 新抽象**；需要时用一句话说明为什么不能更简单。
- 只在边界校验（API/外部输入/DB constraint）；内部不重复校验、不层层 try/except。
- 没有 ≥2 个真实实现/明确测试缝，不抽 interface/base/factory/strategy。
- 模块模板只建当前用到的文件；空目录/空接口/空 base class 不建。
- 一个改动只碰一个模块；不顺手重构无关文件。
- 测试行为，不测私有实现；不追 100% 覆盖率。
- 先量测再优化；没有数字不上缓存/队列/并发优化。

详见 [`docs/09-anti-overengineering.md`](docs/09-anti-overengineering.md)。

---

## 9. 术语

| 术语 | 含义 |
|---|---|
| 模块 | 一个 vertical slice：api/contracts/services/domain/models/events/tests |
| public | `contracts.py` + `services.py`；其他模块只能依赖这些 |
| shared kernel | ids/time/errors/pagination/events/actor/audit；无业务规则 |
| reporting | 唯一允许跨模块只读查询的模块 |
| tools | agent 访问业务的唯一桥；带风险/确认元数据 |
| draft | intake 的识别结果；不是业务数据，确认后才提交 |
| core schema | 业务真相源；只有 core API 写 |
| ai schema | intake/knowledge/agent/jobs；可重建，不是真相源 |
