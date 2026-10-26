# 08 · 已有软件：学什么、能不能直接用、怎么融合

> 目标不是“集成一堆开源软件”，而是借它们的**领域模型/边界/交互**；
> 能直接用的，限定在库、扩展、标准或外部 API；**不引入第二个全功能 App** 来替代我们的核心模块。

---

## 1. 四种“复用”方式

| 方式 | 含义 | 适合 |
|---|---|---|
| **A. 直接依赖** | 作为库/扩展/服务运行 | Django、DRF、pgvector、LlamaIndex、pi-agent、Next.js |
| **B. 设计参考** | 读源码/文档，借数据模型/边界/交互 | Mealie、Tandoor、Grocy、NetBox |
| **C. 一次性导入/导出** | 用 CSV/JSON/API 把数据搬进来 | 已有 Mealie/Tandoor/Grocy 数据 |
| **D. 运行时 API** | 外部服务作为 adapter，不共享 DB | Open Food Facts、以后可能的 OCR/通知 |
| **E. 不做** | 运维/授权/复杂度不划算 | Home Assistant、n8n、完整 DMS |

判断标准：**它是不是我们核心闭环的一部分？**
是 → 自己做，最多借设计；不是 → 可以外部 API/一次性导入。

---

## 2. 候选软件对照

| 软件 | 栈/定位 | 相关模块 | 值得学 | 直接用？ | 结论 |
|---|---|---|---|---|---|
| [Mealie](https://github.com/mealie-recipes/mealie) | FastAPI + Vue；self-hosted 菜谱/菜单/采购 | recipe、meal_plan | 菜谱/食材/菜单/采购的数据关系、导入流程、API/UX | ❌ 不运行 | 设计参考；以后可做**一次性菜谱导入** |
| [Tandoor Recipes](https://github.com/TandoorRecipes/recipes) | Django；菜谱/菜单/采购 | recipe、meal_plan | Django 建模、表单、食材/属性、采购清单 | ❌ 不运行 | 设计参考；Django 结构对照 |
| [Grocy](https://github.com/grocy/grocy) | PHP；家庭库存/过期/采购/家务 | catalog、inventory、task | stock/lot/location/expiry/quantity 的领域模型 | ❌ 不运行 | 设计参考；以后可做**CSV 库存导入** |
| HomeBox（Go；家庭物品/位置） | Go；家庭库存 | catalog、inventory | 位置层级、标签、附件、物品字段 | ❌ 不运行 | 设计参考；核对当前仓库/许可证 |
| [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) | Django + OCR；文档管理 | intake | 上传/OCR/重试/元数据/任务状态 | ❌ 不运行 | 设计参考；以后可做**外部 OCR adapter**，不共享 DB |
| [NetBox](https://github.com/netbox-community/netbox) / [Pretix](https://github.com/pretix/pretix) | Django；大型业务系统 | core 结构 | app 边界、迁移、admin、权限、插件边界 | ❌ 不运行 | 只看结构；不抄插件体系/复杂权限 |
| [Baby Buddy](https://github.com/babybuddy/babybuddy) | Django；婴儿记录 | health（以后） | 喂养/睡眠/成长记录的数据模型 | ❌ 不运行 | 以后做 health 时参考；高隐私 |
| [Home Assistant](https://www.home-assistant.io/) | 设备/自动化平台 | — | 通知/设备接入思路 | ❌ 不做 | 不是我们的领域；最多 webhook 通知 |
| [n8n](https://n8n.io/) / Node-RED | 通用工作流 | — | 触发器/节点 | ❌ 不做 | 我们的 Agent 更窄；引入会变重 |
| [Open Food Facts](https://openfoodfacts.github.io/openfoodfacts-server/api/) | 开放食品/条码数据 | intake、catalog | 条码/产品字段 | ✅ 外部 API（可选） | P3 以后做条码查询；注意 ODbL 署名/缓存 |
| [schema.org Recipe](https://schema.org/Recipe) | 词表/标准 | recipe | 菜谱导入/导出字段 | ✅ 标准 | 需要导入/导出时用；不强制全字段 |
| [iCalendar RFC 5545](https://datatracker.ietf.org/doc/html/rfc5545) | 日历标准 | meal_plan、task | 导出日历 | ✅ 标准 | 以后做日历导出时用 |

> 许可证提醒：上面不少是 AGPL/GPL 项目（以仓库 LICENSE 为准）。**不要复制代码进我们的项目**；独立运行 + API 调用也要核对许可证/分发方式。只用设计思路最安全。

---

## 3. 融合方式（具体）

### 3.1 一次性导入（优先）

适合：你已经在用 Mealie / Tandoor / Grocy / HomeBox，想把数据搬过来。

```text
外部导出（JSON/CSV/API）
  → 我们的 import 脚本
  → 映射到 catalog/recipe/inventory
  → dry-run 预览
  → 确认后写入（幂等）
```

规则：

- 导入放 `integration` 模块，不直接写别的模块表；调 public service。
- 先 dry-run，输出“将新增/跳过/冲突”数量。
- 保留 `source` / `external_id` 字段，方便重跑/对账。
- 只做一次性，不做双向同步；避免双写。

### 3.2 运行时 API（少而明确）

适合：外部服务提供我们不想自建的能力，例如条码查询、OCR、通知。

```text
我们的模块 → adapter（超时/重试/错误映射）→ 外部 API
```

规则：

- 不共享 DB；不把外部 ID 当主键。
- adapter 在 `platform/`，业务模块只依赖接口。
- 外部失败不影响核心；有降级/超时。
- 许可证/隐私/成本先评估；能缓存就缓存。

### 3.3 设计参考（最常用）

- 读它的**表结构/关系**，画成我们自己的模型。
- 读它的**边界**：哪些模块管什么、哪些是 adapter。
- 读它的**失败处理**：任务、重试、状态。
- 不复制代码、不复制它的多租户/权限/插件体系。

### 3.4 不采用“第二个全功能 App”

- 运行 Mealie/Tandoor 替代我们的 recipe：会多一套 auth/DB/备份/升级，且和单一写者冲突。
- 运行 Paperless 替代 intake：同理；以后最多做外部 adapter。
- 运行 Home Assistant/n8n：不是我们的领域，增加运维面。

---

## 4. 可以直接用的（第一批）

| 类型 | 选择 | 用途 |
|---|---|---|
| 框架 | Django 5.2 + DRF + drf-spectacular | core API/Admin/OpenAPI |
| 框架 | FastAPI + Pydantic v2 | AI API/schema |
| 数据库 | PostgreSQL 16 | 业务 + AI schema |
| 扩展 | pgvector | RAG 向量 |
| RAG | LlamaIndex | 摄取/检索/回答 |
| Agent | pi-agent（官方链接待补） | 入口 Agent |
| Web | Next.js + TanStack Query | 前端 |
| 质量 | pytest / ruff / mypy / import-linter | 测试/质量/边界 |
| 可选 | Caddy / MinIO | TLS / 对象存储（以后） |

> 这些是“库/扩展”，不是“完整 App”。新增依赖前先看：标准库/框架能不能做？维护/许可证/体积是否可接受？

---

## 5. 许可证与运维检查

直接依赖或外部 API 前，至少确认：

- LICENSE 是否允许我们的使用/分发方式；
- 最近 6 个月是否有维护/安全更新；
- 是否需要额外服务/账号/密钥；
- 数据是否出境/是否用于训练；
- 备份/恢复是否多一套；
- 出问题能否替换/降级。

---

## 6. 第一批决策

| 问题 | 现在 | 以后 |
|---|---|---|
| 运行 Mealie/Tandoor？ | 不 | 不；最多一次性导入 |
| 运行 Grocy？ | 不 | 不；最多 CSV 导入 |
| 运行 Paperless？ | 不 | 可做外部 OCR adapter |
| 用 Open Food Facts？ | 不 | P3 以后条码查询 |
| 用 schema.org Recipe？ | 不强制 | 导入/导出时用 |
| 用 Home Assistant/n8n？ | 不 | 最多 webhook 通知 |
| 直接依赖 pi-agent/LlamaIndex？ | 是 | 是 |

---

## 7. 需要你确认

1. 你现在是否已经在用 Mealie / Tandoor / Grocy / HomeBox？如果有，数据导出格式是什么？
2. 你更想“自己重做一遍学习”，还是“先把旧数据导进来用起来”？
3. 条码/食品数据（Open Food Facts）对你重要吗？还是先手工录入？
4. 哪些外部服务你不想引入（隐私/运维/成本）？
