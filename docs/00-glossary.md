# 00 · 名词解释（大白话版）

> 不追求学术定义；先能看懂、能用。遇到新词继续往这里加。

---

## Schema（数据结构）

**一句话**：数据长什么样——有哪些字段、每个字段是什么类型、必填还是可选、有什么限制。

就像一张表的表头：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | UUID | 是 | 唯一标识 |
| name | 文本 | 是 | 物品名 |
| quantity | 数字 | 是 | 数量，≥0 |
| unit | 文本 | 是 | 个/盒/瓶 |
| expires_at | 日期 | 否 | 过期日 |

同一个词在不同地方：

- **数据库 schema**：表、列、类型、约束、外键。
- **API schema**：请求/响应里有哪些字段（OpenAPI / JSON Schema）。
- **工具 schema**：AI 调用工具时，参数长什么样（Pydantic / JSON Schema）。

> Schema 不是“数据库”本身，是**数据的形状**。改形状要用迁移（migration），不要手改线上表。

## Migration（迁移）

改 schema 时的一次性脚本：加字段、改类型、建表。
Django 用 migrations，AI 服务可能用 Alembic。**不要手动改生产表**。

## API / Endpoint

- **API**：程序之间说话的接口。
- **Endpoint**：一个具体的地址，比如 `POST /api/v1/items`。

## Contract（契约）

两边约定好的“怎么调用、传什么、返回什么、错了怎么办”。
Schema 是契约的一部分；OpenAPI 是常见的契约格式。

## DTO（Data Transfer Object）

跨模块/跨服务传的数据对象。
只带数据，不带数据库行为；不要把 ORM 对象直接传出去。

## ORM

用 Python 对象操作数据库表，比如 Django Model / SQLAlchemy Model。
`models.py` 里定义表；不要跨模块 import 别人的 models。

## Module（模块）

一个功能目录，自包含：接口、契约、服务、表、测试、README。
本项目的模块是 vertical slice，不是“controller/service/repository”三层空壳。

## Vertical slice（垂直切片）

按“一个功能”切，而不是按技术层切。
一个模块从 API 到表都自己管；新功能 = 新目录 + 注册一行。

## Adapter（适配器）

把外部服务/旧接口包一层，让业务代码不感知细节。
比如 `core_client` 包 home-core API；`feishu` 包飞书 API。

## Idempotency（幂等）

同一个请求重复执行，结果一样。
写操作常用 `Idempotency-Key`；重试不会重复入库。

## Confirmation token（确认令牌）

AI 提议一个写操作，人点“确认”后，用一个一次性 token 真正执行。
token 有有效期、只能用一次；比“模型直接写”安全。

## RAG

先检索资料，再让模型**基于资料**回答，并给出引用。
适合“为什么/怎么办”；不适合“库存还有几个”这种精确数据。

## Agent / Tool calling

Agent：模型根据目标决定下一步。
Tool calling：模型选择调用某个函数（工具），并给出参数；工具 schema 定义参数。

## Embedding / Vector

把文本变成一串数字，用于“语义相似”检索。
pgvector 是 PostgreSQL 的向量扩展。

## OpenAPI / JSON Schema

- **OpenAPI**：描述 HTTP API 的标准（路径、参数、响应）。
- **JSON Schema**：描述 JSON 数据形状的标准。

## Monolith / Modular monolith / Microservice

- **Monolith**：一个程序。
- **Modular monolith**：一个程序，但内部按模块切开。
- **Microservice**：多个独立服务，各自部署/数据库。

本项目是 **3 个程序 + 模块化单体**，不是微服务。

## Single writer（单一写者）

每类数据只有一个入口能改。
比如库存只能经 core API 改；AI 只能写自己的草稿/索引。

## P95

100 个请求里，95 个比这个值快。
比“平均值”更能反映卡顿体验。

## CI

每次提交自动跑检查（lint、测试、构建）。
本项目的架构图用 `make check` 验证。

---

> 还有不懂的词，直接加到这张表；不要让术语变成门槛。
