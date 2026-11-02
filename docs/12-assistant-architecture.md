# 12 · Assistant Architecture

> Status: **design accepted; runtime not implemented yet** (2026-11)
> Goal: a lightweight AI life assistant built from shared capabilities, composable skills, and isolated domain assistants.

---

## 1. The five layers

```text
L5  Domain assistants    Inventory · Meal · Shopping · Reminder
L4  Life skills          Each skill belongs to exactly one assistant
L3  Domain services      Shared reads; writes stay in the owning domain
L2  Atomic capabilities  OCR/ASR · LLM · rules · scheduler · notifications
L1  Platform base        home-core · home-ai runtime · PostgreSQL · files · jobs
```

This is a **composition view**, not a deployment view. The runtime is still 3 programs: `home-web`, `home-core`, `home-ai`.

### Layer ownership

| Layer | Owns | Code |
|---|---|---|
| L5 assistants | domain scope, context, tool allowlist | `home-ai/assistants` + Web surfaces |
| L4 skills | a repeatable life workflow | `home-ai/skills/<assistant>` |
| L3 domain services | data, business rules, transactions | `home-core/modules` |
| L2 capabilities | replaceable primitives | `home-ai/platform` |
| L1 platform | processes, DB, files, jobs, model runtime | deployment + platform |

---

## 2. Assistants are isolated domains

```text
Inventory assistant  → capture, stock, locations
Meal assistant       → recipes, weekly plans, meal records
Shopping assistant   → dynamic purchase list
Reminder assistant   → tasks, due/low-stock reminders
```

Rules:

1. **No assistant-to-assistant calls.** There is no hidden master assistant.
2. **No shared conversation, context, or tool allowlist.** Each assistant has its own scope.
3. **Shared reads are allowed.** A meal assistant may read inventory availability; a shopping assistant may read a meal week.
4. **Writes stay in the owning domain.** The meal assistant writes meal plans, not shopping items.
5. **Cross-domain actions are explicit.** The user switches assistants; no implicit multi-assistant orchestration.
6. **UI may aggregate cards.** A home screen can show several assistants, but that is presentation, not mutual awareness.

### Why not one omniscient assistant?

A single assistant with every tool and every context is easy to demo and hard to keep correct. It creates:

- unclear ownership;
- a growing prompt/context budget;
- cross-domain side effects;
- tool permissions that are too broad.

Domain isolation sacrifices some “one-shot” convenience for explainability and safe evolution. A thin channel router may route an entry to one assistant; it must not reason across domains.

---

## 3. Data sharing without assistant coupling

```text
Assistant A ──read──► shared domain read contract
Assistant B ──read──► shared domain read contract
Assistant A ──write─► its own domain ──► core API
```

Examples:

- Meal assistant reads inventory availability to suggest dishes; it does not update stock.
- Shopping assistant reads the current meal week to generate a shopping draft; it does not edit the menu.
- Reminder assistant reads due dates / low-stock projections; it does not change inventory.
- Inventory assistant writes stock movements; it does not invoke the meal assistant.

Shared data lives at **L3 domain services** (and L2/L1 capabilities). It is not a shared assistant memory.

---

## 4. Action lifecycle

The target runtime introduces a server-side action record:

```text
assistant_action
  id
  assistant_name   inventory / meal / shopping / reminder
  channel          web / feishu / scheduler
  skill_name
  skill_version
  input_json
  context_json
  draft_json
  diff_json
  risk_level
  status           proposed / confirmed / executed / failed / expired
  idempotency_key
  trace_id
  created_at / confirmed_at / executed_at / error
```

Flow:

```text
user / scheduled trigger
  → domain assistant
  → skill
  → proposed action / draft
  → human confirms
  → owner executor calls core API
  → executed / failed
```

Important:

- AI never writes `core` directly.
- An action has one owner assistant; another assistant cannot confirm or execute it.
- Confirmation is idempotent.
- Drafts expire; they are not business truth.
- Current implementation still uses browser-local drafts for intake; the server-side action store is a target, not shipped.

---

## 5. Skill contract

Each life skill should be a versioned unit, not a new service:

```text
name / version
owner assistant
triggers
context sources
allowed tools
input/output schema
risk level
confirmation policy
evaluation cases
```

First candidate skills:

| Skill | Owner | Composes |
|---|---|---|
| `capture_inventory` | Inventory | perception + inventory |
| `plan_week_menu` | Meal | recipe + meal_plan + rules (+ optional LLM) |
| `replenish_shopping` | Shopping | meal_plan + shopping + inventory read |
| `remind` | Reminder | task + scheduler + notifications |

Skills never own tables. Persistent state belongs to a domain module.

---

## 6. What is implemented vs designed

Implemented:

- inventory ledger, quick add, low stock;
- local OCR/ASR + DeepSeek structured intake;
- recipe library (37 imported recipes, 249 ingredients);
- weekly multi-dish meal plans + immutable meal records;
- dynamic shopping list, decoupled from inventory;
- manual kitchen web UI.

Designed, not implemented:

- domain assistant runtime;
- `assistant_action` server state;
- task/jobs/notification loop;
- recipe and shopping voice import;
- Feishu channel adapter;
- knowledge assistant;
- multi-step orchestration.

---

## 7. Tradeoffs

| Choice | Cost | Benefit |
|---|---|---|
| Domain assistants isolated | some cross-domain requests need explicit switches | clear ownership, smaller context/tool scope |
| Shared domain reads | potential duplicate query logic | no assistant-to-assistant coupling |
| AI drafts only | one confirmation step | no model errors directly in the ledger |
| Layered view | can hide deployment/data boundaries | easy to explain capability → skill → assistant |
| 3 programs | shared failure domain for AI modules | far less ops than microservices |

The layered view is intentionally paired with module, write-path, data-ownership, and deployment views. No single diagram tells the whole story.
