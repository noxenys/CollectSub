# SmartSub - 智能订阅聚合器

🚀 **自动化、全方位、高质量的代理订阅抓取与聚合工具**

从互联网各个角落（Telegram 频道、GitHub 仓库、普通网页）自动抓取、智能筛选并聚合免费的代理订阅链接与节点。

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-自动化部署-green)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-GPL--3.0-orange)](LICENSE)

---

## ✨ 核心特性

### 🌐 全方位抓取
- ✅ **Telegram 频道**：自动解析频道消息中的订阅链接
- ✅ **GitHub/直连源**：直接集成高质量的开源订阅源
- ✅ **网页模糊抓取**：智能识别任意网页中的订阅链接，无视页面结构
- ✅ **裸节点捕获**：自动识别并收集 `vmess://`, `ss://`, `trojan://`, `vless://`, `hysteria://` 等节点

### 🎯 智能质量控制 (NEW!)
- ✅ **订阅内容验证**：自动过滤空订阅和节点过少的低质量订阅
- ✅ **智能去重**：MD5 哈希检测，消除内容重复的镜像订阅
- ✅ **垃圾内容检测**：识别"已过期"、"请购买"等无效订阅
- ✅ **统计报告**：每次运行自动输出质量控制效果报告

### 🛡️ 自动清理与维护 (NEW!)
- ✅ **失效订阅自动删除**：识别 404/502 等错误状态码，自动清理失效链接
- ✅ **失效记录追踪**：所有失效订阅记录到日志文件，可审查和恢复
- ✅ **流式下载熔断**：限制下载大小（3MB），防止内存溢出
- ✅ **文件膨胀保护**：自动限制节点库和黑名单文件大小，防止无限增长

### ⚡ 高性能与稳定性
- ✅ **并发加速**：32 线程池，极速处理成百上千个订阅
- ✅ **智能超时控制**：可配置的请求超时和重试机制
- ✅ **多协议支持**：支持 7+ 种节点协议（vmess, ss, ssr, trojan, vless, hysteria, hysteria2）

### ⚙️ 自动化部署
- ✅ **GitHub Actions 集成**：7×24 小时无人值守自动更新
- ✅ **完全配置化**：所有参数可在 `config.yaml` 灵活调整
- ✅ **安全依赖**：已升级到最新版本，修复所有已知安全漏洞

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/SmartSub.git
cd SmartSub
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖管理说明**:
- `requirements.txt`: 使用 `>=` 允许小版本更新，获取安全补丁
- `requirements-lock.txt`: 锁定当前测试通过的稳定版本，适合生产环境

如需使用锁定版本：
```bash
pip install -r requirements-lock.txt
```

### 3. 运行程序

```bash
python main.py
```

首次运行将自动：
- 抓取订阅源
- 验证订阅质量
- 过滤失效和低质量订阅
- 生成聚合文件

---

## ⚙️ 配置说明

编辑 `config.yaml` 自定义抓取源和质量控制参数：

### 基础配置

```yaml
# Telegram 频道列表
tgchannel:
  - https://t.me/example_channel
  - https://t.me/another_channel

# 直连订阅源（GitHub 或其他稳定 URL）
subscribe:
  - https://raw.githubusercontent.com/user/repo/main/sub.yaml

# 网页模糊抓取（博客、论坛、任何网页）
web_pages:
  - https://example.com/free-vpn-list
```

### 性能配置

```yaml
performance:
  max_workers: 32              # 并发线程数（根据机器调整）
  content_limit_mb: 3          # 下载限制（MB）
  request_timeout: 6           # 请求超时（秒）
```

### 质量控制配置 (NEW!)

```yaml
quality_control:
  min_nodes: 3                 # 最少节点数（少于此数将被过滤）
  enable_duplicate_check: true # 启用内容去重
  enable_quality_check: true   # 启用质量检查
```

### 订阅转换后端配置

```yaml
subconverter_backends:
  - api.dler.io
  - sub.xeton.dev
  - sub.id9.cc
  - sub.maoxiongnet.com
```

### 通知配置 (可选)

支持多种通知方式，通过环境变量配置：

### 4. 配置 GITHUB_TOKEN / GIST_TOKEN (必选)

为了生成 **GitHub Gist 订阅链接**（推荐，最稳定私密），你需要配置 Token：

1. **创建 Token**:
   - 访问 [GitHub Settings > Tokens](https://github.com/settings/tokens/new)
   - Note: `SmartSub`
   - Scopes: **仅勾选 `gist`**
   - 点击 Generate token 并复制

2. **配置 Secrets**:
   - 在仓库 Settings -> Secrets -> Actions -> New repository secret
   - Name: `GIST_TOKEN`
   - Value: (刚才复制的 Token)

3. **(推荐) 配置 GIST_ID 实现永久订阅**:
   - 如果你想让订阅链接**永远不变**：
     1. 手动创建一个 Gist (或运行一次脚本生成)
     2. 获取 Gist ID (URL 中最后那串字符)
     3. 添加 Secret Name: `GIST_ID`, Value: (你的 Gist ID)

#### Telegram Bot 通知（可选，推荐）

1. 在 Telegram 搜索 `@BotFather` 创建 Bot
2. 获取 Bot Token 和 Chat ID
3. GitHub 仓库设置 Secrets：
   - `TELEGRAM_BOT_TOKEN`: Bot Token
   - `TELEGRAM_CHAT_ID`: Chat ID

#### Discord Webhook

1. Discord 频道设置 → Webhook → 复制 URL
2. 设置 Secret: `DISCORD_WEBHOOK_URL`

#### Server酱（微信推送）

1. 访问 https://sct.ftqq.com/ 获取 SendKey
2. 设置 Secret: `SERVERCHAN_KEY`

#### PushPlus（微信推送）

1. 访问 http://www.pushplus.plus/ 获取 Token
2. 设置 Secret: `PUSHPLUS_TOKEN`

配置后会在每次运行完成时收到通知！

---

## 📊 运行效果示例

程序运行后会自动输出统计报告：

```
============================================================
📊 订阅抓取统计报告
============================================================
✅ 有效订阅: 45 个
   - Clash 订阅: 28 个
   - V2Ray 订阅: 15 个
   - 机场订阅: 2 个

🔍 质量控制统计:
   - 检查总数: 120 个
   - 重复内容: 25 个
   - 低质量订阅: 30 个
     • 空订阅: 10 个
     • 节点过少: 15 个
     • 垃圾内容: 5 个

❌ 失效订阅: 20 个

💡 质量提升: 过滤了 75 个无效/低质订阅 (62.5%)
============================================================
```

---

## 📂 输出文件

### 根目录文件
| 文件 | 说明 |
|------|------|
| `sub_merge.txt` | **推荐** 通用聚合订阅（明文），包含所有链接和节点 |
| `sub_merge_base64.txt` | **推荐** 通用聚合订阅（Base64），可直接作为订阅链接使用 |
| `collected_nodes.txt` | 抓取到的所有直连/裸节点（实时更新，限制 10k 条） |
| `failed_subscriptions.log` | 失效订阅记录（可审查/恢复） |

### `sub/` 目录文件
| 文件 | 说明 |
|------|------|
| `sub_all.yaml` | 所有有效订阅的聚合文件（总库） |
| `sub_all_clash.txt` | **Clash订阅文件（Base64编码，可直接导入）** ✅ |
| `sub_all_loon.txt` | **Loon订阅文件（Base64编码，可直接导入）** ✅ |
| `sub_all_sub_store.txt` | Sub-Store 专用格式（区分机场与开心玩耍） |
| `YYYY/MM/D-DD.yaml` | 按日期归档的每日抓取结果 |
| `sub/high_quality_nodes.txt` | ⭐ **高质量筛选节点**（经过连通性、延迟、IP风险检测） |
| `sub/quality_report.json` | 节点质量分析报告（包含统计数据） |

### 节点格式规范

高质量节点输出（`sub/high_quality_nodes.txt`）采用标准化命名格式：

```
{国旗Emoji} {国家代码} 🛡️{风险值} ⚡{综合得分} {协议名}
```

**示例**：
```
🇺🇸 US 🛡️0 ⚡98 Vmess
🇯🇵 JP 🛡️0 ⚡95 Vless
🇸🇬 SG 🛡️15 ⚡85 Trojan
🇩🇪 DE 🛡️N/A ⚡72 Hysteria2
```

**字段说明**：
- **国旗Emoji**: 节点所在国家/地区的旗帜
- **国家代码**: ISO 3166-1 alpha-2 标准代码（US, JP, SG等）
- **🛡️风险值**: IP风险评分（0=纯净IP，100=高风险，N/A=未检测）
  - `0`: 家庭宽带IP，最佳质量
  - `1-50`: 低风险
  - `50+`: 高风险（可能被限制）
  - `N/A`: 未启用IP检测
- **⚡综合得分**: 基于协议、延迟、风险值的综合评分（0-100+）
  - 协议加分：Hysteria2(10) > Vless(8) > Trojan(7) > Vmess(6) > SS(5)
  - 延迟加分：<100ms(+5), 100-200ms(+3), 200-300ms(+1)
  - IP纯净度加分：风险值0(+10)
- **协议名**: 节点协议类型（Vmess, Vless, Trojan, SS, Hysteria2等）

> **注意**: `collected_nodes.txt` 中的节点为原始格式（未重命名），仅 `high_quality_nodes.txt` 采用上述标准化格式。

---

## 🤖 GitHub Actions 自动化

本项目完全支持 GitHub Actions，实现自动化抓取：

### 工作流说明

工作流文件位于 `.github/workflows/fetch.yaml`，主要步骤：

1. **定时触发**: 每天北京时间凌晨 4 点自动运行
2. **手动触发**: 可在 Actions 页面手动运行
3. **执行流程**:
   - 抓取订阅源 (`main.py`)
   - 筛选高质量节点 (`node_quality_filter.py`)
   - 生成订阅 URL (`generate_subscription_url.py`)
   - 推送到 Telegram（如已配置）
   - 提交更新到仓库

### 首次部署

1. Fork 本仓库
2. 配置必需的 Secrets (Settings → Secrets → Actions):
   - `GIST_TOKEN`: GitHub Personal Access Token (需 `gist` 权限)
   - `GIST_ID`: Gist ID (可选，用于固定订阅链接)
3. 手动触发一次工作流验证配置
4. 完成！之后将自动运行

---

## 📝 更新日志

### v2.0 (2026-01)
- ✅ 修复 GitHub Actions 推送冲突问题
- ✅ 添加自动订阅 URL 生成
- ✅ 增强节点 URL 正则表达式
- ✅ 添加日志文件自动轮转
- ✅ 优化工作流程

### v1.0
- 🎯 智能质量控制系统
- 🔄 自动失效订阅清理
- 📊 详细统计报告
- 🔒 安全依赖升级
- ⚡ 性能优化和配置化
- 🛡️ 内存保护与文件自动维护

---

## 📚 相关文档

- **[配置参数详解](docs/CONFIGURATION.md)** - 详细说明所有配置参数的作用、影响和最佳实践
- **[故障排查指南](docs/TROUBLESHOOTING.md)** - 常见问题诊断和解决方案
- **[节点来源说明](NODES_SOURCE.md)** - 各个文件的来源和用途说明

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

在提交 Issue 时，请提供：
- 详细的错误日志
- 运行环境（操作系统、Python 版本）
- 相关配置文件（脱敏后）

