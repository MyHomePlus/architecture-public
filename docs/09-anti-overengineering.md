# 09 · 复杂度预算与 AI coding 规则

> 这份不是“架构规范大全”，而是给**单人 + AI** 的减法规则：
> 默认做最小实现；每加一层抽象/依赖/服务，都要说清“为什么不能更简单”。
> 规则是默认值，不是法律；例外可以，但要在 PR / ADR / 模块 README 里写一句理由。

---

## 1. 复杂度预算

| 项目 | 默认预算 | 超出时 |
|---|---|---|
| 部署单元 | 3 个（web/core/ai） | 写 ADR；先证明失败域/扩缩容差异 |
| 数据库 | 1 个 PostgreSQL | 先加 schema；不要加第二个 DB |
| 业务写入口 | 1 个（core API） | 不允许；AI 只写自己的 schema |
| 新服务 | **0** | 先证明“模块内做不了” |
| 新依赖 | **0**（标准库/框架优先） | 一句话理由 + license/维护检查 |
| 新抽象（interface/base/factory/strategy） | **0**，除非 ≥2 个真实实现或明确测试缝 | 先写最小实现，重复 3 次再抽 |
| 新配置/Feature Flag | **0**，除非真的要多环境/多值 | 不要为一次需求加开关 |
| 模块初始文件数 | 8–10 个以内 | 超过先删空文件/合并层 |
| 单个 service | 先 ≤ ~300 行 | 按用例拆，不按“层”拆 |

> “默认 0”不是永远不做，而是**先不做**；需要时再付成本。

---

## 2. AI coding / vibe coding 常见问题 → 规则

| 常见问题 | 症状 | 规则 |
|---|---|---|
| **过度防御** | 每层都 try/except、重复校验、null 检查满天飞 | **只在边界校验**（API/外部输入/DB 约束）；内部调用信任类型/约束；只 catch 能处理的异常 |
| **模板过大** | 一个模块生成 20 个空文件、base class、接口、factory | 模板只保留**当前用到的文件**；没有实现的接口/空目录不要建 |
| **无效抽象** | `BaseRepository[T]`、`BaseService`、`AbstractFactory` | 没有 ≥2 个真实实现/明确测试缝，不抽；先写直接代码 |
| **过度分层** | DTO → Entity → Domain → Repository → Service → Controller，5 层 | 一个模块最多：`api → services → models`；需要时再加 `domain/contracts` |
| **重复校验** | Pydantic/DRF 校验了，service/model 再校验一遍 | 边界校验一次；DB 用 constraint 兜底，不写重复 Python 检查 |
| **防御性复制** | 每个函数都 deep copy/list copy | 内部数据默认不可变/只读；边界再复制 |
| **吞异常** | `except Exception: pass` / 返回默认值掩盖错误 | 不吞；边界转成统一错误；记录一次日志 |
| **全链路重试** | 每层都 retry/timeout，写操作也重试 | 只在 adapter/边界做；只对幂等读重试；写不盲目重试 |
| **日志噪音** | 每个函数入口/出口都 log | 边界、状态变化、错误、关键决策才 log |
| **测试实现** | mock 一切、断言内部调用次数 | 测行为/输入输出/边界；少 mock；模块集成测试优先 |
| **追求覆盖率** | 为 getter/框架代码写测试 | 测关键路径/失败路径；不追 100% |
| **注释复述代码** | `# 获取用户` 在 `get_user()` 上 | 注释写**为什么/取舍**；不写“是什么” |
| **文档膨胀** | 一个 CRUD 写 17 张图/5 份 ADR | 只写能改变决策的内容；模块 README 一页 |
| **过度配置** | 每个常量都进 env/feature flag | 配置只放环境差异/密钥；业务常量放代码 |
| **提前优化** | 先上缓存/队列/分库，没量测 | 先跑通；有数字再优化 |
| **顺手重构** | 改 A 模块顺便重命名 B/C | 一次只改一个模块；重构单独提交 |
| **造轮子** | 自己写日期/校验/HTTP/重试库 | 标准库/框架优先；新依赖先评估 |
| **AI 幻觉依赖** | 引入不存在的 API/包/配置 | 只依据官方文档/pin 版本；跑测试/构建验证 |
| **生成大段样板** | 复制 200 行模板/示例代码 | 只保留最小可运行片段；删无关代码 |

---

## 3. 硬规则（默认遵守）

1. **边界校验**：API 入参、外部 API 返回、文件输入；内部调用不重复校验。
2. **一个错误出口**：API 层统一错误格式；service 抛领域错误；不在每层包 try/except。
3. **没有 2 个实现，不抽接口**；没有 3 次重复，不抽 helper。
4. **新文件/新依赖/新服务/新抽象**：默认 0；加之前写一句“为什么不能更简单”。
5. **一个改动只碰一个模块**；不顺手重构无关文件。
6. **模板最小化**：只建当前需要的文件；空目录/空接口/空 base class 不建。
7. **测试行为**：输入/输出/失败/边界；不测私有实现/调用次数。
8. **注释写 why**：为什么这样、代价是什么；不复述代码。
9. **先删后加**：死代码/注释代码/未用配置直接删。
10. **先量测后优化**：没有数字，不上缓存/队列/并发优化。

---

## 4. 好 / 坏例子

### 坏：一个 todo 的 5 层

```text
TodoController → TodoService → TodoRepository → TodoEntity → TodoDTO
+ ITodoRepository + BaseRepository[T] + TodoMapper + TodoFactory
```

问题：没有第二个实现，抽象没有收益；改一个字段要动 6 个文件。

### 好：一个 todo 的最小实现

```python
# api.py
@router.post("/tasks")
def create_task(payload: TaskCreate, svc: TaskService = Depends()):
    return svc.create(payload)

# services.py
def create(self, payload: TaskCreate) -> TaskView:
    task = Task.objects.create(**payload.model_dump())
    return TaskView.model_validate(task)
```

需要时再加：权限、事件、审计；不需要时不加。

### 坏：过度防御

```python
try:
    user = get_user(uid)
except Exception:
    return None
if user is None:
    return None
if not user.name:
    return None
```

问题：吞了真实错误；调用方不知道发生了什么。

### 好：边界处理

```python
user = get_user(uid)          # 不存在 → NotFoundError
if not user.name:             # 业务规则 → 明确错误
    raise DomainError("user.name_required")
```

### 坏：事件总线 for one handler

```text
StockChanged → EventBus → Redis Stream → Consumer → Task
```

只有一个消费者时，直接调用 `task_service.create_low_stock_task()` 更简单；等第二个消费者再上事件。

---

## 5. 给 AI 的提示词

```text
先给最小可运行实现，不要新增抽象/依赖/空文件。
只改这个模块；不要顺手重构无关文件。
边界校验一次；内部不要重复校验/过度 try-except。
错误在 API 边界统一处理；不要吞异常。
先写/改行为测试；不要测私有实现。
如果新增文件、依赖、抽象、服务，先用一句话说明为什么不能更简单。
不确定的 API/配置，先查官方文档或问，不要猜。
```

### 代码 review 追问

- 这个功能家里真的会用吗？
- 有没有更简单的实现？
- 这个抽象有 2 个真实实现吗？
- 这个校验在边界做过吗？
- 这个依赖/服务非加不可吗？
- 这段代码 3 个月后还能看懂吗？
- 失败时会发生什么？会不会吞错？
- 有没有测试行为，而不是实现？
- 有没有顺手改无关文件？
- 有没有空文件/死代码/过度注释？

---

## 6. 停止规则

出现以下情况，先停，不要继续堆：

- 一个功能需要 **>1 个新服务** 或 **>2 个新依赖**；
- 模块还没被真实使用，文件数已经 **>10**；
- 为了一个需求写了 **>100 行基础设施**；
- 一个改动跨了 **3 个以上模块**；
- 你无法在 **一周内** 做出可演示的 slice；
- 你开始写“以后可能会用”的接口/配置/插件。

处理方式：写一页决策（问题/备选/取舍），或者先做一个 spike，再决定。

---

## 7. 不要过度简化掉的东西

- API 边界校验、DB constraint、迁移；
- 关键路径测试、备份/恢复；
- 错误格式、日志（边界/错误）；
- 异步/外部写的幂等；
- 模块 README、公开接口；
- 安全基础（密钥、输入、依赖）。

> 目标是**去掉无效复杂度**，不是去掉工程严谨性。

---

## 8. 例外流程

如果确实需要突破预算：

1. 在模块 README / ADR 写：问题、为什么简单方案不够、代价、回滚。
2. 先做最小 spike，验证后再进主分支。
3. 加一条测试/检查，防止以后退化。
4. 如果 2 周后没人用，删掉。
