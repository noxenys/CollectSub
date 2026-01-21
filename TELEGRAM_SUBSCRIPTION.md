# Telegram Bot 私密订阅分发

## 功能说明

筛选出的高质量节点可以通过Telegram Bot私密发送，避免在GitHub公开展示。

## 配置步骤

### 1. 创建Telegram Bot

1. 在Telegram搜索 `@BotFather`
2. 发送 `/newbot` 创建新Bot
3. 按提示设置Bot名称
4. 获得 **Bot Token**（格式：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

### 2. 获取Chat ID

**方法一：使用 @userinfobot**
1. 搜索 `@userinfobot`
2. 发送任意消息
3. 获得你的 **Chat ID**

**方法二：通过API获取**
1. 给你的Bot发送一条消息
2. 访问 `https://api.telegram.org/bot<YourBotToken>/getUpdates`
3. 在返回的JSON中找到 `chat.id`

### 3. 配置环境变量

**方式一：GitHub Secrets（推荐）**
```
仓库Settings → Secrets and variables → Actions → New repository secret

添加两个秘密：
- Name: TELEGRAM_BOT_TOKEN
  Value: 你的Bot Token

- Name: TELEGRAM_CHAT_ID
  Value: 你的Chat ID
```

**方式二：本地环境变量**
```bash
# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"

# Linux/Mac
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## 4. 配置 GITHUB_TOKEN (可选，推荐)

为了生成 **GitHub Gist 订阅链接**（最稳定、私密的订阅方式），你需要配置 `GITHUB_TOKEN`。

1. 访问 [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. 勾选 **gist** 权限
4. 复制生成的Token

**配置环境变量：**
- `GITHUB_TOKEN`: 你的GitHub Token

> **⚠️ GitHub Actions 特别提示**：
> 默认的 `GITHUB_TOKEN` **没有创建 Gist 的权限**。
> 如果你希望在自动运行时生成 Gist 订阅，请：
> 1. 创建一个新的 PAT (Personal Access Token)，勾选 `gist` 权限。
> 2. 在仓库 Secrets 中添加，命名为 **`GIST_TOKEN`**。
> 3. 工作流会自动优先使用它。

## 订阅URL生成功能

工具会自动为你生成可以直接导入的订阅URL，并通过Telegram发送给你。

### 支持的三种方式：

1. **GitHub Gist 订阅** (⭐⭐⭐ 推荐)
   - **原理**: 创建私密Gist，通过GitHub CDN分发
   - **优点**: 私密、高速、稳定、支持所有客户端
   - **要求**: 需要配置 `GITHUB_TOKEN`

2. **订阅转换 URL**
   - **原理**: 使用第三方订阅转换服务（如 dler.io）
   - **优点**: 自动转换为 Clash/Surge/V2Ray 格式
   - **注意**: 链接较长

3. **Base64 原始内容**
   - **原理**: 原始 Base64 编码
   - **优点**: 通用格式，可配合任何转换器使用

### 获取方式

运行脚本后，Bot会发送一个 `_urls.txt` 文件，里面包含所有生成的订阅链接。

## 完整工作流

```
1. python main.py              # 抓取节点
   ↓
2. python node_quality_filter.py  # 筛选高质量节点
   ↓
3. 自动生成订阅连接             # Gist/转换/Base64
   ↓
4. 自动发送到Telegram Bot     # 私密分享文件和链接
   ↓
5. 复制URL导入客户端          # 一键使用
```

## 故障排除

### 问题：没有生成 GitHub Gist 链接

**原因**: 未配置 `GITHUB_TOKEN`。
**解决**: 请在环境变量或 GitHub Secrets 中添加 `GITHUB_TOKEN`。

### 问题：Bot发送失败

**检查项：**
- ✓ Bot Token是否正确
- ✓ Chat ID是否正确
- ✓ 是否给Bot发送过至少一条消息
- ✓ 网络连接是否正常

### 问题：找不到Chat ID

**解决方法：**
```python
# 运行此脚本获取Chat ID
import requests
import os

bot_token = "your_bot_token"
url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
response = requests.get(url)
print(response.json())
```

## 安全提示

⚠️ **重要**：
- Bot Token是敏感信息，不要提交到代码仓库
- 使用GitHub Secrets或环境变量存储
- 定期更换Bot Token
- 不要在公开场合分享Bot Token

## 示例消息

Bot发送的消息示例：

```
🎉 高质量节点订阅

📊 统计信息:
  • 节点总数: 126 个
  • 文件大小: 13.06 KB

💡 使用方法:
1. 下载此文件
2. 直接导入到代理客户端
3. 或使用订阅链接（见下方）

⚠️ 注意: 
- 此订阅为私密分享，请勿公开传播
- 节点质量已筛选，延迟<500ms
- 定期更新，保持订阅最新
```
