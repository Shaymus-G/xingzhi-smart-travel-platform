## 2. AI API 联调结论

### 2.1 已验证结果

线上服务地址：

```text
https://xingzhi-smart-travel-platform.onrender.com
```

已确认：

| 接口 | 结果 | 说明 |
|---|---:|---|
| `GET /api/users/me` | 200 | Render 服务、HTTPS、JWT 鉴权和用户数据链正常 |
| `GET /api/ai/sessions` | 500 | AI 会话查询链路异常 |
| `POST /api/ai/chat` | 500 | 使用有效 JSON 后仍为服务端异常 |
| 本地 AI 接口 | 暂未形成有效结论 | 本地测试 Token 无效，返回 401 |

有效聊天请求体：

```json
{
  "message": "请只回复：AI接口测试成功",
  "session_id": null
}
```

此前出现过一次 `422 JSON decode error`，该错误由 PowerShell 调用 `curl.exe` 时 JSON 引号被破坏导致，不属于 AI 业务故障。改用 `Invoke-RestMethod` 后，线上聊天接口稳定返回 500。

### 2.2 可以排除的前端问题

当前可以排除：

- Render 域名或外部端口配置错误；
- 前端将 Render 地址错误拼接为 `:8000`；
- JWT 未携带或 JWT 无效；
- 请求体字段缺失；
- 请求体不是有效 JSON；
- 前端页面本身导致 `/api/ai/sessions` 查询失败。

`/api/ai/sessions` 不需要调用第三方大模型，但仍返回 500。因此首要问题不是 DeepSeek 响应质量，而是 AI 会话数据库、ORM、迁移或响应序列化。

### 2.3 后端优先检查项

后端与部署人员需要提供同一时间点的 Render Runtime Traceback，并检查：

```sql
SHOW TABLES LIKE 'ai_sessions';
DESCRIBE ai_sessions;
SELECT COUNT(*) FROM ai_sessions;
```

同时核对：

1. Render 当前连接的数据库实例和数据库名称；
2. `ai_sessions`、AI 消息表及相关关联表是否存在；
3. 线上 Alembic migration 是否执行到最新 revision；
4. 数据库字段是否与 SQLAlchemy 模型一致；
5. `user_id`、`session_id`、`role`、`content`、`created_at` 等字段类型是否匹配；
6. AI 会话查询是否包含 TiDB/MySQL 不兼容 SQL；
7. 响应模型是否因空值、时间类型或字段缺失而序列化失败；
8. `/api/ai/chat` 是否在调用大模型前，就因会话读取或写入失败；
9. DeepSeek 相关环境变量是否存在，但不要在日志中输出完整密钥；
10. 500 响应为什么没有统一 JSON 错误正文；
11. 当前 Render 部署 commit 是否包含最新 AI 实现。

后端应返回：

```text
- Render Runtime Traceback
- 当前部署 commit
- 当前 Alembic revision
- AI 会话相关表结构
- 问题根因
- 修复 commit
- 修复后的接口验证结果
```