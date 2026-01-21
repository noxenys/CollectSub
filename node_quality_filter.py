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
import requests
import yaml
import random
import concurrent.futures
import urllib.parse
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
            'hysteria': 9,
            'vless': 8,
            'trojan': 7,
            'vmess': 6,
            'ss': 5,
            'ssr': 4
        }
        
        # 首选协议列表
        self.preferred_protocols = ['hysteria2', 'vless', 'trojan', 'vmess', 'ss']
        
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
        except Exception as e:
            logger.warning(f'加载配置失败，使用默认配置: {e}')
    
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
            elif protocol in ['ss', 'ssr']:
                node_info.update(self._parse_ss(node_url))
            elif protocol in ['trojan', 'vless']:
                node_info.update(self._parse_trojan_vless(node_url))
            elif protocol in ['hysteria', 'hysteria2']:
                node_info.update(self._parse_hysteria(node_url))
            
            return node_info if node_info['host'] and node_info['port'] else None
            
        except Exception as e:
            logger.debug(f'节点解析失败: {node_url[:50]}... - {e}')
            return None
    
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
            
            return {
                'host': config.get('add', ''),
                'port': int(config.get('port', 0)) if config.get('port') else None
            }
        except:
            return {'host': None, 'port': None}
    
    def _parse_ss(self, url):
        """解析 ss/ssr 节点"""
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
            # trojan://password@host:port 或 vless://uuid@host:port
            match = re.search(r'://[^@]+@([^:/?#]+):?(\d+)?', url)
            if match:
                host = match.group(1)
                port = int(match.group(2)) if match.group(2) else 443
                return {'host': host, 'port': port}
        except:
            pass
        
        return {'host': None, 'port': None}
    
    def _parse_hysteria(self, url):
        """解析 hysteria/hysteria2 节点"""
        try:
            # hysteria://host:port 或 hysteria2://password@host:port
            if '@' in url:
                match = re.search(r'@([^:/?#]+):?(\d+)?', url)
            else:
                match = re.search(r'://([^:/?#]+):?(\d+)?', url)
            
            if match:
                host = match.group(1)
                port = int(match.group(2)) if match.group(2) else 443
                return {'host': host, 'port': port}
        except:
            pass
        
        return {'host': None, 'port': None}
    
    def test_connectivity(self, node_info):
        """测试节点连通性和延迟"""
        if not node_info or not node_info['host'] or not node_info['port']:
            return None
        
        host = node_info['host']
        port = node_info['port']
        
        try:
            # 解析域名到IP
            start_time = time.time()
            ip = socket.gethostbyname(host)
            dns_time = (time.time() - start_time) * 1000
            
            # 测试TCP连接
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connect_timeout)
            
            result = sock.connect_ex((ip, port))
            connect_time = (time.time() - start_time) * 1000
            sock.close()
            
            if result == 0:
                total_latency = dns_time + connect_time
                node_info['latency'] = round(total_latency, 2)
                node_info['status'] = 'online'
                return node_info
            else:
                node_info['status'] = 'offline'
                return None
                
        except socket.timeout:
            node_info['status'] = 'timeout'
            return None
        except socket.gaierror:
            node_info['status'] = 'dns_error'
            return None
        except Exception as e:
            node_info['status'] = f'error: {type(e).__name__}'
            return None
    
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
             
        # 随机打乱
        import random
        random.shuffle(parsed_nodes)
        
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
            
            # 测试连通性
            batch_results = []
            test_bar = tqdm(total=len(current_batch), desc=f'批次 {batch_idx} 测试')
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.test_connectivity, node) for node in current_batch]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result and result.get('latency', float('inf')) <= self.max_latency:
                        batch_results.append(result)
                    test_bar.update(1)
            test_bar.close()
            
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
        
        available_nodes.sort(key=lambda x: (x['final_score'], -x.get('latency', 999)), reverse=True)
        
        if len(available_nodes) > self.max_output_nodes:
            logger.info(f'✂️ 输出节点超过限制，截取 Top {self.max_output_nodes}')
            available_nodes = available_nodes[:self.max_output_nodes]
            
        # IP 风险检测 (包含区域检查)
        available_nodes = self.check_ip_risk(available_nodes)
        
        available_nodes.sort(key=lambda x: (x['final_score'], -x.get('latency', 999)), reverse=True)
         
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
            for node in available_nodes:
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
                
                # 方案B格式: 🇺🇸 US | Vless | 🛡️0
                new_name = f"{flag} {country_code} | {protocol} | 🛡️{risk}"
                
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
                        # VLESS, Trojan, SS, Hysteria: 修改 URL Fragment (#)
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
        
        if report['top_10_nodes']:
            logger.info('\n🏆 Top 10 节点 (详细信息已通过Telegram发送):')
            for node in report['top_10_nodes'][:5]:  # 只显示前5个
                # 对IP进行脱敏处理，防止GitHub Action日志泄露
                safe_host = node['host'][:3] + '***' + node['host'][-3:] if len(node['host']) > 6 else '***'
                risk_info = f" | 🛡️风险值: {node.get('risk_score', 'N/A')}" if 'risk_score' in node else ""
                country_info = f" | 🌍地区: {node.get('country', 'N/A')}" if 'country' in node else ""
                
                logger.info(f"   {node['rank']}. {node['protocol']}://{safe_host}:**** - {node['latency']} (分数: {node['score']}){risk_info}{country_info}")

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
        all_nodes.sort(key=lambda x: (x['final_score'], -x.get('latency', 999)), reverse=True)
        
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
                is_mobile = data.get('mobile', False)
                is_proxy = data.get('proxy', False)
                is_hosting = data.get('hosting', False)
                
                node['country'] = country
                node['isp'] = isp
                
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
                    
        except Exception as e:
            logger.warning(f"IP-API 检测异常: {e}")



def main():
    """主函数"""
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    filter_tool = NodeQualityFilter()
    filter_tool.process_nodes()


if __name__ == '__main__':
    main()
