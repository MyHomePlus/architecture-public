# 02 · Modules, Skills, and Capabilities

> Decision rule: **new life scenario → skill; new persistent domain → module; new reusable primitive → capability.**
> A skill belongs to one domain assistant; assistants do not call each other.

---

## 1. Three different things

| Thing | What it is | Owns tables? | Example |
|---|---|---|---|
| Capability | replaceable primitive | usually no | OCR, ASR, LLM, rules, scheduler, notify |
| Domain service | business truth and rules | ✅ | inventory, recipe, meal_plan, shopping, task |
| Life skill | versioned workflow composing domain + capabilities | ❌ | capture_inventory, plan_week_menu |
| Domain assistant | user-facing scope, context, tool allowlist | ❌ | inventory / meal / shopping / reminder |

Do not turn every scenario into a Django app.

---

## 2. Module anatomy

A domain module is a vertical slice:

```text
modules/<name>/
├── README.md
├── api.py
├── contracts.py
├── services.py
├── models.py
├── migrations/
└── tests/
```

Public boundary:

- `contracts.py` — DTOs/Protocols; no ORM imports.
- `services.py` — application service; transaction boundary; returns DTOs.
- `models.py`, migrations, admin — internal.
- Cross-module: no model import, no FK, no JOIN; use IDs/DTOs and public services.

`reporting` is the only read-only cross-module exception.

---

## 3. Domain modules

| Module | Owns | Depends on |
|---|---|---|
| `catalog` | items, categories, locations | shared |
| `inventory` | lots, movements, stock projection | catalog |
| `recipe` | recipes, JSON ingredients/steps/tags | shared |
| `meal_plan` | weekly plan, dishes, meal records | recipe |
| `shopping` | dynamic purchase items | meal_plan/recipe read |
| `task` (next) | tasks, reminders | shared |

Rules:

- One module owns one set of tables.
- A module's service method is one transaction boundary by default.
- Cross-module read is allowed through public services; cross-module write is not hidden behind a model import.
- `shopping` never queries or mutates inventory.

---

## 4. Life skills

A skill is a versioned workflow, not a service:

```text
name / version
owner assistant
triggers
context sources
allowed tools
input/output schema
risk level
confirmation policy
eval cases
```

Candidate skills:

| Skill | Owner | Composes |
|---|---|---|
| `capture_inventory` | Inventory | perception + inventory |
| `plan_week_menu` | Meal | recipe + meal_plan + rules (+ optional LLM) |
| `replenish_shopping` | Shopping | meal_plan + shopping + inventory read |
| `remind` | Reminder | task + scheduler + notify |

A skill may read shared data. It must not call another assistant or write another domain.

---

## 5. Growth rules

1. **Add a skill** when a user-facing life workflow is missing.
2. **Add a module** only when there is persistent data + its own lifecycle/transaction.
3. **Add a capability** when a primitive is reused by multiple skills.
4. **Do not add a service** until a real deploy/scale/permission boundary appears.
5. **Do not create empty modules** for future ideas.

### Decision tree

```text
new request
├─ needs a new table / transaction / lifecycle? → module
├─ composes existing domain + capabilities?      → skill
├─ reusable primitive (OCR, LLM, rules)?        → capability
└─ just a UI/query?                             → page / read model
```

---

## 6. Assistant boundaries

- Assistants do not call each other.
- They do not share conversations, context, or tool allowlists.
- Shared reads go through domain read contracts.
- Writes stay in the owning domain and go through the core API.
- A thin channel router may select an assistant; it must not reason across domains.
- The home screen may aggregate cards, but that is UI aggregation.

See [`12-assistant-architecture.md`](12-assistant-architecture.md).

---

## 7. Current modules

Implemented:

```text
catalog / inventory / recipe / meal_plan / shopping
```

Next:

```text
task / reminder
```

Later, only on real need:

```text
knowledge / reporting / integration / plants / budget / journal
```

---

## 8. Non-goals

- No microservice per module.
- No event bus for in-process side effects.
- No multi-agent orchestration.
- No generic workflow engine.
- No shared ORM/domain model across `home-core` and `home-ai`.
