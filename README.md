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

#### Telegram Bot 通知（推荐）

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

1.# SmartSub 智能订阅

![GitHub Actions](https://github.com/noxenys/SmartSub/workflows/Fetch%20Subscriptions%20Source/badge.svg)

**SmartSub** 是一个智能化的全自动节点订阅与筛选系统。它不仅负责收集，更专注于**清洗与优化**。

## ✨ 核心特性

- **🧠 智能筛选**: 从海量公共节点中提炼出真正可用的高质量节点。
- **🚀 极致轻量**: 纯 Python 实现，零外部核心依赖。
- **⚡ 高效筛选**: 多线程并发检测，30秒处理 3000+ 节点。
- **🛡️ 智能风控**: 集成 **IP 风险检测**与**区域合规检查**，自动过滤被墙或高风险 IP (Gemini/ChatGPT 可用性保障)。
- **📨 自动分发**: 支持 **Telegram Bot** 自动推送高质量订阅（文件/Gist/Base64）。
- **🤖 全自动**: 配合 GitHub Actions 实现每日自动抓取、筛选、推送。

## 🛠️ 主要功能
从收集的节点中筛选出高质量节点：

```bash
python node_quality_filter.py
```

**筛选标准：**
- ✅ **连通性测试**：检查节点是否可以正常连接
- ✅ **延迟测试**：测量连接延迟，优选低延迟节点
- ✅ **协议评分**：现代协议(hysteria2, vless)获得更高分数
- ✅ **自动去重**：移除完全重复的节点
- ✅ **智能排序**：按综合得分和延迟排序

**输出文件：**
- `high_quality_nodes.txt` - 筛选后的高质量节点
- `quality_report.json` - 详细的质量分析报告

**配置调优：**

在 `config.yaml` 中调整筛选参数：

```yaml
quality_filter:
  max_workers: 32              # 并发测试线程数
  connect_timeout: 5           # 连接超时(秒)
  max_latency: 500             # 最大延迟(毫秒)
  preferred_protocols:         # 首选协议
    - hysteria2
    - vless
    - trojan
```

---

### 失效订阅管理

所有失效的订阅会被记录到 `failed_subscriptions.log`：

```
=== 2026-01-20 16:20:00 - 失效订阅 (3 个) ===
https://dead-link.com/sub1
https://timeout-link.com/sub2
https://404-link.com/sub3
```

如需恢复误删的订阅，可从日志文件中找回。

### 质量控制调优

根据需求调整 `config.yaml` 中的质量参数：

```yaml
quality_control:
  min_nodes: 5                 # 提高到 5 个节点
  enable_duplicate_check: true # 保持开启
  enable_quality_check: false  # 关闭质检（不推荐）
```

---

## 📈 性能优化建议

| 环境 | max_workers | request_timeout | 说明 |
|------|-------------|-----------------|------|
| **GitHub Actions (推荐)** | **32** | **6-8** | 极致速度模式，适合配额紧张用户 |
| 本地/高性能 | 32-64 | 10-15 | 追求更全面的抓取覆盖率 |
| 低配置服务器 | 8-16 | 15-20 | 稳定性优先，避免 CPU 过载 |

---

## 🤝 致谢与参考

本项目的发展离不开开源社区，特别感谢以下项目提供的灵感与资源：

- **核心框架**: 基于 [RenaLio/proxy-minging](https://github.com/RenaLio/proxy-minging/) 进行重构和增强
- **订阅源采集**: 参考了 [ermaozi/get_subscribe](https://github.com/ermaozi/get_subscribe) 的高质量订阅源列表与维护策略
- **爬虫逻辑**: 借鉴了 [ssrlive/proxypool](https://github.com/ssrlive/proxypool) 的抓取思路与正则匹配模式

---

## 🔒 安全说明

- ✅ 所有依赖已升级到最新安全版本
- ✅ PyYAML >= 6.0.1（修复 CVE-2020-14343 等漏洞）
- ✅ requests >= 2.32.4（修复凭证泄露漏洞）
- ✅ urllib3 >= 2.2.0（修复资源耗尽漏洞）

---

## � 资源说明

- **公共订阅源 (`sub/` 目录)**: 
  - 包含每日自动爬取的**海量原始节点** (30,000+)。
  - 适合作为节点池或自行二次筛选。
  - 文件：`sub/sub_all_url_check.txt` (全部URL), `sub/sub_all_clash.txt` (Clash格式) 等。

- **高质量筛选 (`node_quality_filter.py`)**:
  - 本项目提供的**核心工具**。
  - 用于从海量公共节点中，提炼出**低延迟、低风险、可解锁流媒体**的 VIP 节点。
  - **隐私说明**: 筛选后的高质量节点默认**不上传 GitHub**，而是通过 Telegram Bot 私发给自己。建议 Fork 本项目搭建属于你自己的私有订阅服务。

## �📜 免责声明

本项目仅供**学习交流**使用，请勿用于非法用途。

- ❌ 请勿用于商业目的
- ❌ 请勿用于违法活动
- ⚠️ 使用本工具产生的任何后果由使用者自行承担

---

## ⭐ Star History

如果这个项目对您有帮助，请给个 Star ⭐ 支持一下！

---

**最近更新**：
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
