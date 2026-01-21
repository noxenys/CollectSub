# 故障排查指南

本文档提供 SmartSub 项目常见问题的诊断和解决方案。

---

## 📋 目录

- [运行问题](#运行问题)
- [订阅抓取问题](#订阅抓取问题)
- [节点质量筛选问题](#节点质量筛选问题)
- [GitHub Actions 问题](#github-actions-问题)
- [Telegram 推送问题](#telegram-推送问题)
- [性能问题](#性能问题)

---

## 运行问题

### ❌ ModuleNotFoundError: No module named 'xxx'

**症状**: 运行时提示缺少依赖模块

**解决方案**:
```bash
# 重新安装依赖
pip install -r requirements.txt

# 或使用国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**预防**: 建议使用虚拟环境
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

### ❌ Config file not found

**症状**: 
```
ERROR - Config file not found: d:\Github\collectSub\config.yaml
```

**原因**: 配置文件不存在或路径错误

**解决方案**:
1. 确认 `config.yaml` 在项目根目录
2. 检查文件名是否正确（区分大小写）
3. 如果缺失，从 GitHub 重新下载或复制默认配置

---

### ❌ Permission Denied 错误

**症状**: 无法创建或写入文件

**解决方案**:
```bash
# Linux/Mac: 检查文件权限
ls -l config.yaml
chmod 644 config.yaml

# Windows: 以管理员身份运行
```

---

## 订阅抓取问题

### ⚠️ 抓取的订阅数量很少

**可能原因**:

#### 1. 订阅源失效
**诊断**:
```bash
# 运行后查看日志
python main.py

# 查看失效订阅记录
cat failed_subscriptions.log
```

**解决方案**:
- 查看 `failed_subscriptions.log` 找出失效的订阅源
- 从 `config.yaml` 中移除或更新失效源
- 添加新的订阅源

#### 2. 网络连接问题
**诊断**:
```bash
# 检查网络连接
ping github.com
ping raw.githubusercontent.com
```

**解决方案**:
- 检查防火墙设置
- 使用代理：设置环境变量
  ```bash
  # Windows PowerShell
  $env:HTTP_PROXY="http://127.0.0.1:7890"
  $env:HTTPS_PROXY="http://127.0.0.1:7890"
  
  # Linux/Mac
  export HTTP_PROXY="http://127.0.0.1:7890"
  export HTTPS_PROXY="http://127.0.0.1:7890"
  ```

#### 3. 质量控制过于严格
**症状**: 日志中大量 "节点过少" 或 "质量不达标" 提示

**解决方案**: 放宽 `config.yaml` 中的质量控制参数
```yaml
quality_control:
  min_nodes: 2              # 从 3 降低到 2
  enable_quality_check: false  # 暂时关闭质量检查
```

---

### ⚠️ Telegram 频道抓取失败

**症状**: 
```
WARNING - https://t.me/s/xxx遇到 403 (可能 IP 被屏蔽)
```

**原因**: Telegram 对爬虫有限制，可能被临时封禁

**解决方案**:
1. **等待一段时间**（通常1-24小时后自动解除）
2. **减少请求频率**:
   ```yaml
   performance:
     request_timeout: 10  # 增加超时时间
     max_workers: 16      # 减少并发数
   ```
3. **使用代理**（如果在中国大陆）
4. **暂时注释掉部分 Telegram 频道**，分批抓取

---

### ⚠️ 黑名单文件过大

**症状**: 
```
WARNING - 黑名单行数 (60000) 超过限制 (50000)，执行自动清理...
```

**解决方案**: 
- 系统会自动清理，保留最新的 50,000 条
- 如需完全重置：
  ```bash
  # 备份
  cp blacklist.txt blacklist.txt.bak
  # 清空
  > blacklist.txt
  ```

---

## 节点质量筛选问题

### ❌ 筛选后节点数量为 0

**可能原因**:

#### 1. 输入文件不存在或为空
**诊断**:
```bash
# 检查输入文件
ls -lh sub/sub_all_url_check.txt
ls -lh collected_nodes.txt
```

**解决方案**: 先运行 `main.py` 抓取节点
```bash
python main.py
```

#### 2. 所有节点都无法连接
**症状**: 日志显示大量 "offline" 或 "timeout"

**解决方案**:
```yaml
quality_filter:
  connect_timeout: 10      # 增加超时时间
  max_latency: 1000        # 提高延迟上限
```

#### 3. IP 风险检测过于严格
**症状**: 日志显示 "发现风险IP" 并淘汰

**解决方案**:
```yaml
ip_risk_check:
  enabled: false           # 暂时关闭 IP 检测
  # 或
  ipapi_behavior:
    exclude_hosting: false  # 允许机房 IP
```

---

### ⚠️ 筛选速度很慢

**症状**: 测试数千个节点耗时过长

**解决方案**:
```yaml
quality_filter:
  max_workers: 64          # 增加并发（根据机器性能）
  connect_timeout: 3       # 减少超时时间
  max_test_nodes: 3000     # 减少测试数量
  
ip_risk_check:
  check_top_nodes: 100     # 减少 IP 检测数量
```

---

### ⚠️ IP-API 速率限制

**症状**: 
```
WARNING - IP-API 检测异常: HTTPError 429
```

**原因**: IP-API 免费版限制 45 次/分钟

**解决方案**:
1. **减少检测数量**:
   ```yaml
   ip_risk_check:
     check_top_nodes: 50   # 降低到 50
   ```
2. **增加延迟**（代码中已有 1.5 秒延迟）
3. **使用 AbuseIPDB**（需要 API Key）:
   ```yaml
   ip_risk_check:
     provider: abuseipdb
     api_key: "your_api_key_here"
   ```

---

### ⚠️ 节点解析失败

**症状**: 
```
INFO - 解析成功: 0 个节点
```

**可能原因**: 节点格式不符合规范

**解决方案**:
1. 检查输入文件内容是否正确
2. 确认节点包含协议前缀（`vmess://`, `ss://` 等）
3. 查看日志中的详细错误信息

---

## GitHub Actions 问题

### ❌ Workflow 运行失败

**常见错误**:

#### 1. Python 依赖安装失败
**症状**: 
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案**: 检查 `requirements.txt` 格式，确保版本号正确

#### 2. Git push 失败
**症状**: 
```
! [rejected] main -> main (fetch first)
```

**解决方案**: 
- 检查 Actions 是否有写入权限
- 在仓库设置中启用 `Read and write permissions`
  1. Settings → Actions → General
  2. Workflow permissions → Read and write permissions

#### 3. 超时错误
**症状**: 
```
Error: The operation was canceled.
```

**解决方案**: 减少测试数量
```yaml
quality_filter:
  max_test_nodes: 3000     # 减少到 3000
  max_output_nodes: 100    # 减少到 100
```

---

### ⚠️ 定时任务未触发

**诊断**:
1. 检查 `.github/workflows/fetch.yaml` 中的 cron 设置
2. 确认仓库有至少一次手动触发（首次需要手动运行）
3. 查看 Actions 历史记录

**解决方案**:
```yaml
# 测试用：每小时运行一次
schedule:
  - cron: '0 * * * *'

# 生产环境：每天凌晨 4 点
schedule:
  - cron: '0 20 * * *'  # UTC 20:00 = 北京时间 04:00
```

---

### ⚠️ Secrets 未配置

**症状**: Telegram 推送失败或 Gist 创建失败

**解决方案**:
1. 进入仓库 Settings → Secrets and variables → Actions
2. 添加必要的 Secrets:
   - `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
   - `TELEGRAM_CHAT_ID`: Telegram Chat ID
   - `GIST_TOKEN`: GitHub Personal Access Token (需要 gist 权限)
   - `ABUSEIPDB_API_KEY`: (可选) AbuseIPDB API Key

---

## Telegram 推送问题

### ❌ Telegram 消息发送失败

**症状**: 
```
⚠️ Telegram消息发送失败: 401
```

**原因**: Bot Token 或 Chat ID 错误

**解决方案**:
1. **验证 Bot Token**:
   ```bash
   curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
   ```
2. **获取正确的 Chat ID**:
   - 向 Bot 发送消息
   - 访问 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - 查找 `"chat":{"id":123456789}`

---

### ⚠️ Gist 创建失败

**症状**: 
```
❌ Gist创建失败: HTTP 401
```

**解决方案**:
1. 检查 `GITHUB_TOKEN` 或 `GIST_TOKEN` 是否配置
2. 确认 Token 有 `gist` 权限
3. 创建新的 Personal Access Token:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token (classic)
   - 勾选 `gist` 权限

---

## 性能问题

### ⚠️ 内存占用过高

**症状**: 程序运行时内存持续增长

**可能原因**:
1. 节点数量过多
2. 黑名单文件过大
3. 并发数过高

**解决方案**:
```yaml
performance:
  max_workers: 16          # 降低并发
  content_limit_mb: 2      # 降低下载限制

quality_filter:
  max_test_nodes: 3000     # 减少测试数量
```

**清理缓存**:
```bash
# 清理大文件
rm -f blacklist.txt.bak
rm -f collected_nodes.txt.bak
```

---

### ⚠️ CPU 占用过高

**解决方案**:
```yaml
performance:
  max_workers: 8           # 大幅降低并发

quality_filter:
  max_workers: 8
```

---

## 日志分析

### 查看详细日志

**main.py 日志位置**:
- 控制台输出（使用 loguru）
- `failed_subscriptions.log` - 失效订阅记录

**node_quality_filter.py 日志位置**:
- 控制台输出
- `sub/quality_report.json` - 质量报告

### 日志等级说明

- `INFO`: 正常流程信息
- `WARNING`: 警告（不影响运行）
- `ERROR`: 错误（可能影响结果）
- `DEBUG`: 调试信息（默认不显示）

---

## 常见问题速查表

| 问题 | 可能原因 | 快速解决 |
|------|---------|---------|
| 节点数量为 0 | 输入文件为空 | 先运行 `python main.py` |
| 抓取速度很慢 | 并发数太小 | 增加 `max_workers` |
| 内存占用过高 | 测试节点过多 | 减少 `max_test_nodes` |
| Telegram 失败 | Token/ChatID 错误 | 检查 Secrets 配置 |
| IP-API 限流 | 检测数量过多 | 减少 `check_top_nodes` |
| 所有节点超时 | 超时设置过短 | 增加 `connect_timeout` |

---

## 获取帮助

如果以上方案都无法解决问题：

1. **查看日志**: 详细阅读控制台输出和日志文件
2. **检查配置**: 对照 [CONFIGURATION.md](CONFIGURATION.md) 检查配置
3. **提交 Issue**: 
   - 提供完整的错误日志
   - 说明运行环境（操作系统、Python 版本）
   - 附上配置文件（脱敏后）

---

## 相关文档

- [README.md](../README.md) - 项目概览
- [CONFIGURATION.md](CONFIGURATION.md) - 配置参数详解
- [节点格式规范](../README.md#节点格式规范) - 输出节点的命名规则
