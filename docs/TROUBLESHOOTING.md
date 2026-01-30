# 故障排查指南

## 运行失败 / 缺少依赖

```bash
pip install -r requirements.txt
```

如果网络较慢，可使用镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 配置自检失败

```bash
python scripts/self_check.py
```

- 检查 `config.yaml` 是否存在与格式是否正确  
- 检查协议范围（仅允许 vmess/ss/trojan/vless/hysteria2）  
- 提示订阅源重复条目

---

## 订阅源清理

```bash
python scripts/clean_sources.py
```

需要最近一次运行生成的 `sub/source_health.json`，可自动移除 404 与低质量来源。

---

## 没有抓到订阅/节点

可能原因与处理：
1) 订阅源失效 → 检查 `config.yaml` 中的 `tgchannel/subscribe/web_pages`。  
2) 网络受限 → 设置 `HTTP_PROXY/HTTPS_PROXY`。  
3) 质量控制过严 → 调低 `quality_control.min_nodes` 或关闭 `enable_quality_check`。  

---

## Telegram 频道抓取失败（403/429）

- Telegram 有访问频控，建议降低 `performance.max_workers`，增加 `request_timeout`。
- 必要时使用代理环境变量：

```bash
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
```

---

## 节点筛选结果为 0

常见原因：
1) `collected_nodes.txt` 或 `sub/sub_all_url_check.txt` 为空  
2) `quality_filter.max_latency` 太低  
3) CN 测试代理失败且 `cn_test_proxy.required=true`

建议：
- 先跑 `main.py` 确保输入存在  
- 放宽 `max_latency`  
- 或暂时关闭 CN 真实性检测

---

## Actions 里探测代理失败

当 `sing-box` 启动失败或代理不可用时，会跳过本地代理：
- 检查 `sub/singbox.log`
- 确认 `sub/probe_head.json` 是否生成
- 需要兜底代理时可设置 `DYNAMIC_PROBE_PROXY_URL`
