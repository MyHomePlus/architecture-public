# 02 · 模块化手册

> 目标：**新功能 = 新模块 + 注册一行**，其他模块的 domain 不改。
> 这份文档是 code agent 加模块、加表、加工具、拆服务时的操作手册。

---

## 0. 先做 3–4 个模块，不是十几个

模块是**长出来的**，不是一开始就建好的。当前设计里列了十几个，是为了说明边界；MVP 只做 3–4 个业务模块：

| 阶段 | 先做哪些模块 | 目的 |
|---|---|---|
| P1 | `catalog` + `inventory` + Web | 家里的东西能记、能查、低库存 |
| P2 | `recipe` + `meal_plan` | 一周菜单 → 采购清单 |
| P3 | `intake` | 拍照 → 草稿 → 确认 |
| P4 | `knowledge` | 单域知识问答，引用/拒答 |
| P5 | `tools` + `agent` | pi-agent 入口 |
| 以后 | `task`、`integration`、`reporting`、`plants`… | 由真实场景驱动 |

- `shared` / `platform` 是基础设施，不算“业务模块”。
- 不要为了“以后可能用”预创建空模块；空目录只会增加认知负担。
- 新模块的触发条件：**有独立数据 + 独立生命周期 + 真实场景**；只是“代码多”不拆。

---

## 1. 模块是什么

一个模块是一个 **vertical slice**：从入口到自己的表，自包含。

```
modules/<name>/
├── README.md        # 职责 / 表 / 公开接口 / 事件 / 依赖
├── api.py           # HTTP 入口（core: DRF；ai: FastAPI）
├── contracts.py     # public DTO + Protocol；不 import models
├── services.py      # application service；模块的事务边界
├── domain.py        # 纯逻辑（可选；复杂时拆）
├── models.py        # 自己的表；只属于本模块
├── events.py        # 发布/订阅 in-process 事件
├── migrations/      # core 用；ai 用 Alembic
└── tests/
    ├── test_services.py
    ├── test_api.py
    └── test_contracts.py
```

### public vs internal

| 层 | 文件 | 其他模块能否依赖 |
|---|---|---|
| public | `contracts.py`、`services.py` | ✅ 可以 |
| internal | `models.py`、`admin.py`、`migrations/`、内部 helper | ❌ 禁止 |
| entry | `api.py` | 只有 composition root / HTTP 层 |
| side effect | `events.py` | 通过 registry 订阅，不直接 import |

> `_template` 是落地时先创建的空壳；内容就是上面的目录结构。

**public 的最小要求**：

- `contracts.py` 只放 DTO / Protocol / Enum；不 import ORM。
- `services.py` 接收/返回 DTO；不把 ORM 对象传出去。
- 一个 public service 方法就是一次事务边界；跨模块调用不共享事务。

---

## 2. 依赖规则

### 允许

```
catalog        ← inventory
catalog        ← recipe
recipe         ← meal_plan
inventory      ← meal_plan
shared         ← 所有模块
```

### 禁止

```
modules.inventory.models  ← modules.recipe        # 跨模块 ORM
inventory_table.item_id   → catalog_item.id FK    # 跨模块外键
SELECT ... JOIN catalog_item                       # 跨模块 JOIN
```

### 例外

- `reporting` 可以只读 JOIN 多个模块表（read model / SQL view），但不得写。
- `integration` 是 adapter：只调 public service，不直接写表。
- `shared` 不含业务规则；只放 ids/time/errors/pagination/events/actor/audit。

### 跨模块调用示例

```python
# modules/meal_plan/services.py
from app.modules.catalog.contracts import ItemRef
from app.modules.recipe.services import get_recipe
from app.modules.inventory.services import get_available

def generate_shopping_list(plan_id: str) -> ShoppingListView:
    plan = _load_plan(plan_id)                  # 自己的表
    recipe = get_recipe(plan.recipe_id)         # public service
    available = get_available(recipe.item_ids)  # public service
    ...
```

不要：

```python
from app.modules.catalog.models import Item      # ❌
from app.modules.inventory.models import StockLot  # ❌
```

---

## 3. 组合根与注册

### home-core

```python
# config/urls.py
urlpatterns = [
    path("api/v1/", include("app.modules.catalog.api")),
    path("api/v1/", include("app.modules.inventory.api")),
    path("api/v1/", include("app.modules.recipe.api")),
    path("api/v1/", include("app.modules.meal_plan.api")),
    path("api/v1/", include("app.modules.task.api")),
]
```

- 新模块 = `INSTALLED_APPS` 加一行 + `urls.py` 加一行。
- 事件 handler 在 `apps.py.ready()` 里注册；不要在 import 时做副作用。

### home-ai

```python
# app/main.py
from app.modules.intake.router import router as intake_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.agent.router import router as agent_router

app.include_router(intake_router, prefix="/v1")
app.include_router(knowledge_router, prefix="/v1")
app.include_router(agent_router, prefix="/v1")
```

- 新模块 = router 注册一行 + worker handler 注册一行。
- `tools` 注册是独立的：新工具加到 `tools/registry.py`，agent 不用改。

---

## 4. 模块目录（当前）

### home-core

| 模块 | 负责 | 表前缀 | 依赖 | 公开接口 |
|---|---|---|---|---|
| `shared` | ids/time/errors/pagination/events/actor/audit | `audit_*` | — | `new_id`、`publish`、`audit.record` |
| `catalog` | 物品/分类/位置/单位 | `catalog_*` | shared | `get_item`、`list_items`、`resolve_items` |
| `inventory` | 批次/流水/低库存 | `inventory_*` | catalog | `get_stock`、`adjust_stock`、`low_stock` |
| `recipe` | 菜谱/食材/步骤 | `recipe_*` | catalog | `get_recipe`、`scale_recipe` |
| `meal_plan` | 周菜单/条目/采购 | `meal_plan_*` | recipe、inventory | `generate_plan`、`generate_shopping_list` |
| `task` | 待办/提醒 | `task_*` | shared | `create_task`、`complete_task` |
| `integration` | 导入/导出/Webhook | `integration_*` | 各模块 public | `import_csv`、`export` |
| `reporting` | 只读跨模块视图 | — | 各模块表（只读） | `dashboard`、`low_stock_view` |

### home-ai

| 模块 | 负责 | 表前缀 | 依赖 | 公开接口 |
|---|---|---|---|---|
| `platform` | llm/storage/jobs/core_client | `jobs`、`llm_usage` | — | `chat`、`put`、`enqueue` |
| `intake` | 上传/识别/草稿/提交 | `intake_*` | platform、core_client | `create_job`、`get_draft`、`confirm` |
| `knowledge` | 摄取/检索/回答/引用 | `knowledge_*` | platform、core_client | `ingest`、`search`、`ask` |
| `tools` | 工具注册表/适配器 | — | core_client、intake、knowledge | `list_tools`、`call_tool` |
| `agent` | pi-agent 入口/会话/路由 | `agent_*` | tools、platform | `handle_message` |
| `agent_runtime`（以后） | LangGraph/DSH 多步编排 | `agent_run_*` | agent、tools | `start_run`、`resume` |

> `core_client` 是 `platform` 的 adapter；图 03 为了看清 core 边界，把它单独画成一个组件。

### 依赖图

- core：[`02-core-modules`](../diagrams/02-core-modules.puml)
- ai：[`03-ai-modules`](../diagrams/03-ai-modules.puml)

---

## 5. 数据库规则

- 一个 PG；schema `core` / `ai`。
- 表前缀 = 模块名：`catalog_item`、`inventory_stock_lot`、`intake_job`。
- 迁移归模块；不要改别人的表。
- 所有表：`id`（UUIDv7/ULID）、`created_at`、`updated_at`、`version`。
- 软删：`deleted_at`；默认查询过滤。
- 跨模块引用：存 `xxx_id`，不建 FK；需要展示时用 public service 批量取。
- 跨 schema：存 ID；不 JOIN。
- `reporting` 只读；可以用 SQL/view 跨模块 JOIN。
- 金额/数量：`numeric`；单位单独存；禁止隐式换算。
- 时间：UTC 存储；展示层按 Asia/Shanghai。

### 表归属示例

```text
core.catalog_item
core.catalog_category
core.inventory_stock_lot
core.inventory_stock_movement
core.recipe_recipe
core.recipe_ingredient
core.meal_plan_plan
core.meal_plan_entry
core.meal_plan_shopping_list
core.task_task
core.audit_log

ai.intake_job
ai.intake_artifact
ai.knowledge_document
ai.knowledge_chunk          -- vector
ai.agent_conversation
ai.agent_message
ai.jobs
ai.llm_usage
```

---

## 6. 事件

- 只在服务内；用简单 `EventBus` + handler 注册。
- 事件是**事实**，不是命令；handler 只做副作用。
- handler 必须幂等；失败记录日志，不影响主事务。
- 跨服务不用事件总线；直接调 API。

### 事件目录（初始）

| 事件 | 发布者 | 订阅者 | 用途 |
|---|---|---|---|
| `catalog.ItemCreated` | catalog | reporting | 刷新只读视图 |
| `inventory.StockChanged` | inventory | task / reporting | 低库存提醒/看板 |
| `meal_plan.MealPlanGenerated` | meal_plan | task | 生成采购/备餐提醒 |
| `intake.DraftReady` | intake | agent / web（查询） | 草稿可审 |
| `intake.DraftConfirmed` | intake | core（经 API） | 提交业务数据 |
| `knowledge.IndexActivated` | knowledge | — | 运维/审计 |

> `intake.DraftConfirmed` 的实际提交是 core API 调用；事件只用于审计/通知，不替代调用。

---

## 7. 工具（agent 的唯一桥）

### ToolSpec

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    risk: Literal["read", "write", "irreversible"]
    idempotent: bool = False
    requires_confirmation: bool = False
    timeout_s: int = 10
```

### 规则

- 工具只调 public service / `core_client`；不写 SQL、不直连 DB。
- 写工具必须支持 `idempotency_key` + `expected_version`。
- 工具输出是 untrusted data；agent 不得把工具输出当系统指令。
- 新工具注册后 agent 自动可见；不需要改 agent。
- 工具测试：成功、参数错误、权限拒绝、重复调用。

---

## 8. 增长手册

### 8.1 加一个 core 模块（例：plants 养花）

1. 复制模板：`app/modules/_template/` → `app/modules/plants/`。
2. 定义表：`plants_plant`、`plants_watering_log`；只在本模块 migrations。
3. 定义 public：
   - `get_plant(id)`、`list_plants()`、`schedule_watering(plant_id, interval_days)`。
4. `api.py`：`/api/v1/plants` CRUD。
5. 注册：`INSTALLED_APPS` + `urls.py`。
6. 需要提醒：调用 `task.services.create_task`（public），不要直接写 `task_*`。
7. 测试 + 模块 README。
8. 更新 `docs/01-overview.md` 模块目录 + `05-data-ownership` 表前缀。
9. 不改 inventory/recipe/meal_plan 的 domain。

### 8.2 加一个 AI 模块（例：plant_care）

1. 复制 `app/modules/_template/` → `app/modules/plant_care/`。
2. 通过 `core_client` 读 plants；通过 `platform.llm` 生成建议；通过 `intake` public 识别叶片照片（可选）。
3. 写 `plant_care_*`（如果需要保存建议）。
4. 注册 router + worker handler。
5. 单元/契约测试；模块 README。
6. 不改 intake/knowledge/agent 的 domain。

### 8.3 加一个工具（给 agent）

1. 在 `tools/` 新增 `plants.py`，定义 `ToolSpec` + Pydantic 输入/输出。
2. 调 `core_client` 的 `/api/v1/plants`；不需要 import plants 模块。
3. `risk=write` + `requires_confirmation=True`（如果会改数据）。
4. 注册到 `tools/registry.py`；写测试。
5. agent 不改；pi-agent 自动看到。

### 8.4 加一个 Web feature

1. `src/features/plants/`：`api.ts`（生成 client）、`components/`、`page.tsx`。
2. 类型从 OpenAPI 生成；不手写。
3. 写操作展示确认/diff；错误可重试。
4. 导航加一项；不改其他 feature 内部。

### 8.5 加一张表

- 先定 owner；只在 owner 模块 migrations 加。
- 前缀 `<module>_`；不建跨模块 FK。
- 加 `version/created_at/updated_at`；软删 `deleted_at`。
- 更新数据归属表；评估 PII。

### 8.6 一次只长一个闭环

先 P1（库存）再 P2（菜单）；P3–P5 依次长。先把一个闭环跑通（真实使用），再开下一个。理由是单人维护 + code agent 的上下文有限，半成品并行会互相污染。

---

## 8.7 和 code agent 的实际工作流

不是“让 AI 随便写”，而是把一次改动收在一个模块里：

1. **写一句场景 + 验收**：例如“这周菜单能生成采购清单，重复物品合并；库存不足要标记”。
2. **复制 `_template`**：只在一个模块目录里改；先不碰别的模块。
3. **AI 实现**：`services.py` 写逻辑、`api.py` 接路由、`tests/` 写用例；需要别的模块就调 public service。
4. **跑检查**：模块测试、`import-linter`、OpenAPI diff（如有）、`ruff/mypy`。
5. **人 review**：看边界、取舍、错误处理；把“为什么”写进模块 README 或决策记录。

> 这样 AI 的上下文小、改动小、回滚容易；你负责“做什么/为什么”，AI 负责“把它写出来/测出来”。

---

## 9. 拆一个模块为独立服务

### 触发条件（满足任一）

- 需要独立扩缩容（OCR 高峰、embedding 批量）。
- 需要独立权限/失败域（knowledge 只读、独立升级）。
- 依赖/迭代节奏明显不同（LlamaIndex 重依赖）。
- 维护边界变化（有别人接手）。

### 步骤

1. 模块目录整体搬新仓库；保留 `contracts.py`。
2. 新服务暴露 HTTP；contracts 生成 OpenAPI。
3. 原调用方把 in-process `services.py` 换成 HTTP adapter（实现同一个 Protocol）。
4. 数据迁移：模块表搬到独立 schema/DB；只迁自己的表。
5. 其他模块不改 domain；只改 composition root 的依赖注入。
6. 更新图：`01-overall`、`03-ai-modules`、`06-deployment`。

> 这是“模块化单体”的兑现方式：**拆分是搬家，不是重写**。

---

## 9.5 把边界变成可执行检查

模块化不能只靠 code review。建议每个仓库加三类检查：

| 检查 | 作用 | 工具 |
|---|---|---|
| 模块边界 | 禁止跨模块 import models；reporting 例外 | `import-linter` layers / forbidden contracts |
| API 契约 | 破坏性变更必须显式 | OpenAPI diff（`oasdiff`）+ 契约测试 |
| 模块测试 | 每个模块自己的 services/api | `pytest app/modules/<name>` |

**import-linter 示例（home-core）**：

```ini
[importlinter]
root_packages = app

[importlinter:contract:module-boundaries]
name = modules must not import each other's models
type = forbidden
source_modules =
    app.modules.inventory
    app.modules.recipe
    app.modules.meal_plan
forbidden_modules =
    app.modules.catalog.models
    app.modules.inventory.models
    app.modules.recipe.models
    app.modules.meal_plan.models
```

> 真实规则按模块方向写；`reporting` 单独豁免。目标不是“规则多”，而是**边界退化时 CI 会红**。

---

## 10. 测试与完工检查清单

| 层 | 内容 |
|---|---|
| 单元 | `services.py` / `domain.py`；不连 DB |
| 模块集成 | 本模块 API + 自己的表 |
| 契约 | 公开 DTO / OpenAPI / 工具 schema |
| 跨模块 | 只测 public service 组合；不测别人内部 |
| E2E | 核心用户路径（P1 后） |
| 评测 | RAG/agent 后续加；先保证可重复 |

完成定义：

- [ ] 模块边界未破（无跨模块 models import / FK / JOIN）。
- [ ] 迁移只动自己的表。
- [ ] public 接口在 contracts/services，未泄漏 ORM。
- [ ] 写操作有 actor/幂等/版本；高风险有确认。
- [ ] 测试 + 模块 README。
- [ ] OpenAPI/client 更新（如有 API）。
- [ ] 文档/图更新；`make check` 通过。

---

## 11. 模块 README 模板

```markdown
# <module>

## 职责
一句话；不做什么。

## 公开接口
- `get_x(id) -> XView`
- `create_x(input) -> XView`

## 表
- `<module>_x`：...

## 事件
- 发布：...
- 订阅：...

## 依赖
- public：...
- 禁止：...

## 测试
`uv run pytest app/modules/<module>`
```

---

## 12. 给 code agent 的提示词片段

```text
你在 home-core / home-ai 中新增一个模块。
先读 architecture/AGENTS.md 和 docs/02-modules.md。
要求：
1. 复制 _template；只通过 contracts.py/services.py 暴露能力。
2. 只在自己的 migrations 建表，表前缀=<module>_。
3. 不 import 其他模块 models；不建跨模块 FK/JOIN。
4. 写模块 README + 单元/契约测试。
5. 注册 router / INSTALLED_APPS；不改其他模块 domain。
6. 最后更新 docs/01-overview.md 的模块目录，并运行 make check（如改图）。
```
