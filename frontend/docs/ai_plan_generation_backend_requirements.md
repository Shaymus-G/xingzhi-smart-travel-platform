# AI 旅行计划生成 — 后端能力需求说明

> **文档类型**：前端 → 后端交接文档  
> **创建日期**：2026-07-28  
> **状态**：前端建议方案，非后端现有接口  
> **关联**：`frontend/src/pages/plan/generate.vue`、`frontend/src/api/ai.ts`、`frontend/src/api/request.ts`

---

## 一、当前问题

### 1.1 架构现状

```
前端 generate.vue
  → POST /api/ai/plans/generate (同步阻塞)
    → 等待 DeepSeek 生成完整计划
    → 写入数据库
    → 返回 TravelPlan JSON
```

### 1.2 核心问题

| 问题 | 影响 |
|------|------|
| `/api/ai/plans/generate` 是同步接口 | 前端必须等待整个 AI 生成过程完成，Render 冷启动 + DeepSeek 调用可能超过 120 秒 |
| 前端超时 ≠ 后端失败 | 前端 HTTP 超时断开后，后端可能继续执行并成功写入计划到数据库 |
| 无任务 ID | 前端无法在超时后精确查询"我刚刚提交的那个生成任务"的状态 |
| 无幂等机制 | 用户因超时重试会生成多条内容相同或相似的重复计划 |
| 前端通过计划列表匹配只能作为降级方案 | 匹配可能不精确（依赖 destination/days/created_at 组合判断），多设备同时生成时风险更高 |

---

## 二、建议后端能力

### 2.1 异步任务模式（P0 推荐）

将 `POST /api/ai/plans/generate` 改为异步模式：

**请求：**
```
POST /api/ai/plans/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "destination": "杭州",
  "days": 3,
  "budget": 3000,
  "travelers": 2,
  "preferences": ["自然风光", "本地美食"],
  "start_date": "2026-08-15",
  "notes": "节奏适中"
}
```

**建议响应（立即返回，不等待 AI 完成）：**
```json
{
  "code": 0,
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending"
  }
}
```

### 2.2 任务状态查询（P0 必需）

```
GET /api/ai/plans/generate/{task_id}
Authorization: Bearer <token>
```

**建议状态枚举：**

| 状态 | 含义 | 建议返回字段 |
|------|------|-------------|
| `pending` | 任务已接受，排队中 | `task_id`, `status`, `created_at` |
| `processing` | AI 正在生成中 | 同上 + `started_at` |
| `completed` | 生成成功 | 同上 + `plan_id`, `completed_at` |
| `failed` | 生成失败 | 同上 + `error_code`, `error_message`, `failed_at` |

**completed 响应示例：**
```json
{
  "code": 0,
  "data": {
    "task_id": "550e8400-...",
    "status": "completed",
    "plan_id": 42,
    "created_at": "2026-07-28T10:00:00Z",
    "completed_at": "2026-07-28T10:01:30Z"
  }
}
```

**failed 响应示例：**
```json
{
  "code": 0,
  "data": {
    "task_id": "550e8400-...",
    "status": "failed",
    "error_code": "AI_RESPONSE_PARSE_ERROR",
    "error_message": "DeepSeek 返回内容无法解析为结构化行程",
    "failed_at": "2026-07-28T10:02:00Z"
  }
}
```

### 2.3 幂等机制（P1 推荐）

支持客户端传入幂等键，同一用户 + 同一幂等键的重复请求不创建重复计划：

**请求：**
```json
{
  "destination": "杭州",
  "days": 3,
  "idempotency_key": "a1b2c3d4-..."
}
```

**行为：**
- 首次请求：正常创建任务
- 重复请求（相同 user_id + idempotency_key + 任务未过期）：返回已有任务的状态/结果
- 幂等键有效期：建议 30 分钟

### 2.4 任务生命周期建议

| 维度 | 建议值 | 说明 |
|------|--------|------|
| 轮询间隔 | 3-5 秒 | 前端轮询频率 |
| 任务最大等待时间 | 5 分钟 | 超过后标记为超时失败 |
| 幂等键有效期 | 30 分钟 | 同一键在此期间去重 |
| 客户端断开后是否继续 | **是** | AI 生成任务继续，避免浪费 |
| 是否支持取消任务 | 建议支持 | `DELETE /api/ai/plans/generate/{task_id}` |
| 完成任务重复查询 | 始终返回相同结果 | completed/failed 结果持久保留 |

### 2.5 plan_json 坐标回填（P0 推荐，关联问题四）

AI 生成 `plan_json` 时，根据 `resource_id` 从资源表查询并回填坐标字段：

```json
{
  "period": "morning",
  "resource_type": "scenic_spot",
  "resource_id": 6324,
  "name": "西湖",
  "address": "浙江省杭州市西湖区龙井路1号",
  "latitude": 30.2374470,   // ← 从 scenic_spots 表查询
  "longitude": 120.1409320,  // ← 从 scenic_spots 表查询
  "start_time": "09:00",
  "end_time": "12:00"
}
```

---

## 三、前端临时降级方案（已实现）

由于当前无后端异步任务和幂等能力，前端已实现以下降级方案：

### 3.1 已实现机制

| 机制 | 实现方式 | 说明 |
|------|---------|------|
| 独立超时 | `AI_PLAN_GENERATE_TIMEOUT = 120000` (2 分钟) | 比普通接口 60s 更长 |
| 错误分类 | `ApiError` 类 + `code` 字段 | `REQUEST_TIMEOUT` / `NETWORK_ERROR` / `BUSINESS_ERROR` / `AUTH_EXPIRED` |
| 超时后确认 | 查询 `/api/travel/plans` 列表，匹配新生成的计划 | 匹配条件：destination + days + created_at > submit_time + id 不在基线中 |
| 有限轮询 | 6 次 × 5 秒 = 30 秒 | 不会无限等待 |
| 防重复锁 | `uni.setStorageSync` 存储指纹 + 10 分钟过期 | 阻止用户在同一设备上重复提交相同参数 |
| 安全降级 | 无法确认时引导用户前往计划列表 | 不自动重新提交 |
| 生命周期清理 | `onUnload` 清理所有 timer 和标记 | 防止卸载后继续操作 |

### 3.2 降级方案局限

| 局限 | 风险等级 | 说明 |
|------|---------|------|
| 无任务 ID | 🔴 高 | 无法精确确认"我刚提交的任务是否完成" |
| 计划匹配可能误匹配 | 🟡 中 | 如果有其他途径同时创建了相同 destination+days 的计划，可能误判 |
| 多设备同时生成 | 🔴 高 | Storage 锁仅限单设备，多设备用户可能重复提交 |
| 前端锁 ≠ 服务端幂等 | 🟡 中 | 清除 storage 或换设备即可绕过 |
| `abort()` ≠ 取消后端 | 🟡 中 | 前端 HTTP 断开后后端可能继续执行 |
| 页面被杀死 | 🟡 中 | App 被强制关闭后，前端无法继续确认，但后端可能仍然生成成功 |
| 基线查询失败 | 🟢 低 | 基线失败时降低匹配可信度但不阻塞提交 |

---

## 四、迁移路径建议

当后端实现异步任务模式后，前端可按以下路径升级：

1. `api/ai.ts`：`generatePlan()` 改为调用异步接口，返回 `{ task_id }`
2. 新增 `api/ai.ts`：`getGenerateTaskStatus(taskId)` 调用状态查询接口
3. `plan/generate.vue`：
   - 移除 `queryAndMatch()` 和匹配逻辑
   - 使用 `task_id` 精确轮询
   - `idempotency_key` 替代 fingerprint-based lock
   - 极大简化状态机（不再需要"模糊匹配"）

---

## 五、参考

- 前端 request 层：`frontend/src/api/request.ts`（ApiError 类定义、RequestTask abort）
- 前端生成页：`frontend/src/pages/plan/generate.vue`
- 前端 AI API：`frontend/src/api/ai.ts`（`AI_PLAN_GENERATE_TIMEOUT` 常量）
- 数据库 Schema：`docs/schema.md`（travel_plans 表结构）
