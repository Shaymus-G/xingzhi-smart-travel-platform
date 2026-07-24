# 行知 XingZhi — 前端

uni-app CLI 项目（Vue 3 + Vite + TypeScript）。

---

## 快速开始

```bash
cd frontend
npm install

# 类型检查
npm run type-check

# H5 开发
npm run dev:h5

# H5 构建
npm run build:h5

# 微信小程序开发
npm run dev:mp-weixin

# 微信小程序构建
npm run build:mp-weixin
```

---

## 目录结构

```
frontend/
├── package.json          # 项目配置与依赖
├── vite.config.ts        # Vite 构建配置
├── tsconfig.json         # TypeScript 配置
├── index.html            # H5 入口 HTML
├── env.d.ts              # 环境变量类型声明
├── .env.development      # 开发环境变量
├── .env.production       # 生产环境变量
├── .env.example          # 环境变量示例
├── .hbuilderx/           # HBuilderX 启动配置
└── src/                  # 源码目录
    ├── App.vue            # 根组件
    ├── main.ts            # 入口
    ├── pages.json         # 页面路由配置
    ├── manifest.json      # 平台配置
    ├── uni.scss           # uni-app 样式变量
    ├── pages/             # 14 个页面
    │   ├── index/         # 启动页
    │   ├── auth/          # 登录/注册
    │   ├── home/          # 首页
    │   ├── city/          # 城市详情
    │   ├── scenic/        # 景点详情
    │   ├── ai/            # AI 对话
    │   ├── plan/          # 旅行计划（列表/详情/生成）
    │   ├── profile/       # 个人中心/收藏/编辑/设置
    │   └── resource/      # 通用资源详情
    ├── components/        # 公共组件
    ├── api/               # API 请求封装
    ├── types/             # TypeScript 类型定义
    ├── utils/             # 工具函数
    ├── stores/            # Pinia 状态管理
    ├── styles/            # 全局样式
    ├── config/            # 运行时配置
    └── static/            # 静态资源
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | uni-app 3 (Vue 3) |
| 构建 | Vite 5 |
| 语言 | TypeScript 5 |
| 状态管理 | Pinia |
| 样式 | SCSS |
| 包管理 | npm |

---

## HBuilderX

使用 HBuilderX 打开 **`frontend/`** 目录（包含 `package.json` 的目录），不要打开 `frontend/src/`。

- **运行到 Android 模拟器**：HBuilderX → 运行 → 运行到手机或模拟器 → 选择模拟器
- **运行到 Android 真机**：开启 USB 调试 → 连接电脑 → HBuilderX → 运行 → 选择设备
- **App 云打包**：HBuilderX → 发行 → 原生 App-云打包

---

## API 地址配置

### 默认地址

通过 `VITE_API_BASE_URL` 环境变量配置（`.env.development` / `.env.production`）。

### 手机端修改

在 App 中：个人中心 → 高级设置 → 修改后端 API 地址（支持测试连接与恢复默认）。地址变更后自动清除登录态。

### 联调网络

| 场景 | API 地址 |
|------|---------|
| H5 开发 | Vite 代理或本机后端 |
| Android 模拟器 | `10.0.2.2`（常见 Emulator 宿主机映射） |
| Android 真机 | 电脑局域网 IP（同 WiFi） |
| 微信小程序 | HTTPS 域名 |
| 正式环境 | 稳定 HTTPS 域名 |

手机不能通过 `127.0.0.1` 访问电脑后端。

---

## 构建状态

| 命令 | 状态 |
|------|------|
| `npm run type-check` | ✅ 通过 |
| `npm run build:h5` | ✅ 通过 |
| `npm run build:mp-weixin` | ✅ 通过 |

Android 运行需 HBuilderX，App 云打包需证书与配置。
