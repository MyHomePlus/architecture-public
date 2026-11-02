# 01 · Overview

> Goals, constraints, the layered model, the three programs, and the current boundary.
> Assistant model: [`12-assistant-architecture.md`](12-assistant-architecture.md).
> Modules: [`02-modules.md`](02-modules.md). Decisions: [`03-decisions.md`](03-decisions.md).

---

## 1. Goals

1. **One person can maintain it.** A real household, not a demo.
2. **Scenarios compose.** New life scenarios become skills first; only persistent domains become modules.
3. **Boundaries can move.** Modular monolith now; extract by module only when a real trigger appears.
4. **AI is useful but bounded.** AI produces drafts/proposals; humans confirm; the core API is the only business write path.
5. **Data is trustworthy.** One writer per domain, append-only where history matters, and drafts are not truth.

### Non-goals

- Multi-tenant SaaS, billing, public registration.
- A complete ERP / medical / security system.
- RBAC/OIDC/JWT, Kubernetes, event bus, formal approval workflow, SLA/on-call.
- A multi-agent runtime, vector database, or API/LLM gateway before a real need.
- One microservice per table.

---

## 2. Constraints

| Constraint | Effect |
|---|---|
| One developer + code agents | Modules must be self-contained; rules must be mechanically checkable |
| One household, low concurrency | One PostgreSQL is enough |
| Sensitive family data | Local-first; minimal external model input |
| Small budget | Start with 3 containers; add Redis/MinIO/Caddy only on demand |
| Learning goals | Django for transactional core/Admin; FastAPI for async/AI |

---

## 3. Layered view

```text
L5  Domain assistants    Inventory · Meal · Shopping · Reminder
L4  Life skills          Each skill belongs to exactly one assistant
L3  Domain services      Shared reads; writes stay in the owning domain
L2  Atomic capabilities  OCR/ASR · LLM · rules · scheduler · notifications
L1  Platform base        home-core · home-ai runtime · PostgreSQL · files · jobs
```

This is a **composition view**, not a deployment view. See [`12-assistant-architecture.md`](12-assistant-architecture.md).

---

## 4. 三个部署单元

| Program | Tech | Responsibility | Failure impact |
|---|---|---|---|
| `home-web` | Next.js / TS | assistant workspace, forms, draft review, confirmations | UI unavailable; APIs remain |
| `home-core` | Django + DRF | business source of truth, Admin, data access | writes unavailable; reads may cache |
| `home-ai` | FastAPI | local perception, structured AI output, future assistants/skills | AI features degrade; core remains |

**Why not 4 services?** The four assistants are domain scopes inside `home-ai`, not independent deployables. They do not need separate scaling, permissions, or failure domains yet.

**Why two backends?** Django is a better fit for transactional CRUD/Admin; FastAPI is a better fit for async/model calls. They have different failure domains.

---

## 5. Domain modules (current)

| Module | Responsibility | Tables | Depends on |
|---|---|---|---|
| `catalog` | items, categories, locations | `catalog_*` | shared |
| `inventory` | lots, append-only movements, low stock | `inventory_*` | catalog |
| `recipe` | recipes, JSON ingredients/steps/tags | `recipe_*` | shared |
| `meal_plan` | weekly plan, day dishes, immutable meal records | `meal_plan_*` | recipe |
| `shopping` | dynamic purchase items | `shopping_*` | meal_plan, recipe (read only) |
| `task` (next) | tasks, reminders | `task_*` | shared |

Rules:

- Modules own their tables and transactions.
- Cross-module calls use public services/contracts; no model imports, FKs, or JOINs across modules.
- `reporting` is the only read-only cross-module exception.

---

## 6. Data ownership

One PostgreSQL, two schemas:

| Schema | Owner | Contains |
|---|---|---|
| `core` | `home-core` | catalog, inventory, recipe, meal_plan, shopping, task, audit |
| `ai` | `home-ai` | intake drafts, future assistant actions, jobs, knowledge index |

- Core writes go only through the core API.
- AI writes only its own schema.
- Cross-service references store IDs; no cross-schema JOIN.
- Local disk first; object storage only when needed.

---

## 7. Contracts and write path

- Core API: OpenAPI 3.1; generated web/AI clients.
- AI API: OpenAPI 3.1; perception/drafts/future assistant actions.
- Cross-module: `contracts.py` + `services.py`, DTOs/IDs only.
- Tool/skill contracts: typed input/output + risk + confirmation policy.

Write path:

```text
human / scheduled trigger
  → domain assistant (future)
  → skill (future)
  → proposed action / draft
  → human confirmation
  → core API
  → core schema
```

No AI process writes `core` directly.

---

## 8. Current state

Implemented:

- inventory ledger, quick add, low stock, admin;
- local OCR/ASR + DeepSeek structured intake;
- recipe library (37 imported recipes / 249 ingredients);
- weekly multi-dish plans, draft/confirm, immutable meal records;
- dynamic shopping list, decoupled from inventory;
- manual kitchen Web.

Designed, not implemented:

- domain assistant runtime and `assistant_action`;
- task/jobs/notifications;
- recipe/shopping voice import;
- Feishu channel;
- knowledge and multi-step orchestration.

---

## 9. Roadmap

| Scenario | State |
|---|---|
| S1 one-sentence inventory | ✅ |
| S2 weekly meals | ✅ manual path |
| S3 shopping / replenishment | ✅ manual path |
| S4 reminders | ⬜ next |
| S5 domain assistants | 🟡 design |
| S6 knowledge / multi-step | ⬜ later |

See [`08-roadmap`](../diagrams/08-roadmap.puml).
