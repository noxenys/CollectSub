# 配置参数详解

本文档完整说明 `config.yaml` 的所有主要参数与推荐值。项目仅支持 5 种协议：
`vmess / ss / trojan / vless / hysteria2`。

---

## 1) 性能配置

```yaml
performance:
  max_workers: 32
  content_limit_mb: 3
  request_timeout: 6
```

- `max_workers`：抓取与解析并发数。Actions 推荐 32-64。
- `content_limit_mb`：单次下载内容上限，避免超大页面耗尽内存。
- `request_timeout`：HTTP 请求超时（秒）。

---

## 2) 订阅质量控制

```yaml
quality_control:
  min_nodes: 3
  enable_duplicate_check: true
  enable_quality_check: true
```

- `min_nodes`：单订阅最少节点数，低于则视为低质量。
- `enable_duplicate_check`：订阅内容去重。
- `enable_quality_check`：订阅质量检查（空订阅、垃圾内容）。

---

## 3) 节点协议

```yaml
nodes:
  protocols:
    - vmess
    - ss
    - trojan
    - vless
    - hysteria2
```

说明：仅允许上述 5 种协议，其它协议会被忽略。

---

## 4) 订阅源配置

```yaml
tgchannel:
  - https://t.me/example_channel

subscribe:
  - https://raw.githubusercontent.com/user/repo/main/sub.yaml

web_pages:
  - https://example.com/free-vpn-list
```

- `tgchannel`：Telegram 频道列表，支持多种写法（完整 URL / 短链 / 频道名）。
- `subscribe`：直连订阅源（GitHub/网站）。
- `web_pages`：网页模糊抓取源（博客、论坛等）。

---

## 5) 订阅转换后端（Subconverter）

```yaml
subconverter_backends:
  - api.dler.io
  - sub.xeton.dev

sub_convert_apis:
  - api.dler.io
  - sub.xeton.dev
```

- `subconverter_backends`：主要使用的转换后端列表。
- `sub_convert_apis`：兼容旧配置的备用后端列表。

---

## 6) 节点质量筛选

```yaml
quality_filter:
  max_workers: 32
  connect_timeout: 5
  max_latency: 500
  min_speed: 0
  max_test_nodes: 5000
  max_output_nodes: 200
  min_guarantee: 150
  preferred_protocols_only: false
  smart_sampling: true

  region_limit:
    enabled: true
    policy: score
    allowed_countries: [US, KR, TW, JP, SG, CA]
    blocked_countries: [CN, RU, IR, KP]

  preferred_protocols:
    - hysteria2
    - vless
    - trojan
    - vmess
    - ss
```

- `max_workers`：筛选并发数。
- `connect_timeout`：连接超时（秒）。
- `max_latency`：最大可接受延迟（毫秒）。
- `min_speed`：最小下载速度，0 表示不测速。
- `max_test_nodes`：最多测试节点数。
- `max_output_nodes`：最终输出数量上限。
- `min_guarantee`：保底输出数量（不足会继续测试）。
- `preferred_protocols_only`：只测试首选协议。
- `smart_sampling`：对超大节点池智能采样。
- `region_limit.policy`：`score`（降分）/ `filter`（丢弃）。

---

## 7) 风险/钓鱼过滤

```yaml
risk_filter:
  enabled: true
  mode: score
  penalty: 6
  max_penalty: 18
  max_path_len: 120
  suspicious_tlds: [tk, xyz, top, icu, cyou]
  phishing_keywords: [login, bank, verify]
  allow_sni_domains: []
  allow_host_domains: []
  allow_path_keywords: []
  block_on:
    sni_phishing: false
    host_phishing: false
    path_phishing: false
    allow_insecure: false
    security_none: false
```

- `mode`：`score`（降分）/ `filter`（丢弃）。
- `penalty/max_penalty`：单项扣分与封顶扣分。
- `max_path_len`：path 超长视为可疑。
- `suspicious_tlds` / `phishing_keywords`：高风险域名后缀与关键词。
- `allow_*`：白名单，用于放行误伤。

---

## 8) IP 风险检测

```yaml
ip_risk_check:
  enabled: true
  provider: ipapi
  check_top_nodes: 300

  ipapi_behavior:
    exclude_hosting: true
    exclude_proxy: false
    exclude_mobile: false

  max_risk_score: 50
  api_key: ""

  asn_filter:
    enabled: true
    mode: score
    penalty: 10
    asn_blacklist: []
    org_blacklist_keywords: []
    isp_blacklist_keywords: []
```

- `provider`：`ipapi`（免 Key）或 `abuseipdb`（需 Key）。
- `check_top_nodes`：仅检测 Top N，权衡速度。
- `ipapi_behavior`：机房/代理/移动 IP 是否降分。
- `asn_filter`：按 ASN/ORG/ISP 过滤或降分。

---

## 9) CN 探测结果加权（可选）

```yaml
cn_probe:
  enabled: false
  results_path: sub/cn_probe.json
  results_url: ""
  weight: 1.0
  max_latency: 800
  max_bonus: 6
```

环境变量：
- `CN_PROBE_URL`
- `CN_PROBE_TOKEN`

---

## 10) CN 测试代理（可选）

```yaml
cn_test_proxy:
  enabled: false
  type: api            # api / http
  api_url: ""
  api_token: ""
  proxy_url: ""
  timeout: 8
  test_url: "https://www.google.com/generate_204"
  expected_status: 204
  required: true
```

说明：用于模拟国内真实访问路径。

---

## 11) 第三方 CN 拨测 API（可选）

```yaml
cn_probe_api:
  enabled: false
  url_template: ""
  method: GET
  timeout: 8
  headers: {}
  success_field: success
  success_values: [true, ok, 1]
  locations_path: data.locations
  location_name_field: city
  location_ok_field: ok
  ok_values: [true, ok, 1]
  require_locations: [北京, 上海, 广州]
```

---

## 12) 动态盲选探测头（Actions 推荐）

```yaml
dynamic_probe:
  enabled: true
  sample_size: 50
  min_success: 5
  force_proxy: true
  proxy_url: ""
  supported_protocols:
    - vless
    - trojan
    - vmess
    - ss
    - hysteria2
  save_path: sub/probe_head.json
```

环境变量：
- `DYNAMIC_PROBE_PROXY_URL`（可选，外部代理兜底）
