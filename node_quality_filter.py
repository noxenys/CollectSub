#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

节点质量筛选工具

功能：

1. 测试节点连通性

2. 测试节点延迟

3. 测试下载速度

4. 按协议类型筛选

5. 节点去重

"""

import os

import re

import json

import time

import socket

import base64

import asyncio

import requests

import yaml

import random

import urllib.parse

import httpx

import argparse

from loguru import logger

from tqdm import tqdm

class NodeQualityFilter:

    def __init__(self, config_path='config.yaml'):

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.config_path = os.path.join(self.base_dir, config_path)

        # 输入输出文件

        # 支持两个输入源

        self.input_file_collected = os.path.join(self.base_dir, 'collected_nodes.txt')  # 裸节点源

        self.input_file_all = os.path.join(self.base_dir, 'sub', 'sub_all_url_check.txt')  # 完整URL源

        # 输出文件放在 sub 文件夹

        self.sub_dir = os.path.join(self.base_dir, 'sub')

        self.output_file = os.path.join(self.sub_dir, 'high_quality_nodes.txt')

        self.report_file = os.path.join(self.sub_dir, 'quality_report.json')

        # 确保输出目录存在

        if not os.path.exists(self.sub_dir):

            os.makedirs(self.sub_dir)

        # 默认配置

        self.max_workers = 32

        self.connect_timeout = 5

        self.max_latency = 500  # 最大延迟(ms)

        self.min_speed = 0  # 最小速度(KB/s)，0表示不测速

        # 大规模节点处理配置

        self.max_test_nodes = 5000  # 最多测试节点数

        self.max_output_nodes = 200  # 最多输出节点数

        self.preferred_protocols_only = False  # 是否只测试首选协议

        self.smart_sampling = True  # 智能采样

        # 协议优先级 (分数越高越好)

        self.protocol_scores = {

            'hysteria2': 10,

            'vless': 9,

            'trojan': 8,

            'vmess': 7,

            'ss': 6

        }

        # 首选协议列表

        self.preferred_protocols = ['hysteria2', 'vless', 'trojan', 'vmess', 'ss']

        # CN probe defaults (optional)

        self.cn_probe_enabled = False

        self.cn_probe_results_path = os.path.join(self.sub_dir, 'cn_probe.json')

        self.cn_probe_url = os.getenv('CN_PROBE_URL', '')

        self.cn_probe_token = os.getenv('CN_PROBE_TOKEN', '')

        self.cn_probe_weight = 1.0

        self.cn_probe_max_latency = 800

        self.cn_probe_max_bonus = 6

        self.cn_probe_results = {}

        self.cn_probe_matched = 0

        # Risk/phishing filter defaults (optional)

        self.risk_filter_enabled = False

        self.risk_filter_mode = 'score'

        self.risk_filter_penalty = 6

        self.risk_filter_max_penalty = 18

        self.risk_filter_max_path_len = 120

        self.risk_filter_suspicious_tlds = []

        self.risk_filter_phishing_keywords = []

        self.risk_filter_allow_sni_domains = []

        self.risk_filter_allow_host_domains = []

        self.risk_filter_allow_path_keywords = []

        self.risk_filter_block_on = {}

        self.risk_filter_blocked = 0

        self.risk_filter_penalized = 0

        # ASN/ISP/ORG filter (ipapi only)

        self.asn_filter_enabled = False

        self.asn_filter_mode = 'score'

        self.asn_filter_penalty = 10

        self.asn_filter_asn_blacklist = []

        self.asn_filter_org_keywords = []

        self.asn_filter_isp_keywords = []

        self.asn_filter_blocked = 0

        self.asn_filter_penalized = 0

        # Dynamic probe head (optional)

        self.dynamic_probe_enabled = False

        self.dynamic_probe_sample_size = 50

        self.dynamic_probe_min_success = 5

        self.dynamic_probe_force_proxy = True

        self.dynamic_probe_proxy_url = ''

        self.dynamic_probe_save_path = os.path.join(self.sub_dir, 'probe_head.json')

        self.dynamic_probe_node = None

        self.dynamic_probe_supported_protocols = ['vless', 'trojan', 'vmess', 'ss', 'hysteria2']

        # CN test proxy (optional)

        self.cn_test_proxy_enabled = False

        self.cn_test_proxy_type = 'api'

        self.cn_test_proxy_api_url = ''

        self.cn_test_proxy_api_token = ''

        self.cn_test_proxy_url = ''

        self.cn_test_proxy_timeout = 8

        self.cn_test_proxy_test_url = 'https://www.google.com/generate_204'

        self.cn_test_proxy_expected_status = 204

        self.cn_test_proxy_required = True

        # Third-party CN probe API (optional)

        self.cn_probe_api_enabled = False

        self.cn_probe_api_url_template = ''

        self.cn_probe_api_method = 'GET'

        self.cn_probe_api_timeout = 8

        self.cn_probe_api_headers = {}

        self.cn_probe_api_success_field = 'success'

        self.cn_probe_api_success_values = [True, 'ok', 1]

        self.cn_probe_api_locations_path = 'data.locations'

        self.cn_probe_api_location_name_field = 'city'

        self.cn_probe_api_location_ok_field = 'ok'

        self.cn_probe_api_ok_values = [True, 'ok', 1]

        self.cn_probe_api_require_locations = ['北京', '上海', '广州']

        self.load_config()

    def load_config(self):

        """加载配置文件"""

        try:

            if os.path.exists(self.config_path):

                with open(self.config_path, 'r', encoding='utf-8') as f:

                    config = yaml.safe_load(f)

                # 读取质量筛选配置

                quality_filter = config.get('quality_filter', {})

                self.max_workers = quality_filter.get('max_workers', 32)

                self.connect_timeout = quality_filter.get('connect_timeout', 5)

                self.max_latency = quality_filter.get('max_latency', 500)

                self.min_speed = quality_filter.get('min_speed', 0)

                self.preferred_protocols = quality_filter.get('preferred_protocols', self.preferred_protocols)

                # 大规模节点处理配置

                self.max_test_nodes = quality_filter.get('max_test_nodes', 5000)

                self.max_output_nodes = quality_filter.get('max_output_nodes', 200)

                self.preferred_protocols_only = quality_filter.get('preferred_protocols_only', False)

                self.smart_sampling = quality_filter.get('smart_sampling', True)

                # IP风险检测配置

                self.ip_risk_config = config.get('ip_risk_check', {})

                self.ip_risk_config.setdefault('enabled', False)

                self.ip_risk_config.setdefault('check_top_nodes', 50)

                self.ip_risk_config.setdefault('max_risk_score', 50)

                logger.info(f'已加载配置: 线程数={self.max_workers}, 超时={self.connect_timeout}s, 最大延迟={self.max_latency}ms')

                logger.info(f'大规模优化: 最多测试={self.max_test_nodes}, 最多输出={self.max_output_nodes}, 首选协议={self.preferred_protocols_only}')

                if self.ip_risk_config['enabled']:

                    logger.info(f'🛡️ IP风险检测已开启 (Top {self.ip_risk_config["check_top_nodes"]})')

                # 读取区域限制配置

                self.region_config = quality_filter.get('region_limit', {})

                if self.region_config.get('enabled'):

                   allowed = self.region_config.get('allowed_countries', [])

                   logger.info(f'🌍 区域限制已开启: 白名单={allowed if allowed else "关闭"}, 策略={self.region_config.get("policy", "filter")}')

                # CN probe config

                self.cn_probe_config = config.get('cn_probe', {})

                self.cn_probe_enabled = bool(self.cn_probe_config.get('enabled', False))

                results_path = self.cn_probe_config.get('results_path', self.cn_probe_results_path)

                if results_path:

                    self.cn_probe_results_path = results_path

                if not os.path.isabs(self.cn_probe_results_path):

                    self.cn_probe_results_path = os.path.join(self.base_dir, self.cn_probe_results_path)

                self.cn_probe_url = os.getenv('CN_PROBE_URL') or self.cn_probe_config.get('results_url', self.cn_probe_url)

                self.cn_probe_token = os.getenv('CN_PROBE_TOKEN') or self.cn_probe_config.get('token', self.cn_probe_token)

                self.cn_probe_weight = float(self.cn_probe_config.get('weight', self.cn_probe_weight))

                self.cn_probe_max_latency = int(self.cn_probe_config.get('max_latency', self.cn_probe_max_latency))

                self.cn_probe_max_bonus = float(self.cn_probe_config.get('max_bonus', self.cn_probe_max_bonus))

                self.cn_probe_results = self._load_cn_probe_results()

                if self.cn_probe_enabled:

                    logger.info(f'🇨🇳 CN probe 已启用: 匹配={len(self.cn_probe_results)} 条, 权重={self.cn_probe_weight}')

                # Risk/phishing filter config

                risk_filter = config.get('risk_filter', {})

                self.risk_filter_enabled = bool(risk_filter.get('enabled', False))

                self.risk_filter_mode = str(risk_filter.get('mode', self.risk_filter_mode)).lower()

                self.risk_filter_penalty = int(risk_filter.get('penalty', self.risk_filter_penalty))

                self.risk_filter_max_penalty = int(risk_filter.get('max_penalty', self.risk_filter_max_penalty))

                self.risk_filter_max_path_len = int(risk_filter.get('max_path_len', self.risk_filter_max_path_len))

                self.risk_filter_suspicious_tlds = [t.lower().lstrip('.') for t in risk_filter.get('suspicious_tlds', [])]

                self.risk_filter_phishing_keywords = [k.lower() for k in risk_filter.get('phishing_keywords', [])]

                self.risk_filter_allow_sni_domains = [d.lower().lstrip('.') for d in risk_filter.get('allow_sni_domains', [])]

                self.risk_filter_allow_host_domains = [d.lower().lstrip('.') for d in risk_filter.get('allow_host_domains', [])]

                self.risk_filter_allow_path_keywords = [k.lower() for k in risk_filter.get('allow_path_keywords', [])]

                self.risk_filter_block_on = risk_filter.get('block_on', {}) if isinstance(risk_filter.get('block_on', {}), dict) else {}

                if self.risk_filter_enabled:

                    logger.info(f'🛡️ 风险/钓鱼过滤已启用: mode={self.risk_filter_mode}, penalty={self.risk_filter_penalty}')

                # ASN filter config (ipapi only)

                asn_filter = self.ip_risk_config.get('asn_filter', {}) if isinstance(self.ip_risk_config, dict) else {}

                self.asn_filter_enabled = bool(asn_filter.get('enabled', False))

                self.asn_filter_mode = str(asn_filter.get('mode', self.asn_filter_mode)).lower()

                self.asn_filter_penalty = int(asn_filter.get('penalty', self.asn_filter_penalty))

                self.asn_filter_asn_blacklist = [str(a).lower().replace('as', '') for a in asn_filter.get('asn_blacklist', [])]

                self.asn_filter_org_keywords = [k.lower() for k in asn_filter.get('org_blacklist_keywords', [])]

                self.asn_filter_isp_keywords = [k.lower() for k in asn_filter.get('isp_blacklist_keywords', [])]

                if self.asn_filter_enabled:

                    logger.info(f'🧭 ASN/ORG/ISP 黑名单已启用: mode={self.asn_filter_mode}, penalty={self.asn_filter_penalty}')

                # CN test proxy config

                cn_test_proxy = config.get('cn_test_proxy', {}) if isinstance(config, dict) else {}

                self.cn_test_proxy_enabled = bool(cn_test_proxy.get('enabled', False))

                self.cn_test_proxy_type = str(cn_test_proxy.get('type', self.cn_test_proxy_type)).lower()

                self.cn_test_proxy_api_url = cn_test_proxy.get('api_url', self.cn_test_proxy_api_url) or ''

                self.cn_test_proxy_api_token = cn_test_proxy.get('api_token', self.cn_test_proxy_api_token) or ''

                self.cn_test_proxy_url = cn_test_proxy.get('proxy_url', self.cn_test_proxy_url) or ''

                self.cn_test_proxy_timeout = int(cn_test_proxy.get('timeout', self.cn_test_proxy_timeout))

                self.cn_test_proxy_test_url = cn_test_proxy.get('test_url', self.cn_test_proxy_test_url)

                self.cn_test_proxy_expected_status = int(cn_test_proxy.get('expected_status', self.cn_test_proxy_expected_status))

                self.cn_test_proxy_required = bool(cn_test_proxy.get('required', self.cn_test_proxy_required))

                if self.cn_test_proxy_enabled:

                    logger.info(f'🇨🇳 CN 测试代理已启用: type={self.cn_test_proxy_type}, required={self.cn_test_proxy_required}')

                # CN probe API config (third-party)

                cn_probe_api = config.get('cn_probe_api', {}) if isinstance(config, dict) else {}

                self.cn_probe_api_enabled = bool(cn_probe_api.get('enabled', False))

                self.cn_probe_api_url_template = cn_probe_api.get('url_template', self.cn_probe_api_url_template) or ''

                self.cn_probe_api_method = str(cn_probe_api.get('method', self.cn_probe_api_method)).upper()

                self.cn_probe_api_timeout = int(cn_probe_api.get('timeout', self.cn_probe_api_timeout))

                self.cn_probe_api_headers = cn_probe_api.get('headers', self.cn_probe_api_headers) or {}

                self.cn_probe_api_success_field = cn_probe_api.get('success_field', self.cn_probe_api_success_field)

                self.cn_probe_api_success_values = cn_probe_api.get('success_values', self.cn_probe_api_success_values)

                self.cn_probe_api_locations_path = cn_probe_api.get('locations_path', self.cn_probe_api_locations_path)

                self.cn_probe_api_location_name_field = cn_probe_api.get('location_name_field', self.cn_probe_api_location_name_field)

                self.cn_probe_api_location_ok_field = cn_probe_api.get('location_ok_field', self.cn_probe_api_location_ok_field)

                self.cn_probe_api_ok_values = cn_probe_api.get('ok_values', self.cn_probe_api_ok_values)

                self.cn_probe_api_require_locations = cn_probe_api.get('require_locations', self.cn_probe_api_require_locations)

                if self.cn_probe_api_enabled:

                    logger.info('🌏 已启用第三方国内拨测 API')

                # Dynamic probe config

                dynamic_probe = config.get('dynamic_probe', {}) if isinstance(config, dict) else {}

                self.dynamic_probe_enabled = bool(dynamic_probe.get('enabled', False))

                self.dynamic_probe_sample_size = int(dynamic_probe.get('sample_size', self.dynamic_probe_sample_size))

                self.dynamic_probe_min_success = int(dynamic_probe.get('min_success', self.dynamic_probe_min_success))

                self.dynamic_probe_force_proxy = bool(dynamic_probe.get('force_proxy', self.dynamic_probe_force_proxy))

                self.dynamic_probe_proxy_url = os.getenv('DYNAMIC_PROBE_PROXY_URL') or dynamic_probe.get('proxy_url', self.dynamic_probe_proxy_url) or ''

                supported = dynamic_probe.get('supported_protocols', self.dynamic_probe_supported_protocols)

                if isinstance(supported, list) and supported:

                    self.dynamic_probe_supported_protocols = [str(p).lower() for p in supported]

                save_path = dynamic_probe.get('save_path', self.dynamic_probe_save_path)

                if save_path:

                    self.dynamic_probe_save_path = os.path.join(self.base_dir, save_path) if not os.path.isabs(save_path) else save_path

                if self.dynamic_probe_enabled:

                    logger.info(f'🛰️ 动态盲选探测头已启用: sample={self.dynamic_probe_sample_size}, min_success={self.dynamic_probe_min_success}')

        except Exception as e:

            logger.warning(f'加载配置失败，使用默认配置: {e}')

    def _load_cn_probe_results(self):

        """Load CN probe data from URL or local file."""

        if not self.cn_probe_enabled:

            return {}

        data = None

        if self.cn_probe_url:

            try:

                headers = {}

                if self.cn_probe_token:

                    headers['Authorization'] = f'Bearer {self.cn_probe_token}'

                response = requests.get(self.cn_probe_url, headers=headers, timeout=10)

                if response.status_code == 200:

                    data = response.json()

                else:

                    logger.warning(f'⚠️ CN probe URL 获取失败: HTTP {response.status_code}')

            except Exception as e:

                logger.warning(f'⚠️ CN probe URL 读取失败: {e}')

        if data is None and os.path.exists(self.cn_probe_results_path):

            try:

                with open(self.cn_probe_results_path, 'r', encoding='utf-8') as f:

                    data = json.load(f)

            except Exception as e:

                logger.warning(f'⚠️ CN probe 文件读取失败: {e}')

        if data is None:

            logger.info('ℹ️ CN probe 已启用，但未找到结果数据')

            return {}

        return self._normalize_cn_probe_data(data)

    def _normalize_cn_probe_data(self, data):

        """Normalize CN probe data into {key: {latency, score}} format."""

        results = {}

        if isinstance(data, dict):

            if isinstance(data.get('nodes'), list):

                items = data.get('nodes', [])

            else:

                for key, value in data.items():

                    if key in ('meta', 'nodes'):

                        continue

                    entry = self._extract_cn_probe_entry(value)

                    if entry:

                        results[key] = entry

                return results

        elif isinstance(data, list):

            items = data

        else:

            return results

        for item in items:

            if not isinstance(item, dict):

                continue

            host = item.get('host') or item.get('ip')

            port = item.get('port')

            if not host or not port:

                continue

            key = f"{host}:{port}"

            entry = self._extract_cn_probe_entry(item)

            if entry:

                results[key] = entry

        return results

    def _extract_cn_probe_entry(self, obj):

        if isinstance(obj, (int, float)):

            return {'latency': float(obj), 'score': None}

        if not isinstance(obj, dict):

            return None

        latency = None

        for key in ('latency_ms', 'latency', 'rtt', 'avg', 'mean'):

            if key in obj:

                try:

                    latency = float(obj[key])

                except Exception:

                    latency = None

                break

        score = None

        for key in ('score', 'cn_score'):

            if key in obj:

                try:

                    score = float(obj[key])

                except Exception:

                    score = None

                break

        if latency is None and score is None:

            return None

        return {'latency': latency, 'score': score}

    def _attach_cn_probe(self, nodes):

        if not self.cn_probe_enabled or not self.cn_probe_results:

            return

        matched = 0

        for node in nodes:

            key = f"{node['host']}:{node['port']}"

            entry = self.cn_probe_results.get(key)

            if not entry:

                continue

            if entry.get('latency') is not None:

                node['cn_latency'] = entry['latency']

            if entry.get('score') is not None:

                node['cn_score'] = entry['score']

            matched += 1

        self.cn_probe_matched = matched

    def _cn_probe_bonus(self, node_info):

        if not self.cn_probe_enabled:

            return None

        if 'cn_score' in node_info and node_info.get('cn_score') is not None:

            try:

                score = float(node_info['cn_score'])

                # assume 0-100

                return (score / 100.0) * self.cn_probe_max_bonus

            except Exception:

                pass

        if 'cn_latency' not in node_info or node_info.get('cn_latency') is None:

            return None

        try:

            latency = float(node_info['cn_latency'])

        except Exception:

            return None

        if latency < 100:

            return self.cn_probe_max_bonus

        if latency < 200:

            return self.cn_probe_max_bonus * 0.7

        if latency < 300:

            return self.cn_probe_max_bonus * 0.4

        if latency < 500:

            return self.cn_probe_max_bonus * 0.2

        if latency > self.cn_probe_max_latency:

            return -self.cn_probe_max_bonus * 0.5

        return 0.0

    def _sort_key(self, node):

        return (

            node.get('final_score', 0),

            -node.get('cn_latency', 999),

            -node.get('latency', 999)

        )

    def _get_by_path(self, data, path):

        if not path:

            return None

        current = data

        for part in str(path).split('.'):

            if isinstance(current, dict) and part in current:

                current = current[part]

            else:

                return None

        return current

    def _value_matches(self, value, allowed_values):

        for allowed in allowed_values or []:

            if value == allowed:

                return True

            if isinstance(value, str) and isinstance(allowed, str) and value.lower() == allowed.lower():

                return True

        return False

    def _normalize_domain(self, value):

        if not value:

            return ''

        text = str(value).strip().lower()

        if '://' in text:

            try:

                text = urllib.parse.urlparse(text).netloc or text

            except Exception:

                pass

        if ',' in text:

            text = text.split(',', 1)[0]

        if ':' in text:

            text = text.split(':', 1)[0]

        return text.strip('.')

    def _domain_allowed(self, domain, allow_list):

        if not domain or not allow_list:

            return False

        for item in allow_list:

            if domain == item or domain.endswith('.' + item):

                return True

        return False

    def _contains_phishing_keyword(self, text):

        if not text:

            return False

        text = str(text).lower()

        for kw in self.risk_filter_phishing_keywords:

            if kw and kw in text:

                return True

        return False

    def _apply_risk_filter(self, node_info):

        """Return (block, penalty, flags) based on rule heuristics."""

        if not self.risk_filter_enabled:

            return False, 0, []

        flags = []

        penalty = 0

        block = False

        def add_flag(flag_key, should_block=False):

            nonlocal penalty, block

            flags.append(flag_key)

            if should_block or self.risk_filter_mode == 'filter':

                block = True

            else:

                penalty += self.risk_filter_penalty

        allow_insecure = node_info.get('allow_insecure')

        if allow_insecure:

            add_flag('allow_insecure', self.risk_filter_block_on.get('allow_insecure', False))

        security = str(node_info.get('security') or '').lower()

        tls_val = str(node_info.get('tls') or '').lower()

        if security in ('none', 'plain') or tls_val in ('0', 'false', 'none'):

            add_flag('security_none', self.risk_filter_block_on.get('security_none', False))

        sni = self._normalize_domain(node_info.get('sni'))

        host_header = self._normalize_domain(node_info.get('host_header'))

        path = str(node_info.get('path') or '')

        # suspicious tld

        if self.risk_filter_suspicious_tlds:

            if sni and any(sni.endswith('.' + tld) or sni == tld for tld in self.risk_filter_suspicious_tlds):

                add_flag('sni_suspicious_tld', self.risk_filter_block_on.get('sni_phishing', False))

            if host_header and any(host_header.endswith('.' + tld) or host_header == tld for tld in self.risk_filter_suspicious_tlds):

                add_flag('host_suspicious_tld', self.risk_filter_block_on.get('host_phishing', False))

        # phishing keyword checks with allowlist

        if sni and not self._domain_allowed(sni, self.risk_filter_allow_sni_domains):

            if self._contains_phishing_keyword(sni):

                add_flag('sni_phishing', self.risk_filter_block_on.get('sni_phishing', False))

            if sni.startswith('xn--'):

                add_flag('sni_punycode', self.risk_filter_block_on.get('sni_phishing', False))

        if host_header and not self._domain_allowed(host_header, self.risk_filter_allow_host_domains):

            if self._contains_phishing_keyword(host_header):

                add_flag('host_phishing', self.risk_filter_block_on.get('host_phishing', False))

            if host_header.startswith('xn--'):

                add_flag('host_punycode', self.risk_filter_block_on.get('host_phishing', False))

        if path:

            if self.risk_filter_max_path_len and len(path) > self.risk_filter_max_path_len:

                add_flag('path_too_long', self.risk_filter_block_on.get('path_phishing', False))

            allow_path = False

            for kw in self.risk_filter_allow_path_keywords:

                if kw and kw in path.lower():

                    allow_path = True

                    break

            if not allow_path and self._contains_phishing_keyword(path):

                add_flag('path_phishing', self.risk_filter_block_on.get('path_phishing', False))

        if penalty > self.risk_filter_max_penalty:

            penalty = self.risk_filter_max_penalty

        return block, penalty, flags

    def _apply_asn_filter(self, node_info, ipapi_data):

        """Apply ASN/ORG/ISP blacklist using ipapi data."""

        if not self.asn_filter_enabled or not isinstance(ipapi_data, dict):

            return False, 0, []

        as_text = str(ipapi_data.get('as', '') or '')

        org = str(ipapi_data.get('org', '') or '')

        isp = str(ipapi_data.get('isp', '') or '')

        asn_num = ''

        match = re.search(r'AS(\\d+)', as_text, re.IGNORECASE)

        if match:

            asn_num = match.group(1)

        flags = []

        penalty = 0

        block = False

        def add_flag(flag_key):

            nonlocal penalty, block

            flags.append(flag_key)

            if self.asn_filter_mode == 'filter':

                block = True

            else:

                penalty += self.asn_filter_penalty

        if asn_num and asn_num in self.asn_filter_asn_blacklist:

            add_flag('asn_blacklist')

        org_l = org.lower()

        for kw in self.asn_filter_org_keywords:

            if kw and kw in org_l:

                add_flag('org_blacklist')

                break

        isp_l = isp.lower()

        for kw in self.asn_filter_isp_keywords:

            if kw and kw in isp_l:

                add_flag('isp_blacklist')

                break

        if flags:

            node_info['asn'] = asn_num or as_text

            if org:

                node_info['org'] = org

            if isp:

                node_info['isp'] = isp

        return block, penalty, flags

    def parse_node(self, node_url):

        """解析节点URL，提取协议、地址、端口等信息"""

        try:

            # 提取协议

            if '://' not in node_url:

                return None

            protocol = node_url.split('://')[0].lower()

            if protocol not in self.protocol_scores:

                return None

            node_info = {

                'url': node_url,

                'protocol': protocol,

                'host': None,

                'port': None,

                'score': self.protocol_scores[protocol]

            }

            # 解析不同协议

            if protocol == 'vmess':

                node_info.update(self._parse_vmess(node_url))

            elif protocol in ['ss']:

                node_info.update(self._parse_ss(node_url))

            elif protocol in ['trojan', 'vless']:

                node_info.update(self._parse_trojan_vless(node_url))

            elif protocol in ['hysteria2']:

                node_info.update(self._parse_hysteria(node_url))

            return node_info if node_info['host'] and node_info['port'] else None

        except Exception as e:

            logger.debug(f'节点解析失败: {node_url[:50]}... - {e}')

            return None

    def _parse_url_params(self, url):

        parsed = urllib.parse.urlparse(url)

        params = urllib.parse.parse_qs(parsed.query)

        def get_param(*names):

            for name in names:

                if name in params and params[name]:

                    return params[name][0]

            return None

        allow_insecure = get_param('allowInsecure', 'allowinsecure', 'insecure')

        if isinstance(allow_insecure, str):

            allow_insecure = allow_insecure.lower() in ('1', 'true', 'yes')

        return {

            'sni': get_param('sni', 'peer', 'serverName', 'servername'),

            'host_header': get_param('host', 'hostHeader', 'ws-host'),

            'path': get_param('path', 'spx', 'ws-path'),

            'security': get_param('security'),

            'tls': get_param('tls'),

            'allow_insecure': allow_insecure

        }

    def _parse_vmess(self, url):

        """解析 vmess 节点"""

        try:

            base64_str = url.replace('vmess://', '')

            # 添加padding

            missing_padding = len(base64_str) % 4

            if missing_padding:

                base64_str += '=' * (4 - missing_padding)

            json_str = base64.b64decode(base64_str).decode('utf-8', errors='ignore')

            config = json.loads(json_str)

            allow_insecure = config.get('allowInsecure')

            if isinstance(allow_insecure, str):

                allow_insecure = allow_insecure.lower() in ('1', 'true', 'yes')

            return {

                'host': config.get('add', ''),

                'port': int(config.get('port', 0)) if config.get('port') else None,

                'sni': config.get('sni') or config.get('servername'),

                'host_header': config.get('host'),

                'path': config.get('path'),

                'security': config.get('tls') or config.get('security'),

                'tls': config.get('tls'),

                'allow_insecure': allow_insecure

            }

        except:

            return {'host': None, 'port': None}

    def _parse_ss(self, url):

        """解析 ss 节点"""

        try:

            # ss://base64

            content = url.split('://')[1].split('#')[0]

            # 尝试解码

            try:

                missing_padding = len(content) % 4

                if missing_padding:

                    content += '=' * (4 - missing_padding)

                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')

                # method:password@host:port

                if '@' in decoded:

                    parts = decoded.split('@')

                    if len(parts) == 2:

                        server_info = parts[1]

                        if ':' in server_info:

                            host, port = server_info.rsplit(':', 1)

                            return {'host': host, 'port': int(port)}

            except:

                pass

            # 尝试直接解析 URL

            match = re.search(r'@([^:]+):(\d+)', url)

            if match:

                return {'host': match.group(1), 'port': int(match.group(2))}

        except:

            pass

        return {'host': None, 'port': None}

    def _parse_trojan_vless(self, url):

        """解析 trojan/vless 节点"""

        try:

            parsed = urllib.parse.urlparse(url)

            host = parsed.hostname

            port = parsed.port or 443

            if host:

                info = {'host': host, 'port': port}

                info.update(self._parse_url_params(url))

                return info

        except:

            pass

        return {'host': None, 'port': None}

    def _parse_hysteria(self, url):

        """解析 hysteria2 节点"""

        try:

            parsed = urllib.parse.urlparse(url)

            host = parsed.hostname

            port = parsed.port or 443

            if host:

                info = {'host': host, 'port': port}

                info.update(self._parse_url_params(url))

                return info

        except:

            pass

        return {'host': None, 'port': None}

    def _run_async(self, coro):

        try:

            return asyncio.run(coro)

        except RuntimeError:

            # already running loop

            loop = asyncio.get_event_loop()

            return loop.run_until_complete(coro)

    def select_dynamic_probe_head(self):

        """Blind select a temporary probe head from collected_nodes.txt."""

        if not self.dynamic_probe_enabled:

            return None

        if not os.path.exists(self.input_file_collected):

            logger.warning('dynamic probe: collected_nodes.txt not found, skip')

            return None

        try:

            with open(self.input_file_collected, 'r', encoding='utf-8') as f:

                raw_nodes = [line.strip() for line in f if line.strip()]

        except Exception as e:

            logger.warning(f'dynamic probe: read failed: {e}')

            return None

        if not raw_nodes:

            logger.warning('dynamic probe: collected_nodes.txt is empty')

            return None

        sample_size = min(self.dynamic_probe_sample_size, len(raw_nodes))

        sample = random.sample(raw_nodes, sample_size)

        parsed = [self.parse_node(u) for u in sample]

        parsed = [p for p in parsed if p]

        if self.dynamic_probe_supported_protocols:

            parsed = [p for p in parsed if p.get('protocol') in self.dynamic_probe_supported_protocols]

        if not parsed:

            logger.warning('dynamic probe: no parsable nodes')

            return None

        results = self._run_async(self._run_connectivity_batch(parsed, batch_idx='probe_head', skip_cn=True))

        if results and self.dynamic_probe_supported_protocols:

            results = [r for r in results if r.get('protocol') in self.dynamic_probe_supported_protocols]

        if not results or len(results) < self.dynamic_probe_min_success:

            logger.warning('dynamic probe: too few success, skip')

            return None

        best = min(results, key=lambda x: x.get('latency', 999999))

        self.dynamic_probe_node = best

        try:

            os.makedirs(os.path.dirname(self.dynamic_probe_save_path), exist_ok=True)

            with open(self.dynamic_probe_save_path, 'w', encoding='utf-8') as f:

                json.dump({'node': best}, f, ensure_ascii=False, indent=2)

        except Exception as e:

            logger.warning(f'dynamic probe: save failed: {e}')

        logger.info(f'dynamic probe locked: {best.get("protocol")}://{best.get("host")}:{best.get("port")} latency={best.get("latency")}ms')

        return best

    async def _async_tcp_connect(self, host, port):

        start_time = time.monotonic()

        try:

            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=self.connect_timeout)

            writer.close()

            try:

                await writer.wait_closed()

            except Exception:

                pass

            latency = (time.monotonic() - start_time) * 1000

            return True, round(latency, 2)

        except Exception:

            return False, None

    async def _http_get(self, client, url):

        start_time = time.monotonic()

        try:

            resp = await client.get(url, follow_redirects=False)

            latency = (time.monotonic() - start_time) * 1000

            ok = resp.status_code == self.cn_test_proxy_expected_status

            return ok, round(latency, 2), resp.status_code

        except Exception:

            return False, None, None

    async def _probe_via_cn_proxy_api(self, client, node_info):

        if not self.cn_test_proxy_enabled or self.cn_test_proxy_type != 'api':

            return None, None

        if not self.cn_test_proxy_api_url:

            return False, None

        headers = {}

        if self.cn_test_proxy_api_token:

            headers['Authorization'] = f'Bearer {self.cn_test_proxy_api_token}'

        payload = {

            'node': node_info.get('url'),

            'host': node_info.get('host'),

            'port': node_info.get('port'),

            'test_url': self.cn_test_proxy_test_url,

            'timeout': self.cn_test_proxy_timeout

        }

        if self.dynamic_probe_node:

            payload['probe_head'] = self.dynamic_probe_node.get('url')

        try:

            resp = await client.post(self.cn_test_proxy_api_url, json=payload, headers=headers)

            if resp.status_code != 200:

                return False, None

            data = resp.json()

            ok = data.get('ok')

            if ok is None:

                ok = data.get('success')

            latency = data.get('latency_ms') or data.get('latency')

            if latency is not None:

                try:

                    latency = float(latency)

                except Exception:

                    latency = None

            return bool(ok), latency

        except Exception:

            return False, None

    async def _probe_via_http_proxy(self, proxy_client):

        if not self.cn_test_proxy_enabled or self.cn_test_proxy_type != 'http':

            return None, None

        if not self.cn_test_proxy_url:

            return False, None

        ok, latency, _ = await self._http_get(proxy_client, self.cn_test_proxy_test_url)

        return ok, latency

    async def _probe_via_cn_api(self, client, host, port):

        if not self.cn_probe_api_enabled or not self.cn_probe_api_url_template:

            return None, None

        url = self.cn_probe_api_url_template.format(host=host, port=port)

        try:

            if self.cn_probe_api_method == 'POST':

                resp = await client.post(url, headers=self.cn_probe_api_headers)

            else:

                resp = await client.get(url, headers=self.cn_probe_api_headers)

            if resp.status_code != 200:

                return False, None

            data = resp.json()

            success_val = self._get_by_path(data, self.cn_probe_api_success_field)

            if self.cn_probe_api_success_field and success_val is not None:

                if not self._value_matches(success_val, self.cn_probe_api_success_values):

                    return False, None

            locations = self._get_by_path(data, self.cn_probe_api_locations_path)

            if isinstance(locations, list) and self.cn_probe_api_require_locations:

                ok_locations = set()

                for item in locations:

                    if not isinstance(item, dict):

                        continue

                    name = item.get(self.cn_probe_api_location_name_field)

                    ok_val = item.get(self.cn_probe_api_location_ok_field)

                    if self._value_matches(ok_val, self.cn_probe_api_ok_values):

                        ok_locations.add(str(name))

                for required in self.cn_probe_api_require_locations:

                    if required not in ok_locations:

                        return False, None

            return True, None

        except Exception:

            return False, None

    async def _async_test_connectivity(self, node_info, api_client, proxy_client, sem, skip_cn=False):

        if not node_info or not node_info['host'] or not node_info['port']:

            return None

        async with sem:

            host = node_info['host']

            port = node_info['port']

            tcp_ok, tcp_latency = await self._async_tcp_connect(host, port)

            if not tcp_ok:

                node_info['status'] = 'offline'

                return None

            node_info['latency'] = tcp_latency or 0

            node_info['status'] = 'online'

            # CN 真实性测试（优先使用 cn_test_proxy）

            if not skip_cn:

                cn_ok = None

                cn_latency = None

                if self.dynamic_probe_proxy_url and self.dynamic_probe_force_proxy and proxy_client is not None:

                    cn_ok, cn_latency = await self._probe_via_http_proxy(proxy_client)

                elif self.cn_test_proxy_enabled:

                    if self.cn_test_proxy_type == 'api':

                        cn_ok, cn_latency = await self._probe_via_cn_proxy_api(api_client, node_info)

                    else:

                        cn_ok, cn_latency = await self._probe_via_http_proxy(proxy_client)

                elif self.cn_probe_api_enabled:

                    cn_ok, cn_latency = await self._probe_via_cn_api(api_client, host, port)

                if cn_ok is False and self.cn_test_proxy_required:

                    return None

                if cn_ok:

                    node_info['cn_ok'] = True

                if cn_latency is not None:

                    node_info['cn_latency'] = cn_latency

            return node_info

    async def _run_connectivity_batch(self, nodes, batch_idx, skip_cn=False):

        sem = asyncio.Semaphore(self.max_workers)

        results = []

        timeout_val = max(self.cn_test_proxy_timeout, self.cn_probe_api_timeout, self.connect_timeout)

        timeout = httpx.Timeout(timeout_val)

        async with httpx.AsyncClient(timeout=timeout) as api_client:

            proxy_client = None

            proxy_url = None

            if self.dynamic_probe_proxy_url:

                proxy_url = self.dynamic_probe_proxy_url

            elif self.cn_test_proxy_enabled and self.cn_test_proxy_type == 'http' and self.cn_test_proxy_url:

                proxy_url = self.cn_test_proxy_url

            if proxy_url:

                async with httpx.AsyncClient(timeout=timeout, proxies=proxy_url) as proxy_client:

                    results = await self._gather_connectivity(nodes, api_client, proxy_client, sem, batch_idx, skip_cn)

            else:

                results = await self._gather_connectivity(nodes, api_client, proxy_client, sem, batch_idx, skip_cn)

        return results

    async def _gather_connectivity(self, nodes, api_client, proxy_client, sem, batch_idx, skip_cn=False):

        results = []

        test_bar = tqdm(total=len(nodes), desc=f'批次 {batch_idx} 测试')

        tasks = [

            self._async_test_connectivity(node, api_client, proxy_client, sem, skip_cn=skip_cn)

            for node in nodes

        ]

        for coro in asyncio.as_completed(tasks):

            try:

                result = await coro

            except Exception:

                result = None

            if result and result.get('latency', float('inf')) <= self.max_latency:

                results.append(result)

            test_bar.update(1)

        test_bar.close()

        return results

    def calculate_score(self, node_info):

        """计算节点综合得分"""

        score = node_info['score']  # 基础协议分数

        # 延迟加分/减分

        if 'latency' in node_info:

            latency = node_info['latency']

            if latency < 100:

                score += 5

            elif latency < 200:

                score += 3

            elif latency < 300:

                score += 1

            elif latency > self.max_latency:

                score -= 5

        # 协议优先级加分

        if node_info['protocol'] in self.preferred_protocols:

            score += 2

        # CN probe bonus (optional)

        cn_bonus = self._cn_probe_bonus(node_info)

        if cn_bonus is not None:

            score += cn_bonus * self.cn_probe_weight

        node_info['final_score'] = score

        return node_info

    def process_nodes(self):

        """处理节点筛选的主流程 (支持保底机制)"""

        nodes = []

        input_source = None

        if os.path.exists(self.input_file_all):

            logger.info(f'📂 从 sub_all_url_check.txt 读取节点...')

            with open(self.input_file_all, 'r', encoding='utf-8') as f:

                nodes = [line.strip() for line in f if line.strip() and '://'in line]

            input_source = 'sub_all_url_check.txt'

        elif os.path.exists(self.input_file_collected):

            logger.info(f'📂 从 collected_nodes.txt 读取节点...')

            with open(self.input_file_collected, 'r', encoding='utf-8') as f:

                nodes = [line.strip() for line in f if line.strip()]

            input_source = 'collected_nodes.txt'

        else:

            logger.error(f'❌ 未找到输入文件！')

            return

        logger.info(f'📥 从 {input_source} 读取到 {len(nodes)} 个节点')

        # 1. 解析节点并按协议分类 (去重)

        parsed_nodes = []

        parsed_nodes_map = {}

        for url in tqdm(nodes, desc='解析节点'):

            info = self.parse_node(url) # 注意这里调用的是 self.parse_node

            if info:

                key = f"{info['protocol']}://{info['host']}:{info['port']}"

                if key not in parsed_nodes_map:

                    parsed_nodes_map[key] = info

                    parsed_nodes.append(info)

        logger.info(f'✅ 解析成功: {len(parsed_nodes)} 个节点')

        # 2. 协议过滤

        if self.preferred_protocols_only:

             parsed_nodes = [n for n in parsed_nodes if n['protocol'] in self.preferred_protocols]

             logger.info(f'🛡️ 仅保留首选协议, 剩余: {len(parsed_nodes)} 个')

        # CN probe data (optional)

        self._attach_cn_probe(parsed_nodes)

        # Risk/phishing filter (optional)

        if self.risk_filter_enabled:

            filtered_nodes = []

            for node in parsed_nodes:

                block, penalty, flags = self._apply_risk_filter(node)

                if block:

                    self.risk_filter_blocked += 1

                    continue

                if penalty > 0:

                    node['score'] -= penalty

                    node['risk_flags'] = flags

                    node['risk_penalty'] = penalty

                    self.risk_filter_penalized += 1

                filtered_nodes.append(node)

            parsed_nodes = filtered_nodes

            logger.info(f'🛡️ 风险过滤: 阻断={self.risk_filter_blocked}, 降分={self.risk_filter_penalized}, 剩余={len(parsed_nodes)}')

        # 随机打乱

        import random

        random.shuffle(parsed_nodes)

        # 动态盲选探测头（可选）

        self.select_dynamic_probe_head()

        # 准备保底参数

        min_guarantee = self.max_output_nodes if hasattr(self, 'max_output_nodes') else 50

        if hasattr(self, 'quality_filter_config'): # 尝试读取 config 中的 min_guarantee

             min_guarantee = self.quality_filter_config.get('min_guarantee', 50)

        # 或者重新读取一次(为了保险)

        try:

            with open(self.config_path, 'r', encoding='utf-8') as f:

                c = yaml.safe_load(f)

                min_guarantee = c.get('quality_filter', {}).get('min_guarantee', 50)

        except: pass

        max_test_once = self.max_test_nodes

        available_nodes = []

        total_tested = 0

        remaining_nodes = parsed_nodes

        batch_idx = 1

        # --- 循环测试流程 ---

        while True:

            if len(available_nodes) >= min_guarantee:

                logger.info(f'✅ 已满足保底数量 ({len(available_nodes)} >= {min_guarantee})，停止测试。')

                break

            if not remaining_nodes:

                logger.info(f'⚠️ 所有源节点已耗尽，停止测试。')

                break

            batch_size = max_test_once

            if len(available_nodes) > 0: batch_size = 2000 # 后续批次减小

            current_batch = remaining_nodes[:batch_size]

            remaining_nodes = remaining_nodes[batch_size:]

            logger.info(f'\n🔄 [批次 {batch_idx}] 开始测试 {len(current_batch)} 个节点 (当前可用: {len(available_nodes)}, 目标: {min_guarantee})...')

            # 测试连通性（异步高并发）

            batch_results = self._run_async(self._run_connectivity_batch(current_batch, batch_idx))

            available_nodes.extend(batch_results)

            total_tested += len(current_batch)

            logger.info(f'   -> 本批次新增可用: {len(batch_results)} 个')

            if total_tested >= 20000:

                 logger.warning('⚠️ 达到最大测试上限 (20000)，强制停止。')

                 break

            batch_idx += 1

        logger.info(f'\n✅ 最终可用节点: {len(available_nodes)} 个')

        # 计算得分

        for node in available_nodes: self.calculate_score(node)

        available_nodes.sort(key=self._sort_key, reverse=True)

        if len(available_nodes) > self.max_output_nodes:

            logger.info(f'✂️ 输出节点超过限制，截取 Top {self.max_output_nodes}')

            available_nodes = available_nodes[:self.max_output_nodes]

        # IP 风险检测 (包含区域检查)

        available_nodes = self.check_ip_risk(available_nodes)

        available_nodes.sort(key=self._sort_key, reverse=True)

        self._save_results(available_nodes, parsed_nodes, nodes)

        if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):

            try:

                from send_to_telegram import send_subscription_to_telegram

                logger.info('\n📤 准备发送订阅...')

                send_subscription_to_telegram(self.output_file, self.report_file)

            except Exception as e:

                logger.warning(f'⚠️ Telegram发送失败: {e}')

        logger.info('='*60 + '\n✨ 筛选完成！\n' + '='*60)

    def _save_results(self, available_nodes, parsed_nodes, original_nodes):

        """保存筛选结果"""

        # 保存高质量节点

        with open(self.output_file, 'w', encoding='utf-8') as f:

            for index, node in enumerate(available_nodes, 1):

                # 1. 生成标准化名称

                # 格式: 🇺🇸 US 🛡️0 ⚡98

                country_code = node.get('country', 'UNK')

                country_map = {

                    'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'HK': '🇭🇰', 'TW': '🇹🇼', 

                    'SG': '🇸🇬', 'GB': '🇬🇧', 'DE': '🇩🇪', 'CA': '🇨🇦', 'AU': '🇦🇺',

                    'FR': '🇫🇷', 'NL': '🇳🇱', 'IN': '🇮🇳', 'TH': '🇹🇭', 'MY': '🇲🇾',

                    'UNK': '🌐'

                }

                flag = country_map.get(country_code, '🌐')

                risk = node.get('risk_score', 'N/A')

                protocol = node.get('protocol', '').capitalize()

                # 新格式: 国家图标 国家 协议 编号排序

                new_name = f"{flag} {country_code} {protocol} {index}"

                if node.get('cn_ok'):

                    new_name += " [CN-OK]"

                original_url = node['url']

                final_link = original_url

                try:

                    # 2. 根据协议类型应用名称

                    if original_url.startswith('vmess://'):

                        # VMess: base64(json) -> 修改 ps -> base64

                        b64_str = original_url.replace('vmess://', '')

                        # 补齐 padding

                        missing_padding = len(b64_str) % 4

                        if missing_padding: b64_str += '=' * (4 - missing_padding)

                        try:

                            json_str = base64.b64decode(b64_str).decode('utf-8')

                            v_config = json.loads(json_str)

                            v_config['ps'] = new_name # 修改备注

                            # 重新打包

                            new_json = json.dumps(v_config, ensure_ascii=False)

                            new_b64 = base64.b64encode(new_json.encode('utf-8')).decode('utf-8')

                            final_link = 'vmess://' + new_b64

                        except:

                            # 如果解析失败，回退到追加 hash (虽然 VMess 标准不支持，但部分客户端支持)

                            if '#' in final_link: final_link = final_link.split('#')[0]

                            final_link += f"#{urllib.parse.quote(new_name)}"

                    else:

                        # VLESS, Trojan, SS, Hysteria2: 修改 URL Fragment (#)

                        if '#' in final_link:

                            final_link = final_link.split('#')[0]

                        final_link += f"#{urllib.parse.quote(new_name)}"

                except Exception as e:

                    logger.warning(f"重命名失败: {e}")

                    pass

                f.write(final_link + '\n')

        logger.info(f'💾 已保存 {len(available_nodes)} 个高质量节点到: {self.output_file}')

        # 生成详细报告

        report = {

            'summary': {

                'total_input': len(original_nodes),

                'after_dedup': len(set(original_nodes)),

                'parsed_success': len(parsed_nodes),

                'available_nodes': len(available_nodes),

                'availability_rate': f'{len(available_nodes)/len(parsed_nodes)*100:.2f}%' if parsed_nodes else '0%'

            },

            'protocol_distribution': {},

            'latency_distribution': {

                '<100ms': 0,

                '100-200ms': 0,

                '200-300ms': 0,

                '300-500ms': 0

            },

            'top_10_nodes': []

        }

        if self.cn_probe_enabled:

            report['cn_probe'] = {

                'enabled': True,

                'matched': self.cn_probe_matched,

                'total_results': len(self.cn_probe_results)

            }

            report['cn_latency_distribution'] = {

                '<100ms': 0,

                '100-200ms': 0,

                '200-300ms': 0,

                '300-500ms': 0,

                '>500ms': 0

            }

        if self.risk_filter_enabled:

            report['risk_filter'] = {

                'enabled': True,

                'mode': self.risk_filter_mode,

                'blocked': self.risk_filter_blocked,

                'penalized': self.risk_filter_penalized

            }

        if self.asn_filter_enabled:

            report['asn_filter'] = {

                'enabled': True,

                'mode': self.asn_filter_mode,

                'blocked': self.asn_filter_blocked,

                'penalized': self.asn_filter_penalized

            }

        # 协议分布

        for node in available_nodes:

            protocol = node['protocol']

            report['protocol_distribution'][protocol] = report['protocol_distribution'].get(protocol, 0) + 1

        # 延迟分布

        for node in available_nodes:

            latency = node.get('latency', 0)

            if latency < 100:

                report['latency_distribution']['<100ms'] += 1

            elif latency < 200:

                report['latency_distribution']['100-200ms'] += 1

            elif latency < 300:

                report['latency_distribution']['200-300ms'] += 1

            else:

                report['latency_distribution']['300-500ms'] += 1

        # CN 延迟分布（可选）

        if 'cn_latency_distribution' in report:

            for node in available_nodes:

                cn_latency = node.get('cn_latency')

                if cn_latency is None:

                    continue

                if cn_latency < 100:

                    report['cn_latency_distribution']['<100ms'] += 1

                elif cn_latency < 200:

                    report['cn_latency_distribution']['100-200ms'] += 1

                elif cn_latency < 300:

                    report['cn_latency_distribution']['200-300ms'] += 1

                elif cn_latency < 500:

                    report['cn_latency_distribution']['300-500ms'] += 1

                else:

                    report['cn_latency_distribution']['>500ms'] += 1

        # Top 10

        for i, node in enumerate(available_nodes[:10]):

            node_data = {

                'rank': i + 1,

                'protocol': node['protocol'],

                'host': node['host'],

                'port': node['port'],

                'latency': f"{node.get('latency', 0)}ms",

                'score': node['final_score']

            }

            if 'risk_score' in node:

                node_data['risk_score'] = node['risk_score']

                node_data['country'] = node.get('country', '')

            if 'cn_latency' in node:

                node_data['cn_latency'] = f"{node.get('cn_latency', 0)}ms"

            if 'cn_score' in node:

                node_data['cn_score'] = node.get('cn_score')

            if 'risk_flags' in node:

                node_data['risk_flags'] = node.get('risk_flags', [])

            if 'risk_penalty' in node:

                node_data['risk_penalty'] = node.get('risk_penalty', 0)

            if 'asn_flags' in node:

                node_data['asn_flags'] = node.get('asn_flags', [])

            if 'asn_penalty' in node:

                node_data['asn_penalty'] = node.get('asn_penalty', 0)

            report['top_10_nodes'].append(node_data)

        # 保存报告

        with open(self.report_file, 'w', encoding='utf-8') as f:

            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f'📊 已生成质量报告: {self.report_file}')

        # 打印报告摘要

        logger.info('\n📈 筛选报告摘要:')

        logger.info(f'   - 输入节点: {report["summary"]["total_input"]} 个')

        logger.info(f'   - 去重后: {report["summary"]["after_dedup"]} 个')

        logger.info(f'   - 解析成功: {report["summary"]["parsed_success"]} 个')

        logger.info(f'   - 高质量节点: {report["summary"]["available_nodes"]} 个')

        logger.info(f'   - 可用率: {report["summary"]["availability_rate"]}')

        logger.info('\n⚡ 延迟分布:')

        for range_name, count in report['latency_distribution'].items():

            logger.info(f'   - {range_name}: {count} 个')

        if 'cn_latency_distribution' in report:

            logger.info('\n🇨🇳 CN 延迟分布:')

            for range_name, count in report['cn_latency_distribution'].items():

                logger.info(f'   - {range_name}: {count} 个')

        if self.risk_filter_enabled:

            logger.info('\n🛡️ 风险过滤统计:')

            logger.info(f'   - 阻断: {self.risk_filter_blocked} 个')

            logger.info(f'   - 降分: {self.risk_filter_penalized} 个')

        if self.asn_filter_enabled:

            logger.info('\n🧭 ASN/ORG/ISP 过滤统计:')

            logger.info(f'   - 阻断: {self.asn_filter_blocked} 个')

            logger.info(f'   - 降分: {self.asn_filter_penalized} 个')

        if report['top_10_nodes']:

            logger.info('\n🏆 Top 10 节点 (详细信息已通过Telegram发送):')

            for node in report['top_10_nodes'][:5]:  # 只显示前5个

                # 对IP进行脱敏处理，防止GitHub Action日志泄露

                safe_host = node['host'][:3] + '***' + node['host'][-3:] if len(node['host']) > 6 else '***'

                risk_info = f" | 🛡️风险值: {node.get('risk_score', 'N/A')}" if 'risk_score' in node else ""

                country_info = f" | 🌍地区: {node.get('country', 'N/A')}" if 'country' in node else ""

                cn_info = f" | 🇨🇳CN延迟: {node.get('cn_latency', 'N/A')}" if 'cn_latency' in node else ""

                logger.info(f"   {node['rank']}. {node['protocol']}://{safe_host}:**** - {node['latency']} (分数: {node['score']}){risk_info}{country_info}{cn_info}")

    def check_ip_risk(self, nodes):

        """

        检测IP风险值

        支持:

        1. abuseipdb (需要API Key，精准)

        2. ipapi (免Key，通过ISP类型判断风险)

        """

        if not self.ip_risk_config.get('enabled', False):

            return nodes

        provider = self.ip_risk_config.get('provider', 'abuseipdb')

        max_check = self.ip_risk_config.get('check_top_nodes', 50)

        # AbuseIPDB 检查

        if provider == 'abuseipdb':

            api_key = self.ip_risk_config.get('api_key') or os.getenv('ABUSEIPDB_API_KEY')

            if not api_key:

                logger.warning('⚠️ AbuseIPDB 需要 API Key，已切换到 ipapi (免Key模式)')

                provider = 'ipapi'

        # 只取前N个进行检测

        target_nodes = nodes[:max_check]

        unchecked_nodes = nodes[max_check:]

        logger.info(f'\n🛡️ 开始IP风险检测 ({provider}, Top {len(target_nodes)})...')

        checked_nodes = []

        for node in tqdm(target_nodes, desc='风险检测'):

            try:

                # 获取IP

                host = node['host']

                ip = None

                # 如果是域名，解析为IP

                if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host):

                    try:

                        ip = socket.gethostbyname(host)

                    except:

                        pass

                else:

                    ip = host

                if ip:

                    # 1. AbuseIPDB 模式

                    if provider == 'abuseipdb':

                        self._check_abuseipdb(node, ip, api_key)

                    # 2. IP-API 免Key模式

                    elif provider == 'ipapi':

                        self._check_ipapi(node, ip)

                # ASN/ORG/ISP 过滤（仅 ipapi）

                if node.get('blocked_by_asn'):

                    time.sleep(1.5 if provider == 'ipapi' else 0.5)

                    continue

                # 3. 区域限制检查

                region_config = getattr(self, 'region_config', {})

                if region_config.get('enabled') and node.get('country'):

                    country = node['country']

                    allowed = region_config.get('allowed_countries', [])

                    blocked = region_config.get('blocked_countries', [])

                    policy = region_config.get('policy', 'filter')

                    is_allowed = True

                    # 如果有白名单，必须在白名单内

                    if allowed and country not in allowed:

                        is_allowed = False

                    # 如果有黑名单，不能在黑名单内

                    elif blocked and country in blocked:

                        is_allowed = False

                    if not is_allowed:

                        if policy == 'filter':

                            logger.info(f"   - ❌ 地区不符 ({country}): {node['host']}")

                            # 跳过添加，直接进入下一个循环

                            # 避免触发速率限制

                            time.sleep(1.5 if provider == 'ipapi' else 0.5)

                            continue 

                        else:

                            node['score'] -= 50 # 扣大分

                            logger.info(f"   - ⚠️ 地区不符 ({country}): 扣50分")

                checked_nodes.append(node)

                # 避免触发速率限制

                time.sleep(1.5 if provider == 'ipapi' else 0.5) # IP-API 限制45次/分

            except Exception as e:

                logger.debug(f"Risk check failed: {e}")

                checked_nodes.append(node)

        # 重新排序

        all_nodes = checked_nodes + unchecked_nodes

        all_nodes.sort(key=self._sort_key, reverse=True)

        return all_nodes

    def _check_abuseipdb(self, node, ip, api_key):

        """AbuseIPDB 检测逻辑"""

        try:

            headers = {'Key': api_key, 'Accept': 'application/json'}

            params = {'ipAddress': ip, 'maxAgeInDays': 90}

            response = requests.get('https://api.abuseipdb.com/api/v2/check', headers=headers, params=params, timeout=5)

            if response.status_code == 200:

                data = response.json()['data']

                score = data['abuseConfidenceScore']

                node['risk_score'] = score

                node['country'] = data.get('countryCode', 'Unknown')

                # 区域检查

                if not self.check_region_restriction(node):

                    node['final_score'] -= 20

                max_risk = self.ip_risk_config.get('max_risk_score', 50)

                if score == 0: node['final_score'] += 3

                elif score < 20: node['final_score'] += 1

                elif score > max_risk: node['final_score'] -= 10

        except:

            pass

    def check_region_restriction(self, node):

        """

        检查节点地区是否支持特定服务

        基于 IP-API 获取的 countryCode

        """

        if not node.get('country'):

            return True

        country = node['country']

        # 必须排除的国家 (CN=中国, RU=俄罗斯, IR=伊朗, KP=朝鲜)

        # 这些地区通常被主流服务屏蔽或被墙

        blocked_countries = ['CN', 'RU', 'IR', 'KP']

        if country in blocked_countries:

            return False

        # ChatGPT/Gemini 特别限制 (香港通常无法使用 ChatGPT)

        # 如果你需要 ChatGPT，最好过滤掉 HK

        # 这里默认保留 HK，因为很多机场的 HK 节点有解锁

        # blocked_for_ai = ['HK', 'MO'] 

        # if country in blocked_for_ai:

        #     node['final_score'] -= 3 # 对 AI 限制地区扣分而不是直接过滤

        return True

    def _check_ipapi(self, node, ip):

        """

        使用 ip-api.com 检测 (免Key)

        检测项目: Hosting(机房), Proxy(代理), Mobile(移动)

        改进：评分模式，不直接淘汰节点，只影响评分

        """

        try:

            # 请求字段: status, message, countryCode, country, isp, org, as, mobile, proxy, hosting

            url = f'http://ip-api.com/json/{ip}?fields=status,message,countryCode,country,isp,org,as,mobile,proxy,hosting'

            response = requests.get(url, timeout=5)

            if response.status_code == 200:

                data = response.json()

                if data.get('status') == 'fail':

                    return

                # 获取详细信息

                country = data.get('countryCode', 'UNK')

                isp = data.get('isp', 'Unknown')

                org = data.get('org', 'Unknown')

                as_text = data.get('as', '')

                is_mobile = data.get('mobile', False)

                is_proxy = data.get('proxy', False)

                is_hosting = data.get('hosting', False)

                node['country'] = country

                node['isp'] = isp

                node['org'] = org

                node['as'] = as_text

                # 风险判断逻辑 - 评分模式

                behavior = self.ip_risk_config.get('ipapi_behavior', {})

                exclude_hosting = behavior.get('exclude_hosting', True)

                exclude_proxy = behavior.get('exclude_proxy', False)

                exclude_mobile = behavior.get('exclude_mobile', False)

                # 计算风险评分

                risk_score = 0

                risk_factors = []

                if is_hosting and exclude_hosting:

                    risk_factors.append('Hosting')

                    risk_score = 50  # 机房IP风险值50

                    node['final_score'] -= 5  # 降5分，而不是归零

                if is_proxy and exclude_proxy:

                    risk_factors.append('Proxy')

                    risk_score = max(risk_score, 60)  # 代理IP风险值60

                    node['final_score'] -= 3

                if is_mobile and exclude_mobile:

                    risk_factors.append('Mobile')

                    risk_score = max(risk_score, 30)

                    node['final_score'] -= 2

                if risk_factors:

                    node['risk_score'] = risk_score

                    logger.info(f"   - ⚠️ 风险IP ({', '.join(risk_factors)}): {ip} ({isp}) | 风险值={risk_score} 降分")

                else:

                    # 纯净家庭宽带IP - 最佳质量

                    node['risk_score'] = 0

                    node['final_score'] += 10

                    logger.info(f"   - ✅ 纯净IP: {ip} ({country} - {isp}) | 风险值=0 加分")

                # ASN/ORG/ISP 黑名单（ipapi）

                block_asn, penalty_asn, flags_asn = self._apply_asn_filter(node, data)

                if flags_asn:

                    node['asn_flags'] = flags_asn

                if block_asn:

                    node['blocked_by_asn'] = True

                    self.asn_filter_blocked += 1

                    logger.info(f"   - ❌ ASN/ORG/ISP 命中黑名单: {ip} ({as_text or isp})")

                elif penalty_asn > 0:

                    node['final_score'] -= penalty_asn

                    node['asn_penalty'] = penalty_asn

                    self.asn_filter_penalized += 1

        except Exception as e:

            logger.warning(f"IP-API 检测异常: {e}")

def main():

    """Main entry."""

    logger.remove()

    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    parser = argparse.ArgumentParser(description='SmartSub node quality filter')

    parser.add_argument('--probe-only', action='store_true', help='Only select dynamic probe head and exit')

    args = parser.parse_args()

    filter_tool = NodeQualityFilter()

    if args.probe_only:

        if not filter_tool.dynamic_probe_enabled:

            logger.warning('Dynamic probe is disabled, skip probe-only mode')

            return

        filter_tool.select_dynamic_probe_head()

        return

    filter_tool.process_nodes()

if __name__ == '__main__':

    main()
