# HBuilderX 与三端运行说明

## 项目类型

本项目是 **uni-app CLI 项目**（Vue 3 + Vite + TypeScript），不是 HBuilderX 原生项目。

HBuilderX 用于 Android 模拟器运行、真机调试和 App 云打包，不替代 CLI 开发流程。

---

## 正确打开目录

使用 HBuilderX 打开：

```
frontend/
```

即包含 `package.json`、`vite.config.ts` 的目录。

**不要打开**：

- `frontend/src/`（缺少 package.json）
- 仓库根目录（不是 uni-app 项目）
- 新建空白 uni-app 项目

HBuilderX 会自动识别 `src/` 目录下的 `pages.json`、`manifest.json` 和 `App.vue`。

---

## 不需要迁移

项目已经是标准 uni-app CLI 结构，不需要：

- 复制源码到新项目
- 移动 `manifest.json` 或 `pages.json`
- 创建重复项目

---

## H5 运行

```bash
cd frontend
npm run dev:h5
```

浏览器打开终端输出的地址（默认 `http://localhost:8080`）。

H5 构建：

```bash
npm run build:h5
```

输出目录：`dist/build/h5/`

---

## 微信小程序

### 开发

```bash
cd frontend
npm run dev:mp-weixin
```

输出目录：`dist/dev/mp-weixin/`

在微信开发者工具中导入该目录。

### 构建

```bash
npm run build:mp-weixin
```

输出目录：`dist/build/mp-weixin/`

### 注意事项

- 开发工具可关闭"不校验合法域名"（仅限开发）
- 真机预览需要 HTTPS 合法域名，并在微信后台配置 `request` 和 `download` 域名
- 正式发布需要微信小程序 appid

---

## Android 模拟器

### 前置条件

- HBuilderX 已安装
- Android 模拟器已创建并启动（如 Android Studio AVD、mumu、夜神等）
- `adb devices` 可见模拟器

### 运行步骤

1. HBuilderX 打开 `frontend/`
2. 菜单 → 运行 → 运行到手机或模拟器 → 选择 Android 模拟器
3. 等待编译和安装

### 网络说明

- `127.0.0.1` = 模拟器自身，**不能**访问宿主机
- `10.0.2.2` = 常见 Android Emulator（AVD）的宿主机映射
- 其他模拟器可能使用不同桥接地址（如 mumu 默认 `172.16.0.1`）

**联调步骤**：

1. 确认后端监听 `0.0.0.0`（不是 `127.0.0.1`）
2. Windows 防火墙放行后端端口
3. 在手机端：高级设置 → 填入 `http://10.0.2.2:8000` → 测试连接 → 保存

---

## Android 真机

### 前置条件

- 手机开启"开发者选项"和"USB 调试"
- 电脑安装手机驱动或通用 ADB 驱动
- `adb devices` 可见设备
- 手机和电脑连接同一 WiFi（局域网联调）

### 运行步骤

1. HBuilderX 打开 `frontend/`
2. 菜单 → 运行 → 运行到手机或模拟器 → 选择设备
3. 等待编译和安装

### 网络说明

手机**不能**通过 `127.0.0.1` 访问电脑后端。

**联调步骤**：

1. 在电脑上查看局域网 IP（`ipconfig`，如 `192.168.1.100`）
2. 确认后端监听 `0.0.0.0`
3. Windows 防火墙放行后端端口
4. 在手机端：高级设置 → 填入 `http://192.168.1.100:8000` → 测试连接 → 保存

**正式环境**建议使用稳定 HTTPS 域名（如 Render 地址），避免依赖局域网。

---

## Android App 打包

HBuilderX → 发行 → 原生 App-云打包

### 前置条件

| 项目 | 说明 |
|------|------|
| DCloud appid | 在 DCloud 开发者中心申请 |
| Android 包名 | 如 `com.example.xingzhi` |
| versionName | 如 `1.0.0` |
| versionCode | 整数，每次发版递增 |
| 应用图标 | 按规范尺寸准备 |
| 启动图 (splash) | 按规范尺寸准备 |
| 签名证书 (keystore) | 使用 HBuilderX 生成或自有证书 |
| 证书别名 (alias) | 创建证书时填写 |
| 证书密码 | 妥善保管，勿提交 Git |
| 隐私政策 URL | App 上架必需 |
| 用户协议 URL | App 上架必需 |

**注意**：证书和密码不要提交到 Git 仓库。

---

## 手机端修改 API 地址

在 App 中：个人中心 → 高级设置

功能：

- 查看当前 API 地址及来源（环境变量 / 手动覆盖）
- 修改地址
- 测试连接（调用 `/api/health`，不携带 JWT）
- 恢复为环境变量默认值

**地址变更后**：自动清除 JWT Token 和用户缓存，需要重新登录。

地址校验规则：

- 必须以 `http://` 或 `https://` 开头
- 不能包含 `/api` 路径（系统自动拼接）
- 本地地址（localhost / 127.0.0.1 / 局域网 IP）允许 HTTP
- 公网地址强制 HTTPS

---

## 环境要求

| 组件 | 当前测试版本 | 推荐 |
|------|------------|------|
| Node.js | v25.2.0 | v18 LTS（uni-app alpha 兼容性更佳） |
| npm | 11.6.2 | ≥9 |
| HBuilderX | — | 最新正式版 |
| 微信开发者工具 | — | 最新稳定版 |

---

## 常见问题

### HBuilderX 报"manifest.json 找不到"

确认打开了 `frontend/` 目录（不是 `frontend/src/` 或仓库根目录）。

### 模拟器无法访问 localhost

`127.0.0.1` 指向模拟器自身。使用 `10.0.2.2`（AVD）或对应模拟器的宿主机地址。

### 真机无法访问电脑

确认：
- 手机和电脑同一 WiFi
- 电脑防火墙已放行后端端口
- 后端监听 `0.0.0.0` 而非 `127.0.0.1`
- 使用了电脑的局域网 IP（不是 `127.0.0.1`）

### 微信提示"request 域名不合法"

开发阶段：微信开发者工具 → 详情 → 不校验合法域名（勾选）

正式发布：在微信公众平台配置 `request` 合法域名和 `download` 合法域名。

### CORS 错误 (H5)

需要后端 CORS 配置允许 H5 的访问域名。App 和微信小程序不受浏览器 CORS 限制。

### uni 统计上报失败

不影响核心业务。正式发布前可关闭或正确配置 uni 统计。

### 修改 API 地址后需重新登录

这是预期行为：地址变更后自动清除旧登录态，防止 Token 发送到错误服务器。

### Render 首次请求超时

Render 免费计划存在冷启动延迟（可能 30s+）。首次请求超时可重试。
