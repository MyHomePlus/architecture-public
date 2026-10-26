# 11 · 开发规范与 AI 限制

> 这是后续所有代码仓库的**基础原则**。不是建议，是默认规则；例外要写理由。
> 配套：`AGENTS.md`（AI 施工规则）、`docs/09-anti-overengineering.md`（复杂度预算）、`home-core/AGENTS.md`（当前仓库规则）。

---

## 1. 仓库边界

| 仓库 | 内容 | 不放进 |
|---|---|---|
| `architecture-public` | 架构图、决策、模块规范、开发标准（脱敏版） | 业务代码、真实数据、私有笔记 |
| `home-core` | Django 业务核心（当前 P1：catalog + inventory） | AI/菜谱/登录（未到阶段） |
| `home-ai` | 后续 FastAPI AI 服务 | 业务真相数据 |
| `home-web` | 后续 Next.js 前端 | 业务规则 |

---

## 2. 开发流程

```text
场景/验收
  → 查架构边界与现有模块
  → 写/改一个模块（contracts → services → models → api → tests）
  → 跑测试 / lint / OpenAPI
  → 更新模块 README + 开发日志
  → 一个清晰 commit
```

规则：

- **一次只做一个切片**；不跨模块顺手重构。
- **先写/改测试**（至少 service + API 各一个）。
- **先最小实现**；抽象等第二次/第三次重复再抽。
- **不把设计写成上线**；没跑过的命令/指标不写。
- 任何改变架构形状的决定，先写 ADR 或在 `docs/03-decisions.md` 增加一条。

---

## 3. 代码规范

### 模块

- 一个模块一个目录：`api / contracts / services / models / events / tests / README`。
- 只有 `contracts.py` + `services.py` 是 public；其他模块不能 import `models.py`。
- 不跨模块 FK/JOIN；跨模块只传 DTO / ID。
- `reporting` 是唯一只读跨模块例外（以后）。
- 新模块 = 新目录 + 注册一行；不预创建空模块。

### 数据

- 表归模块所有；migration 只改自己的表。
- 主键 UUID；时间戳；需要时 `version`/`deleted_at`。
- 业务数量用 `decimal`；单位单独存；不隐式换算。
- 不手动改线上表；改结构用 migration。
- 关键约束放 DB（`CheckConstraint` / unique），不只靠 Python。

### API

- DRF/FastAPI 的 schema 是契约；用 OpenAPI 生成 client。
- 统一错误格式：
  ```json
  {"error": {"code": "...", "message": "...", "details": {}, "trace_id": ""}}
  ```
- 写接口：actor、幂等键（有重复风险的）、版本冲突（需要时）。
- 列表返回 `{items, total}`；P1 不分页，P2 以后按需。
- 不在 API 层写业务规则；调 service。

### 测试

- service：业务规则/失败路径。
- API：状态码/契约/至少一个 happy path + 一个失败 path。
- 测试用 SQLite in-memory（P1）；目标库 PostgreSQL 要有一次 smoke。
- 不追 100% 覆盖率；不测私有实现。

### 错误与日志

- 只在边界校验；内部信任类型/约束。
- 不 `except Exception: pass`；不吞异常。
- DomainError 在 `app/shared/errors.py` 统一映射。
- 日志记录边界/状态变化/错误；不要每个函数都 log。

### Git

- 分支：`main`；一个 commit 一个主题。
- 提交信息：Conventional Commits，例如 `feat(inventory): add quick add`。
- 提交前：`git diff --check`、测试、lint。
- 不提交 `.env`、真实数据、密钥、本机路径、构建产物。
- 公开仓库作者用 noreply 邮箱。

---

## 4. AI 限制（硬规则）

### 默认预算

- **0 新服务、0 新依赖、0 新抽象**；需要时写一句“为什么不能更简单”。
- 没有 ≥2 个真实实现/明确测试缝，不抽 interface/base/factory/strategy。
- 模块模板只建当前用到的文件；空目录/空接口/空 base class 不建。

### 不许做

- 不新增 API Gateway / LLM Gateway / 消息队列 / K8s / 多租户。
- 不跨模块 import models；不建跨模块 FK/JOIN。
- 不修改/删除 append-only 流水；只能追加冲正。
- 不宽泛 try/except；不吞异常；不重复校验。
- 不为了“以后可能用”加配置/Feature Flag/插件。
- 不写空模块/空测试/占位 README。
- 不伪造测试结果、指标、引用；没跑就说没跑。
- 不把真实家庭数据、账号、密钥、个人路径写进代码/日志/commit。
- 不擅自改架构决策；需要时先开 ADR/讨论。

### 遇到不确定

先问，不要猜：

- 业务规则不明确（单位、去重、低库存阈值）
- 需要新依赖/新服务/新表
- 要跨越模块边界
- 要改 API 契约/数据结构
- 要删历史数据/流水

---

## 5. Completeness（完工检查）

- [ ] 只改一个模块/一个主题
- [ ] 模块边界未破（无跨模块 models/FK/JOIN）
- [ ] migration 只改本模块表
- [ ] service 测试 + API 测试
- [ ] `pytest` 通过
- [ ] `ruff check` 通过
- [ ] OpenAPI 能生成
- [ ] 模块 README 更新（接口/表变化）
- [ ] `DEVELOPMENT_LOG.md` 更新
- [ ] commit message 清晰
- [ ] 无 PII/密钥/真实数据

---

## 6. 开发日志与 AI 交接

每个代码仓库必须有 `docs/DEVELOPMENT_LOG.md`，最新在最上面。每次结束写：

```markdown
## YYYY-MM-DD · <slice>
- 目标：
- 改了：
- 验证（命令 + 结果）：
- 没做/风险：
- 下一步：
- 不要碰：
```

交接给 AI 时，只给：

1. 本文件 + 仓库 `AGENTS.md`
2. 当前模块 README / contracts / services
3. 相关测试
4. 当前错误/下一步

不要把整个仓库/聊天记录塞进上下文。

---

## 7. 当前阶段（P1）

- `home-core`：catalog + inventory 已完成；下一步最小 Web。
- `home-ai` / `home-web`：还没开始；不要提前写。
- 公开版只同步脱敏后的架构、决策、规范；真实数据与私有笔记不进入本仓库。

---

## 8. 例外

如果需要突破以上规则：

1. 在 `docs/decisions/` 写 ADR：问题、备选、为什么简单方案不够、代价、回滚。
2. 先做最小 spike，验证后再进主分支。
3. 加一条测试/检查，防止以后退化。
4. 两周后没人用，删掉。
