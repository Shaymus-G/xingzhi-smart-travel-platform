# "行知"数据库 Schema 设计文档

> 最后更新：2026-07-23
> 当前数据总量：~55,886 条
> 数据库：TiDB Cloud Serverless（兼容 MySQL 8.0）

---

## 一、数据关系图

```
users ────┬─── favorites (user_id)
          ├─── reviews (user_id)
          ├─── travel_plans (user_id)
          ├─── user_preference (user_id)
          └─── ai_sessions (user_id)

cities ───┬─── scenic_spots (city_id)      ← 游
          ├─── hotels (city_id)             ← 住
          ├─── restaurants (city_id)        ← 吃
          ├─── entertainments (city_id)     ← 娱（P4 新增）
          └─── shopping_malls (city_id)     ← 购（P4 新增）

favorites / reviews 的 target_type:
  scenic_spot | hotel | restaurant | entertainment | shopping_mall
```

---

## 二、表结构

### users（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| email | VARCHAR(255) UNIQUE | 邮箱 |
| password_hash | VARCHAR(255) | bcrypt 哈希密码 |
| avatar | VARCHAR(500) | 头像 URL |
| phone | VARCHAR(20) | 手机号 |
| api_key | VARCHAR(255) | 用户自有大模型 API Key（支持双模式调用） |
| is_active | BOOLEAN | 是否激活，默认 true |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### cities（城市）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| name | VARCHAR(100) | 城市名称 |
| province | VARCHAR(50) | 省份 |
| country | VARCHAR(50) | 国家，默认"中国" |
| description | TEXT | 城市简介 |
| cover_image | VARCHAR(500) | 封面图 URL |
| latitude | DECIMAL(10,7) | 纬度（GCJ-02 坐标系） |
| longitude | DECIMAL(10,7) | 经度（GCJ-02 坐标系） |
| level | VARCHAR(20) | 热度等级：热门 / 普通 / 小众 |

> 数据量：416 条，覆盖全国地级市

### scenic_spots（景点）— 游

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| city_id | BIGINT FK | 所属城市 → cities.id |
| name | VARCHAR(100) | 景点名称 |
| description | TEXT | 简介 |
| address | VARCHAR(500) | 详细地址 |
| category | VARCHAR(50) | 分类（风景名胜 / 科教文化服务 / 寺庙教堂 等） |
| score | DECIMAL(3,1) | 评分 0-5 |
| price | DECIMAL(10,2) | 门票价格（0 = 免费） |
| open_time | VARCHAR(100) | 开放时间 |
| latitude | DECIMAL(10,7) | 纬度 |
| longitude | DECIMAL(10,7) | 经度 |
| image_url | VARCHAR(500) | 图片 URL |
| tags_json | JSON | 标签数组，用于 AI 推荐 |

> 数据量：20,646 条

### hotels（酒店）— 住

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| city_id | BIGINT FK | 所属城市 → cities.id |
| name | VARCHAR(100) | 酒店名称 |
| description | TEXT | 简介 |
| address | VARCHAR(500) | 地址 |
| price | DECIMAL(10,2) | 参考价格 |
| score | DECIMAL(3,1) | 评分 0-5 |
| open_time | VARCHAR(100) | 开业时间（非营业时间） |
| latitude | DECIMAL(10,7) | 纬度 |
| longitude | DECIMAL(10,7) | 经度 |
| image_url | VARCHAR(500) | 图片 URL |

> 数据量：19,454 条

### restaurants（餐厅）— 吃

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| city_id | BIGINT FK | 所属城市 → cities.id |
| name | VARCHAR(100) | 餐厅名称 |
| category | VARCHAR(50) | 菜系类别 |
| description | TEXT | 简介 |
| price_level | VARCHAR(20) | 价格水平 |
| score | DECIMAL(3,1) | 评分 0-5 |
| address | VARCHAR(500) | 地址 |
| latitude | DECIMAL(10,7) | 纬度 |
| longitude | DECIMAL(10,7) | 经度 |
| image_url | VARCHAR(500) | 图片 URL |

> 数据量：15,010 条

### entertainments（娱乐场所）— 娱（P4 新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| city_id | BIGINT FK | 所属城市 → cities.id |
| name | VARCHAR(100) | 名称 |
| description | TEXT | 简介 |
| address | VARCHAR(500) | 详细地址 |
| category | VARCHAR(50) | 类型（KTV / 电影院 / 酒吧 / 网吧 / 洗浴 / 游戏厅） |
| score | DECIMAL(3,1) | 评分 0-5 |
| price | DECIMAL(10,2) | 参考价格 |
| open_time | VARCHAR(100) | 营业时间 |
| latitude | DECIMAL(10,7) | 纬度 |
| longitude | DECIMAL(10,7) | 经度 |
| image_url | VARCHAR(500) | 图片 URL |

> 数据量：180 条，覆盖 36 个重点城市

### shopping_malls（商场）— 购（P4 新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| city_id | BIGINT FK | 所属城市 → cities.id |
| name | VARCHAR(100) | 名称 |
| description | TEXT | 简介 |
| address | VARCHAR(500) | 详细地址 |
| category | VARCHAR(50) | 类型（购物中心 / 百货 / 商业街 / 奥特莱斯） |
| score | DECIMAL(3,1) | 评分 0-5 |
| price | DECIMAL(10,2) | 参考价格 |
| open_time | VARCHAR(100) | 营业时间 |
| latitude | DECIMAL(10,7) | 纬度 |
| longitude | DECIMAL(10,7) | 经度 |
| image_url | VARCHAR(500) | 图片 URL |

> 数据量：180 条，覆盖 36 个重点城市

### favorites（收藏）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| user_id | BIGINT FK | 用户 → users.id |
| target_type | VARCHAR(50) | 收藏目标类型 |
| target_id | BIGINT | 收藏目标 ID |
| created_at | DATETIME | 收藏时间 |

> target_type 取值：`scenic_spot` | `hotel` | `restaurant` | `entertainment` | `shopping_mall`

### reviews（评论）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| user_id | BIGINT FK | 用户 → users.id |
| target_type | VARCHAR(50) | 评论目标类型 |
| target_id | BIGINT | 评论目标 ID |
| content | TEXT | 评论内容 |
| score | DECIMAL(3,1) | 评分 1-5 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

> target_type 取值同 favorites

### travel_plans（AI 旅行计划）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| user_id | BIGINT FK | 用户 → users.id |
| title | VARCHAR(200) | 计划标题 |
| destination | VARCHAR(100) | 目的地城市 |
| days | INT | 旅行天数 |
| budget | DECIMAL(12,2) | 预算总额 |
| plan_json | JSON | 结构化行程（Pydantic 验证后入库） |
| markdown | TEXT | AI 渲染的可展示 Markdown |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

> plan_json 结构示例：
```json
{
  "schema_version": "1.0",
  "title": "杭州三日游",
  "destination": { "city_id": 257, "name": "杭州", "province": "浙江" },
  "days": 3,
  "itinerary": [
    {
      "day": 1,
      "theme": "西湖风光",
      "items": [
        {
          "period": "morning",
          "resource_type": "scenic_spot",
          "resource_id": 6324,
          "name": "西湖",
          "transport_to_next": "步行前往"
        }
      ],
      "meals": [{ "period": "noon", "name": "楼外楼", "resource_id": 2001 }],
      "hotel": { "name": "杭州西湖大酒店", "resource_id": 3001 }
    }
  ],
  "budget": {
    "estimated_total": 2780,
    "breakdown": { "tickets": 300, "food": 700, "lodging": 1200, "transport": 400, "other": 180 }
  },
  "tips": ["穿舒适的鞋子"],
  "assumptions": ["基于平台真实数据生成"]
}
```

### user_preference（用户偏好）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| user_id | BIGINT FK | 用户 → users.id |
| preference_type | VARCHAR(50) | 偏好类型（风景 / 美食 / 历史 等） |
| preference_value | VARCHAR(255) | 偏好值（自然风光 / 川菜 等） |
| weight | FLOAT | 权重，默认 1.0 |

### ai_sessions（AI 聊天记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 自增主键 |
| user_id | BIGINT FK | 用户 → users.id |
| role | VARCHAR(20) | 角色：user / assistant / system |
| content | TEXT | 消息内容 |
| created_at | DATETIME | 发送时间 |

---

## 三、数据总量

| 表 | 数量 | 覆盖城市 |
|------|------|----------|
| cities | 416 | 全国地级市 |
| scenic_spots | 20,646 | 416 个城市 |
| hotels | 19,454 | 416 个城市 |
| restaurants | 15,010 | 416 个城市 |
| entertainments | 180 | 36 个重点城市 |
| shopping_malls | 180 | 36 个重点城市 |
| **合计** | **~55,886** | |

---

## 四、API 接口索引

### 旅游资源（/api/travel）

| 实体 | 列表接口 | 详情接口 | 对应"吃住行娱游购" |
|------|---------|---------|-----------------|
| 景点 | `GET /api/travel/scenics?city_id=` | `/scenics/{id}` | 游 |
| 酒店 | `GET /api/travel/hotels?city_id=` | `/hotels/{id}` | 住 |
| 餐厅 | `GET /api/travel/restaurants?city_id=` | `/restaurants/{id}` | 吃 |
| 娱乐 | `GET /api/travel/entertainments?city_id=` | `/entertainments/{id}` | 娱 |
| 商场 | `GET /api/travel/malls?city_id=` | `/malls/{id}` | 购 |

### 交通路径（/api/transit）— 行

| 接口 | 说明 |
|------|------|
| `GET /api/transit/route` | 任意两点间路径规划（公交/驾车/步行/骑行） |
| `GET /api/transit/between-spots` | 景点间快捷接口 |

### 社交互动（/api/social）

target_type 支持 5 种类型：`scenic_spot` / `hotel` / `restaurant` / `entertainment` / `shopping_mall`

### 其他

| 模块 | 路径 | 说明 |
|------|------|------|
| 用户 | `/api/users/*` | 注册/登录/偏好 |
| AI 对话 | `/api/ai/chat` | DeepSeek 实时对话 |
| AI 计划 | `/api/ai/plans/generate` | 生成结构化旅行计划 |
| 推荐 | `/api/recommend/*` | 周边/相似/反差/协同过滤 |
| 天气 | `/api/weather/*` | OpenWeatherMap 实时天气 |

---

## 五、技术规范

- **主键**：所有表统一 BIGINT + AUTO_INCREMENT
- **时间戳**：需要 created_at / updated_at 的表继承 TimestampMixin
- **坐标**：GCJ-02 坐标系，DECIMAL(10,7) 精度
- **迁移**：使用 Alembic 管理，禁止手动改表
- **ORM**：SQLAlchemy 2.0（Mapped + mapped_column 声明式风格）
- **图片**：所有资源图片使用 HTTPS URL（Lorem Picsum CDN）
