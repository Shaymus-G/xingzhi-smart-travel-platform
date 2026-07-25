# CLI → HBuilderX 迁移报告

## 元信息

| 项目 | 内容 |
|------|------|
| 迁移日期 | 2026-07-25 |
| 迁移前分支 | `feat/local-integration` |
| 迁移分支 | `chore/hbuilderx-migration` |
| 图标提交 | `6b0ed8e` feat(ui): add custom tab bar icons |
| 迁移前基线 | `6b0ed8e030dbe6da56a9d799b0d54ce0284b311f` |
| HBuilderX 版本 | 未记录（CLI 环境） |
| Node 版本 | 需在 HBuilderX 环境中记录 |
| npm 版本 | 需在 HBuilderX 环境中记录 |

## 迁移方案

**采用方案 A：HBuilderX 直接打开现有 frontend/**

操作路径：

```
HBuilderX → 文件 → 打开目录 → E:/project/xingzhi/frontend
```

**不**选择方案 B（新建 HBuilderX 项目并复制源码）。

## 关键决策

| 决策项 | 结论 |
|--------|------|
| 是否新建第二套前端源码 | 否 |
| 是否移动 pages.json | 否 |
| 是否移动 manifest.json | 否 |
| 是否移动 main.ts | 否 |
| 是否移动 App.vue | 否 |
| 是否保留 CLI 构建能力 | 是（npm scripts 全部保留） |
| 是否修改 CLI 配置 | 否（无需修改） |

## HBuilderX 兼容性检查

| 检查项 | 状态 |
|--------|------|
| `package.json` 存在 | ✅ |
| `src/manifest.json` 存在 | ✅ |
| `src/pages.json` 存在 | ✅ |
| `src/main.ts` 存在 | ✅ |
| `src/App.vue` 存在 | ✅ |
| `manifest.json` 声明 `vueVersion: "3"` | ✅ |
| `manifest.json` 声明 `name: "行知"` | ✅ |
| `frontend/.gitignore` 已覆盖 `unpackage/` | ✅ |
| `frontend/.gitignore` 已覆盖 `.hbuilderx/` | ✅ |
| `frontend/.gitignore` 已覆盖 `node_modules/` | ✅ |
| `frontend/.gitignore` 已覆盖 `dist/` | ✅ |
| `frontend/.gitignore` 已覆盖 `*.local` 环境文件 | ✅ |

## 修改文件

| 文件 | 修改内容 | 原因 |
|------|---------|------|
| （无） | — | 项目结构已直接兼容 HBuilderX |

## 新增文件

| 文件 | 说明 |
|------|------|
| `docs/CLI到HBuilderX迁移报告.md` | 本报告 |

## 图标资源映射

| Tab | frontend/fig 源文件 | static 打包文件 | iconPath | selectedIconPath |
|-----|-------------------|----------------|----------|-------------------|
| 首页 | `frontend/fig/首页.png` | `static/tabbar/tab-home.png` | `static/tabbar/tab-home.png` | `static/tabbar/tab-home-active.png` |
| AI 助手 | `frontend/fig/ai助手.png` | `static/tabbar/tab-ai.png` | `static/tabbar/tab-ai.png` | `static/tabbar/tab-ai-active.png` |
| 个人中心 | `frontend/fig/个人中心.png` | `static/tabbar/tab-profile.png` | `static/tabbar/tab-profile.png` | `static/tabbar/tab-profile-active.png` |

> **注意：** frontend/fig 每个 Tab 只有一张源图（均为 2048×2048 PNG），普通态与选中态使用同一缩放版本。选中态通过 `selectedColor: #4A90D9` 区分文字颜色。

## 构建回归结果

| 检查项 | 结果 |
|--------|------|
| `npm run type-check` | ✅ 通过 |
| `npm run build:h5` | ✅ DONE Build complete |
| `npm run build:mp-weixin` | ✅ DONE Build complete |

CLI 构建体系完整保留，未受迁移影响。

## 运行验证

| 验证项 | 状态 |
|--------|------|
| HBuilderX H5 运行 | ⚠️ 需在 HBuilderX GUI 中验证 |
| 首页 Tab 图标显示 | ⚠️ 需在 HBuilderX GUI 中验证 |
| AI 助手 Tab 图标显示 | ⚠️ 需在 HBuilderX GUI 中验证 |
| 个人中心 Tab 图标显示 | ⚠️ 需在 HBuilderX GUI 中验证 |
| Tab 切换正常 | ⚠️ 需在 HBuilderX GUI 中验证 |
| "生成 AI 旅行计划"入口 | ⚠️ 需在 HBuilderX GUI 中验证 |
| AI 会话删除按钮 | ⚠️ 需在 HBuilderX GUI 中验证 |
| Android 模拟器 | ⚠️ 未验证（需 HBuilderX + Android 环境） |
| Android 真机 | ⚠️ 未验证（需设备） |
| 微信开发者工具 | ⚠️ 未验证（需微信开发者工具） |

## 未配置的发布信息

| 配置项 | 状态 | 说明 |
|--------|------|------|
| DCloud AppID | 空 | `manifest.json` 中 `appid: ""`，发布前需在 DCloud 开发者中心申请 |
| 微信小程序 AppID | 空 | `manifest.json` 中 `mp-weixin.appid: ""`，需填写真实 AppID |
| Android 包名 | 未配置 | `manifest.json` 中缺少 `app-plus.distribute.android.packagename` |
| Android 签名 | 未配置 | 需配置 keystore 签名文件 |
| iOS Bundle ID | 未配置 | 需配置 `app-plus.distribute.ios.appid` |

以上信息应在正式发布前由项目负责人填写，不得使用虚假值。

## Git 状态

| 项目 | 内容 |
|------|------|
| 迁移分支 | `chore/hbuilderx-migration` |
| 图标 commit | `6b0ed8e` feat(ui): add custom tab bar icons |
| 未提交修改 | `.gitignore`（backups/ 规则）、`frontend/src/pages/ai/chat.vue`（AI 会话删除功能） |
| stash | 无本次 stash |

## HBuilderX 生成目录处理

| 目录/文件 | .gitignore 状态 |
|-----------|----------------|
| `frontend/unpackage/` | ✅ 已在 `frontend/.gitignore` |
| `frontend/.hbuilderx/` | ✅ 已在 `frontend/.gitignore` |
| `frontend/node_modules/` | ✅ 已在 `frontend/.gitignore` |
| `frontend/dist/` | ✅ 已在 `frontend/.gitignore` |
| `*.apk` | 建议添加至 `.gitignore` |
| `*.aab` | 建议添加至 `.gitignore` |
| `*.keystore` | 建议添加至 `.gitignore` |

## 回滚方式

```bash
git switch feat/local-integration
# 如需删除迁移分支：
git branch -d chore/hbuilderx-migration
```

## 建议 push 命令

```bash
git push -u origin chore/hbuilderx-migration
```

> 等待用户确认后再执行 push。

## 未处理范围

以下项目在本轮明确排除，不在迁移范围内：

| 项目 | 状态 |
|------|------|
| 本地 MySQL 数据不足 | 未处理（本轮排除） |
| Alembic 版本漂移 | 未处理（本轮排除） |
| entertainments / shopping_malls 数据同步 | 未处理（本轮排除） |
| frontend/.env.development 指向 Render | 未处理（本轮排除） |
| 本地 CORS 配置 | 未处理（本轮排除） |
| 本地 AI 端到端联调 | 未重新验证（本轮排除） |
| Render 后端部署 | 未修改（本轮排除） |
| 后端接口和 AI 逻辑 | 未修改（本轮排除） |
