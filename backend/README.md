# 行知 Backend

“行知”智慧文旅平台后端服务 —— 基于 FastAPI + SQLAlchemy 2.0 + MySQL。

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0（Mapped + mapped\_column） |
| 数据库 | MySQL（XAMPP），数据库名 `xingzhi` |
| 迁移 | Alembic |
| 认证 | JWT（python-jose）+ bcrypt |
| 数据校验 | Pydantic v2 |
| 天气 | OpenWeatherMap API |
| AI 通信 | DeepSeek API（兼容 OpenAI SDK） |

## 快速开始

```bash
# 1. 创建虚拟环境
conda create -n xingzhi-backend python=3.10
conda activate xingzhi-backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env   # 或直接编辑 .env
# 填写 MySQL 连接信息 + OpenWeatherMap Key

# 4. 启动 MySQL（XAMPP 控制面板）

# 5. 创建数据库
mysql -u root -e "CREATE DATABASE IF NOT EXISTS xingzhi DEFAULT CHARSET utf8mb4;"

# 6. 执行数据库迁移
alembic upgrade head

# 7. 导入旅游数据（如有 xingzhi.db）
python scripts/import_data.py --clear

# 8. 启动服务
uvicorn main:app --reload --port 8000
```

启动后访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 Swagger 文档。

## 项目结构

```
backend/
├── main.py                  # FastAPI 应用入口
├── .env                     # 环境变量
├── requirements.txt         # Python 依赖
├── alembic.ini              # Alembic 配置
├── alembic/
│   ├── env.py               # 迁移环境
│   └── versions/            # 迁移版本文件
├── app/
│   ├── api/                 # API 路由层
│   │   ├── router.py        # 主路由（注册所有子路由）
│   │   ├── deps.py          # 依赖注入（JWT 认证）
│   │   ├── health.py        # 健康检查
│   │   ├── user.py          # 用户注册/登录/偏好
│   │   ├── travel.py        # 城市/景点/酒店/餐厅/旅行计划
│   │   ├── recommendation.py # 收藏/评论
│   │   ├── ai.py            # AI 对话
│   │   └── weather.py       # 实时天气
│   ├── models/              # ORM 数据模型（10 个实体）
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 业务逻辑层
│   └── core/                # 核心配置
│       ├── config.py        # 配置读取（pydantic-settings）
│       ├── database.py      # 数据库引擎 + 会话管理
│       └── security.py      # JWT + bcrypt
└── scripts/
    └── import_data.py       # SQLite → MySQL 数据导入
```

## API 接口（25 个端点）

### 用户模块 `/api/users`
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/users/register` | 否 | 注册 |
| POST | `/api/users/login` | 否 | 登录（返回 JWT） |
| GET | `/api/users/me` | 是 | 当前用户信息 |
| PUT | `/api/users/me` | 是 | 更新用户信息 |
| GET | `/api/users/me/preferences` | 是 | 用户偏好列表 |
| POST | `/api/users/me/preferences` | 是 | 添加偏好 |
| DELETE | `/api/users/me/preferences/{id}` | 是 | 删除偏好 |

### 旅游资源 `/api/travel`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/travel/cities` | 城市列表/新增 |
| GET/PUT/DELETE | `/api/travel/cities/{id}` | 城市详情/更新/删除 |
| GET/POST | `/api/travel/scenics` | 景点列表/新增 |
| GET/PUT/DELETE | `/api/travel/scenics/{id}` | 景点详情/更新/删除 |
| GET/POST | `/api/travel/hotels` | 酒店列表/新增 |
| GET/PUT/DELETE | `/api/travel/hotels/{id}` | 酒店详情/更新/删除 |
| GET/POST | `/api/travel/restaurants` | 餐厅列表/新增 |
| GET/PUT/DELETE | `/api/travel/restaurants/{id}` | 餐厅详情/更新/删除 |
| GET/POST | `/api/travel/plans` | 旅行计划列表/创建 |
| GET/PUT/DELETE | `/api/travel/plans/{id}` | 计划详情/更新/删除 |

### 社交互动 `/api/social`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/social/favorites` | 收藏列表/添加收藏 |
| DELETE | `/api/social/favorites/{id}` | 取消收藏 |
| GET/POST | `/api/social/reviews` | 评论列表/发表评论 |
| PUT/DELETE | `/api/social/reviews/{id}` | 编辑/删除评论 |

### AI 对话 `/api/ai`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | AI 对话（占位，待接 DeepSeek） |
| GET | `/api/ai/sessions` | 聊天记录 |
| DELETE | `/api/ai/sessions/{id}` | 删除记录 |

### 天气 `/api/weather`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/weather/current?city=杭州` | 实时天气 |
| GET | `/api/weather/forecast?city=杭州&days=5` | 天气预报 |

## 数据库 Schema

| 表 | 数据量 | 说明 |
|------|------|------|
| users | 0 | 用户表 |
| cities | 416 | 全国地级市 |
| scenic\_spots | 10,323 | 景点（含坐标/分类/标签） |
| hotels | 9,727 | 酒店 |
| restaurants | 7,505 | 餐厅 |
| favorites | 0 | 收藏 |
| reviews | 0 | 评论 |
| travel\_plans | 0 | AI 旅行计划 |
| user\_preference | 0 | 用户偏好 |
| ai\_sessions | 0 | AI 聊天记录 |

## 统一响应格式

```json
// 成功
{ "code": 0, "message": "success", "data": { ... } }

// 失败（HTTP 状态码非 200）
{ "detail": "错误描述" }
```

## 认证方式

JWT Bearer Token。步骤：

1. `POST /api/users/register` 注册
2. `POST /api/users/login` 获取 `access_token`
3. 后续请求 Header 加 `Authorization: Bearer <token>`

## 查询参数

| 参数 | 适用接口 | 说明 |
|------|----------|------|
| `level` | 城市列表 | 热门/普通/小众 |
| `province` | 城市列表 | 省份 |
| `city_id` | 景点/酒店/餐厅列表 | 城市筛选 |
| `category` | 景点列表 | 类别 |
| `target_type` | 评论列表 | scenic\_spot/hotel/restaurant |
| `target_id` | 评论列表 | 目标 ID |
| `skip` | 所有列表 | 分页偏移，默认 0 |
| `limit` | 所有列表 | 每页数量，默认 20 |

## 数据库迁移

```bash
# 修改 app/models/ 后：
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

禁止手动修改数据库表结构。

## 数据导入

```bash
# 从 SQLite 导入旅游数据（清空旧数据）
python scripts/import_data.py --clear

# 追加导入（不清空）
python scripts/import_data.py
```
