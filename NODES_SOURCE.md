# 节点来源说明

## 两个节点文件的来源

### 1. collected_nodes.txt (裸节点文件)
**来源**: `main.py` 在抓取网页(Telegram频道、网页等)时，直接提取的**裸节点链接**

**生成位置**: 
- `main.py` 的 `fetch_urls_from_page()` 方法（第352-358行）
- 使用正则表达式从网页内容中提取 `vmess://`, `vless://`, `trojan://` 等节点协议

**内容**: 只包含节点URL，例如：
```
vless://55d9ec38-1b8a-454b-981a-6acfe8f56d8c@172.64.145.144
trojan://5a2c16f9@104.26.1.110
vmess://ew0KICAidiI6I...
```

**数量**: ~327 个（限制10k条）

---

### 2. sub/sub_all_url_check.txt (完整URL文件) ⭐推荐
**来源**: `main.py` **完整运行**后生成的**所有筛选过的URL**（包括订阅链接和节点）

**内容**: 包含：
- 订阅链接（https://...）
- 节点链接（vless://, vmess://, trojan://...）
- 已经过质量控制筛选

**数量**: ~29,455 个（4MB+）

**优势**:
- ✅ 数据更全面（订阅+节点）
- ✅ 已经过 `main.py` 的质量控制
- ✅ 包含更多节点源

---

## 节点质量筛选工具 (node_quality_filter.py)

### 读取优先级
```
1. 优先读取: sub/sub_all_url_check.txt  (完整URL列表)
2. 备用读取: collected_nodes.txt        (裸节点列表)
```

### 输出位置
```
sub/high_quality_nodes.txt     # 高质量节点列表
sub/quality_report.json        # 质量分析报告
```

---

## 使用建议

### 最佳实践
1. **先运行** `python main.py` - 抓取节点和订阅
2. **再运行** `python node_quality_filter.py` - 筛选高质量节点
3. **查看结果** `sub/high_quality_nodes.txt` - 使用筛选后的节点

### 工作流程
```
Telegram频道 + 网页  →  main.py  →  collected_nodes.txt (裸节点)
                                   →  sub_all_url_check.txt (完整URL)

sub_all_url_check.txt  →  node_quality_filter.py  →  sub/high_quality_nodes.txt
```

---

## 总结

| 文件 | 生成方式 | 内容 | 推荐用途 |
|------|---------|------|----------|
| `collected_nodes.txt` | main.py网页抓取 | 裸节点 | 直接抓取的节点 |
| `sub/sub_all_url_check.txt` | main.py完整运行 | 订阅+节点 | 质量筛选输入 ⭐ |
| `sub/high_quality_nodes.txt` | node_quality_filter.py | 高质量节点 | 最终使用 ⭐⭐ |
