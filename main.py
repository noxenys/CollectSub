import re
import os
import yaml
import threading
import base64
import requests
import concurrent.futures
import datetime
import time
import random

from loguru import logger
from tqdm import tqdm
from retry import retry
from urllib.parse import quote, urlencode, urlparse
from pre_check import pre_check, get_sub_all

class SubscriptionCollector:
    def __init__(self):
        # 1. 初始化路径 (使用绝对路径)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # 切换工作目录到脚本所在目录，确保 pre_check 等外部模块能正确创建目录
        os.chdir(self.base_dir)
        
        self.config_path = os.path.join(self.base_dir, 'config.yaml')
        self.blacklist_path = os.path.join(self.base_dir, 'blacklist.txt')
        self.collected_nodes_path = os.path.join(self.base_dir, 'collected_nodes.txt')
        self.failed_log_path = os.path.join(self.base_dir, 'failed_subscriptions.log')
        
        # 2. 初始化数据容器
        self.new_sub_list = []
        self.new_clash_list = []
        self.new_v2_list = []
        self.play_list = []
        self.airport_list = []
        self.collected_nodes_set = set()
        self.failed_sub_list = []
        
        # 3. 质量控制与统计
        self.quality_stats = {
            'total_checked': 0,
            'low_quality': 0,
            'empty_subscription': 0,
            'spam_content': 0
        }
        self.lock = threading.Lock()
        
        # 4. 正则表达式
        self.re_str = r"https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"
        self.node_str = r'(?:vmess|ss|ssr|trojan|vless|hysteria|hysteria2)://[a-zA-Z0-9+/=@#?&._-]+'
        self.check_node_url_str = "https://{}/sub?target={}&url={}&insert=false&config=config%2FACL4SSR.ini"
        
        # 5. 配置参数 (默认值)
        self.max_workers = 32
        self.content_limit_mb = 3
        self.request_timeout = 15
        self.min_nodes = 3
        self.enable_quality_check = True
        self.check_url_list = []
        
        # 6. User-Agent 列表 (抗封锁 - 扩展池)
        self.user_agents = [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Edg/124.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        ]

        # 7. 静态资源后缀 (用于过滤无效链接)
        self.static_extensions = (
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.ico', '.svg', 
            '.css', '.js', '.woff', '.woff2', '.ttf', '.eot', '.otf',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.dmg', '.exe', '.apk'
        )
        
        # 8. 代理配置 (支持 GitHub Actions 等环境)
        self.proxies = self._get_system_proxies()
        
        self.list_tg = []
        self.list_subscribe = []
        self.list_web_fuzz = []
        
        # 加载配置
        self.load_config()

    def get_abs_path(self, relative_path):
        """将相对路径转换为基于脚本目录的绝对路径"""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.base_dir, relative_path)

    @logger.catch
    def load_config(self):
        if not os.path.exists(self.config_path):
            logger.error(f"Config file not found: {self.config_path}")
            return

        with open(self.config_path, encoding="UTF-8") as f:
            data = yaml.safe_load(f)
        
        # 读取性能配置
        performance = data.get('performance', {})
        self.max_workers = performance.get('max_workers', 32)
        self.content_limit_mb = performance.get('content_limit_mb', 3)
        self.request_timeout = performance.get('request_timeout', 15)
        
        # 读取质量控制配置
        quality = data.get('quality_control', {})
        self.min_nodes = quality.get('min_nodes', 3)
        self.enable_quality_check = quality.get('enable_quality_check', True)
        
        # 节点级去重池
        self.unique_nodes = set()
        
        logger.info(f'性能配置: 线程数={self.max_workers}, 限制={self.content_limit_mb}MB, 超时={self.request_timeout}s')
        logger.info(f'质量控制: 最少节点={self.min_nodes}, 质检={self.enable_quality_check}')
        
        # 获取 Telegram 频道
        list_tg_raw = data.get('tgchannel', [])
        self.list_tg = []
        for url in list_tg_raw:
            url = str(url).strip()
            if not url:
                continue
                
            # 使用正则智能提取频道 ID
            # 匹配: t.me/channel, t.me/s/channel, telegram.me/channel
            # 能够处理末尾斜杠、参数等情况
            match = re.search(r'(?:t\.me|telegram\.me)/(?:s/)?([a-zA-Z0-9_]+)', url, re.IGNORECASE)
            
            if match:
                channel_id = match.group(1)
                # 排除一些非频道的系统路径
                if channel_id.lower() not in ['s', 'share', 'joinchat', 'addstickers', 'iv']:
                    self.list_tg.append(f'https://t.me/s/{channel_id}')
            elif '/' not in url and '@' not in url:
                # 支持纯频道名: channel_name
                self.list_tg.append(f'https://t.me/s/{url}')
            elif url.startswith('@'):
                # 支持 @channel_name
                self.list_tg.append(f'https://t.me/s/{url[1:]}')
            else:
                logger.warning(f'忽略无法解析的 Telegram 链接: {url}')
        
        self.list_subscribe = data.get('subscribe', [])
        self.list_web_fuzz = data.get('web_pages', [])

        # 获取订阅转换 API
        # 优先读取 subconverter_backends，兼容旧配置 sub_convert_apis
        config_apis = data.get('subconverter_backends') or data.get('sub_convert_apis', [])
        if config_apis:
            self.check_url_list = config_apis
            logger.info(f'已加载 {len(self.check_url_list)} 个订阅转换 API')
        else:
            logger.warning('未配置 subconverter_backends，将使用默认 API')
            # 提供一组内置的默认 API 防止程序出错
            self.check_url_list = ['api.dler.io','sub.xeton.dev','sub.id9.cc','sub.maoxiongnet.com']

    @logger.catch
    def load_sub_yaml(self, path_yaml):
        abs_path = self.get_abs_path(path_yaml)
        if os.path.isfile(abs_path):
            with open(abs_path, encoding="UTF-8") as f:
                dict_url = yaml.safe_load(f)
        else:
            dict_url = {
                "机场订阅": [],
                "clash订阅": [],
                "v2订阅": [],
                "开心玩耍": []
            }
        logger.info(f'读取文件成功: {abs_path}')
        return dict_url

    def get_random_ua(self):
        """随机获取 User-Agent"""
        return random.choice(self.user_agents)

    def mask_url(self, url):
        """对 URL 进行脱敏处理，隐藏敏感参数"""
        if not url: return ""
        # 常见敏感参数
        sensitive_keys = ['token', 'key', 'uuid', 'access_token', 'secret', 'auth']
        try:
            masked_url = url
            for key in sensitive_keys:
                # 匹配 ?key=value 或 &key=value
                pattern = f'([?&]{key}=)([^&]+)'
                masked_url = re.sub(pattern, r'\1******', masked_url, flags=re.IGNORECASE)
            return masked_url
        except Exception:
            return "******"

    def check_ssrf(self, url):
        """简单的 SSRF 防御检测"""
        if not url: return False
        try:
            url_lower = url.lower()
            # 简单判断是否以 localhost 或 127.0.0.1 开头
            if url_lower.startswith(('http://localhost', 'https://localhost', 
                                   'http://127.0.0.1', 'https://127.0.0.1')):
                logger.warning(f'拦截潜在的 SSRF 请求: {self.mask_url(url)}')
                return False
            return True
        except Exception:
            return False

    def _get_system_proxies(self):
        """从环境变量获取代理设置"""
        proxies = {}
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
            
        if proxies:
            logger.info(f'已检测到系统代理设置: {proxies}')
        return proxies if proxies else None

    @logger.catch
    def fetch_urls_from_page(self, url):
        """通用网页抓取函数 (增强抗封锁)"""
        if not self.check_ssrf(url):
            return []

        # 针对 Telegram 频道的优化：不重试，快速跳过
        is_tg_channel = 't.me/s/' in url
        # TG 频道: 1 次尝试 (0 次重试)
        # 普通链接: 2 次尝试 (1 次重试) - 从 3 改为 2，提高效率
        max_attempts = 1 if is_tg_channel else 2

        url_list = []
        node_list = []
        data = None
        
        # 重试机制
        for attempt in range(max_attempts):
            try:
                headers = {
                    'User-Agent': self.get_random_ua()
                }
                
                # 发起请求 (启用 stream 模式防止内存溢出)
                resp = requests.get(url, headers=headers, timeout=self.request_timeout, proxies=self.proxies, stream=True)
                
                # 针对 403/429 的特殊重试逻辑
                if resp.status_code in [403, 429]:
                    resp.close()
                    if attempt < max_attempts - 1:
                        wait_time = random.uniform(1, 3)
                        msg = f'{self.mask_url(url)}\t遇到 {resp.status_code}'
                        if resp.status_code == 403:
                            msg += ' (可能 IP 被屏蔽)'
                        logger.warning(f'{msg}，等待 {wait_time:.1f}s 后更换 UA 重试...')
                        time.sleep(wait_time)
                        continue
                    else:
                        # TG 频道遇到限制直接跳过，不输出警告，减少日志噪音
                        if not is_tg_channel:
                            logger.warning(f'{self.mask_url(url)}\t遇到 {resp.status_code}，重试次数耗尽')
                        return []
                
                # 针对 404 的快速失败逻辑
                if resp.status_code == 404:
                    resp.close()
                    logger.warning(f'{self.mask_url(url)}\t资源不存在 (404)，跳过')
                    return []
                    
                # 针对 500/502/503/504 的服务器错误重试逻辑
                if resp.status_code >= 500:
                    resp.close()
                    if attempt < max_attempts - 1:
                        wait_time = random.uniform(2, 5) # 服务器错误多等一会儿
                        logger.warning(f'{self.mask_url(url)}\t服务器错误 {resp.status_code}，等待 {wait_time:.1f}s 后重试...')
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f'{self.mask_url(url)}\t服务器错误 {resp.status_code}，重试次数耗尽')
                        return []
                
                # 正常响应处理
                content_limit = self.content_limit_mb * 1024 * 1024
                content = b""
                download_failed = False
                
                try:
                    for chunk in resp.iter_content(chunk_size=8192):
                        content += chunk
                        if len(content) > content_limit:
                            logger.warning(f'{self.mask_url(url)}\t超过大小限制({self.content_limit_mb}MB)，截断下载')
                            # download_failed = True  <-- 不需要标记为失败，直接使用截断后的内容尝试提取
                            break
                except Exception as e:
                     logger.warning(f'{self.mask_url(url)}\t下载中断: {e}')
                     download_failed = True

                resp.close()
                
                if download_failed and attempt < max_attempts - 1:
                    continue

                # 尝试解码
                data = content.decode('utf-8', errors='ignore')
                break # 成功获取，跳出循环
                
            except requests.RequestException as e:
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
                else:
                    if not is_tg_channel:
                         logger.warning(f'{self.mask_url(url)}\t网络请求失败: {type(e).__name__}')
                    return []
            except Exception as e:
                logger.error(f'{self.mask_url(url)}\t处理失败: {type(e).__name__} - {str(e)}')
                return []
        
        if not data:
            return []

        try:
            # 1. 提取订阅 URL
            all_url_list = re.findall(self.re_str, data)
            
            filter_string_list = ["//t.me/", "cdn-telegram.org", "w3.org", "google.com", "github.com/site", "github.com/features", "cdn5.telesco.pe"]
            url_list = [item for item in all_url_list if not any(filter_string in item for filter_string in filter_string_list)]
            
            # 过滤静态资源
            url_list = [item for item in url_list if not item.lower().endswith(self.static_extensions)]
            
            url_list = list(set(url_list))

            # 过滤敏感链接
            url_list = [u for u in url_list if self.is_safe_url(u)]

            # 2. 提取直接节点
            direct_nodes = re.findall(self.node_str, data)
            if direct_nodes:
                node_list.extend(direct_nodes)
                logger.info(f'{self.mask_url(url)}\t发现 {len(direct_nodes)} 个直接节点')

            if node_list:
                self.collected_nodes_set.update(node_list)

            # 3. 质量控制
            if len(url_list) == 0 and len(node_list) == 0:
                logger.warning(f'{self.mask_url(url)}\t无有效内容')
                return []
            
            if len(url_list) + len(node_list) < 2:
                logger.warning(f'{self.mask_url(url)}\t内容过少({len(url_list) + len(node_list)} < 2)，已跳过')
                return []
            
            logger.info(f'{self.mask_url(url)}\t获取成功\t订阅链接:{len(url_list)} 节点链接:{len(node_list)}')
        except Exception as e:
            logger.error(f'{self.mask_url(url)}\t数据解析失败: {type(e).__name__} - {str(e)}')
        
        return url_list

    def is_safe_url(self, url):
        if not url: return False
        url_lower = url.lower()
        sensitive_patterns = [
            'glpat-', 'ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_', 
            'private-token', 'access_token=', 'secret='
        ]
        for pattern in sensitive_patterns:
            if pattern in url_lower:
                logger.warning(f'发现敏感链接并已过滤: {self.mask_url(url)[:30]}... (包含 {pattern})')
                return False
        return True

    def filter_base64(self, text):
        ss = ['ss://', 'vmess://', 'trojan://', 'vless://', 'hysteria2://']
        for i in ss:
            if i in text:
                return True
        return False

    def extract_nodes(self, content):
        """从内容中提取节点链接"""
        nodes = []
        try:
            # 尝试解析 Base64
            decoded_text = ""
            try:
                # 简单的 Base64 探测
                sample_length = min(256, len(content))
                head_text = content[:sample_length].strip()
                if not '://' in head_text and not 'proxies:' in head_text: # 只有不包含协议头才尝试解码
                    missing_padding = len(content) % 4
                    if missing_padding:
                        content += '=' * (4 - missing_padding)
                    decoded_text = base64.b64decode(content).decode('utf-8', errors='ignore')
            except Exception:
                pass

            # 从原始内容提取
            nodes.extend(re.findall(self.node_str, content))
            
            # 从解码内容提取
            if decoded_text:
                nodes.extend(re.findall(self.node_str, decoded_text))
                
        except Exception:
            pass
        
        return list(set(nodes)) # 局部去重

    def count_nodes_in_content(self, content, is_clash=False):
        try:
            if is_clash:
                data = yaml.safe_load(content)
                proxies = data.get('proxies', [])
                return len(proxies)
            else:
                try:
                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                    nodes = [line for line in decoded.split('\n') if line.strip() and '://' in line]
                    return len(nodes)
                except Exception:
                    return 0
        except Exception:
            return 0

    def validate_subscription_quality(self, url, content, is_clash=False):
        if not self.enable_quality_check:
            return True
        
        node_count = self.count_nodes_in_content(content, is_clash)
        
        if node_count == 0:
            logger.warning(f'{self.mask_url(url)}\t空订阅（0个节点）- 已跳过')
            with self.lock:
                self.quality_stats['empty_subscription'] += 1
            return False
        
        if node_count < self.min_nodes:
            logger.warning(f'{self.mask_url(url)}\t节点过少（{node_count} < {self.min_nodes}）- 已跳过')
            with self.lock:
                self.quality_stats['low_quality'] += 1
            return False
        
        spam_keywords = ['已过期', '请购买', '试用结束', '联系客服', '已到期']
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in spam_keywords):
            logger.warning(f'{self.mask_url(url)}\t检测到垃圾内容 - 已跳过')
            with self.lock:
                self.quality_stats['spam_content'] += 1
            return False
        
        logger.info(f'{self.mask_url(url)}\t质量验证通过（{node_count} 个节点）')
        return True

    @logger.catch
    def sub_check(self, url, bar):
        if not self.check_ssrf(url):
            bar.update(1)
            return

        # 快速过滤静态资源后缀 (二次保险)
        if url.lower().endswith(self.static_extensions):
            bar.update(1)
            return

        # 3次重试机制 (替代 @retry)
        for attempt in range(2):
            try:
                headers = {'User-Agent': self.get_random_ua()}
                
                res = requests.get(url, headers=headers, timeout=self.request_timeout, stream=True, proxies=self.proxies)
                
                # 针对 403/429 的特殊重试逻辑
                if res.status_code in [403, 429]:
                    res.close()
                    if attempt < 1:
                        wait_time = random.uniform(1, 3)
                        msg = f'{self.mask_url(url)}\t检测遇到 {res.status_code}'
                        if res.status_code == 403:
                            msg += ' (可能 IP 被屏蔽)'
                        logger.warning(f'{msg}，等待 {wait_time:.1f}s 后更换 UA 重试...')
                        time.sleep(wait_time)
                        continue
                    else:
                        self.failed_sub_list.append(url)
                        logger.warning(f'{self.mask_url(url)}\t状态码异常: {res.status_code} (重试耗尽)')
                        break
                
                if res.status_code == 200:
                    header_info_valid = False
                    header_play_info = ""

                    # Header Check
                    # 注意：获取到流量信息后不应直接返回，必须继续执行 Body 下载和节点提取，
                    # 这样才能确保该订阅中的节点被解析并加入去重池。
                    try: 
                        info = res.headers.get('subscription-userinfo')
                        if info:
                            info_num = re.findall(r'\d+', info)
                            if info_num:
                                upload = int(info_num[0])
                                download = int(info_num[1])
                                total = int(info_num[2])
                                unused = (total - upload - download) / 1024 / 1024 / 1024
                                unused_rounded = round(unused, 2)
                                if unused_rounded > 0:
                                    header_info_valid = True
                                    header_play_info = '可用流量:' + str(unused_rounded) + ' GB                    ' + url
                    except Exception:
                        pass

                    # Body Check
                    content_limit = self.content_limit_mb * 1024 * 1024
                    content = b""
                    try:
                        for chunk in res.iter_content(chunk_size=8192):
                            content += chunk
                            if len(content) > content_limit:
                                logger.debug(f'{self.mask_url(url)} 超过大小限制，截断下载')
                                break
                        text = content.decode('utf-8', errors='ignore')
                    except Exception:
                        res.close()
                        if attempt < 2: continue # 下载中断尝试重试
                        break
                    finally:
                        res.close()

                    # 质量控制：内容去重检查 (已废弃文件级 MD5 去重)
                    with self.lock:
                        self.quality_stats['total_checked'] += 1
                    
                    # 解析节点并加入全局去重池
                    nodes = self.extract_nodes(text)
                    if nodes:
                        with self.lock:
                            self.unique_nodes.update(nodes)

                    # Clash 判断
                    is_clash = False
                    try:
                        if 'proxies:' in text:
                            is_clash = True
                            if not self.validate_subscription_quality(url, text, is_clash=True):
                                break # 质量不达标，不重试
                            
                            with self.lock:
                                self.new_clash_list.append(url)
                                if header_info_valid:
                                    self.new_sub_list.append(url)
                                    self.play_list.append(header_play_info)
                            break # 成功
                    except Exception:
                        pass

                    # V2Ray/Base64 判断
                    try:
                        sample_length = min(256, len(text))
                        head_text = text[:sample_length].strip()
                        missing_padding = len(head_text) % 4
                        if missing_padding:
                            head_text += '=' * (4 - missing_padding)
                        
                        decoded_text = base64.b64decode(head_text).decode('utf-8', errors='ignore')
                        if self.filter_base64(decoded_text):
                            if not self.validate_subscription_quality(url, text, is_clash=False):
                                break # 质量不达标，不重试
                            
                            with self.lock:
                                self.new_v2_list.append(url)
                                if header_info_valid:
                                    self.new_sub_list.append(url)
                                    self.play_list.append(header_play_info)
                    except Exception:
                        pass
                    
                    # 成功处理完毕（即使没匹配到任何类型，也视为200响应处理结束）
                    break
                else:
                    # 非 200, 403, 429 的其他错误 (如 404, 500)
                    res.close()
                    if attempt < 2 and res.status_code >= 500:
                        # 5xx 错误可以重试
                        continue
                    
                    self.failed_sub_list.append(url)
                    logger.warning(f'{self.mask_url(url)}\t状态码异常: {res.status_code}')
                    break

            except Exception:
                # 网络异常重试
                if attempt < 2:
                    continue
                self.failed_sub_list.append(url)
                logger.warning(f'{self.mask_url(url)}\t请求失败 - 已标记为失效')
                break
        
        bar.update(1)

    def start_check_urls(self, url_list):
        logger.info('开始筛选---')
        
        # 加载自动黑名单
        blacklist_set = set()
        if os.path.exists(self.blacklist_path):
            try:
                with open(self.blacklist_path, 'r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
                
                # 限制黑名单大小，防止无限膨胀
                blacklist_limit = 50000
                if len(lines) > blacklist_limit:
                    logger.warning(f'黑名单行数 ({len(lines)}) 超过限制 ({blacklist_limit})，执行自动清理...')
                    # 保留最新的 50000 条 (假设是追加写入，末尾为最新)
                    lines = lines[-blacklist_limit:]
                    try:
                        with open(self.blacklist_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(lines))
                        logger.info('黑名单清理完成')
                    except Exception as e:
                        logger.error(f'黑名单清理写入失败: {e}')

                blacklist_set = set(line.strip() for line in lines if line.strip())
                logger.info(f'已加载自动黑名单，包含 {len(blacklist_set)} 个失效链接')
            
            except MemoryError:
                logger.error('加载黑名单时发生 MemoryError，正在重置文件...')
                try:
                    if os.path.exists(self.blacklist_path):
                        backup_path = self.blacklist_path + '.bak'
                        os.rename(self.blacklist_path, backup_path)
                        logger.warning(f'原黑名单已备份至: {backup_path}')
                except Exception as e:
                    logger.error(f'备份黑名单失败: {e}')
                blacklist_set = set()

            except Exception as e:
                logger.warning(f'加载黑名单失败: {e}')

        # 黑名单过滤
        if blacklist_set:
            original_count = len(url_list)
            url_list = [str(url) for url in url_list if str(url) not in blacklist_set]
            filtered_count = original_count - len(url_list)
            if filtered_count > 0:
                logger.info(f'已根据黑名单跳过 {filtered_count} 个 URL')
        
        bar = tqdm(total=len(url_list), desc='订阅筛选：')
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.sub_check, url, bar) for url in url_list]
            concurrent.futures.wait(futures)

        bar.close()
        logger.info('筛选完成')

    def save_collected_nodes(self):
        if not self.collected_nodes_set:
            return

        old_nodes = set()
        if os.path.exists(self.collected_nodes_path):
            try:
                with open(self.collected_nodes_path, 'r', encoding='utf-8') as f:
                    old_nodes = set(f.read().splitlines())
            except MemoryError:
                logger.error('读取 collected_nodes.txt 时发生 MemoryError，正在重置文件...')
                try:
                    backup_path = self.collected_nodes_path + '.bak'
                    os.rename(self.collected_nodes_path, backup_path)
                    logger.warning(f'原文件已备份至: {backup_path}')
                except Exception as e:
                    logger.error(f'备份失败: {e}')
                old_nodes = set()
            except Exception as e:
                logger.warning(f'读取已采集节点失败: {e}')
        
        all_nodes = old_nodes | self.collected_nodes_set
        
        # 严格过滤无效节点 (必须包含 :// 且长度 > 15)
        all_nodes = {node for node in all_nodes if '://' in node and len(node) > 15}

        # 限制文件大小
        nodes_limit = 10000
        if len(all_nodes) > nodes_limit:
            logger.info(f'节点总数 ({len(all_nodes)}) 超过限制 ({nodes_limit})，执行随机采样清理...')
            # 随机保留指定数量，防止文件过大
            all_nodes = set(random.sample(list(all_nodes), nodes_limit))
        
        try:
            with open(self.collected_nodes_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sorted(all_nodes)))
            logger.info(f'已保存 {len(self.collected_nodes_set)} 个新节点到 {self.collected_nodes_path} (当前总数: {len(all_nodes)})')
        except Exception as e:
            logger.error(f'保存节点文件失败: {e}')

    def sub_update(self, url_list, path_yaml):
        logger.info('开始更新订阅---')
        if len(url_list) == 0:
            logger.info('没有需要更新的数据')
            return 
        
        # 重置列表
        self.new_sub_list = []
        self.new_clash_list = []
        self.new_v2_list = []
        self.play_list = []
        self.failed_sub_list = []
        
        check_url_list = list(set(url_list))
        
        # 写入 _url_check.txt
        abs_path_yaml = self.get_abs_path(path_yaml)
        # url_file = abs_path_yaml.replace('.yaml','_url_check.txt')
        # with open(url_file, 'w', encoding='utf-8') as f:
        #     f.write('\n'.join(str(item) for item in check_url_list))
            
        self.start_check_urls(check_url_list)
        
        # 处理失效链接
        if self.failed_sub_list:
            failed_count = len(self.failed_sub_list)
            logger.warning(f'发现 {failed_count} 个失效订阅链接，已自动清理')
            
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.failed_log_path, 'a', encoding='utf-8') as f:
                f.write(f'\n=== {timestamp} - 失效订阅 ({failed_count} 个) ===\n')
                for failed_url in self.failed_sub_list:
                    f.write(f'{failed_url}\n')
            
            try:
                with open(self.blacklist_path, 'a', encoding='utf-8') as f:
                    for failed_url in self.failed_sub_list:
                        f.write(f'{failed_url}\n')
                logger.info(f'已将 {failed_count} 个失效链接加入自动黑名单')
            except Exception as e:
                logger.warning(f'写入黑名单失败: {e}')
        
        # 更新 YAML
        dict_url = self.load_sub_yaml(path_yaml)
        
        self.new_sub_list = sorted(list(set(self.new_sub_list)))
        self.new_clash_list = sorted(list(set(self.new_clash_list)))
        self.new_v2_list = sorted(list(set(self.new_v2_list)))
        self.play_list = sorted(list(set(self.play_list)))

        dict_url.update({'机场订阅': self.new_sub_list})
        dict_url.update({'clash订阅': self.new_clash_list})
        dict_url.update({'v2订阅': self.new_v2_list})
        dict_url.update({'开心玩耍': self.play_list})
        
        with open(abs_path_yaml, 'w', encoding="utf-8") as f:
            yaml.dump(dict_url, f, allow_unicode=True)
        
        self.print_quality_report()

    def print_quality_report(self):
        total = self.quality_stats['total_checked']
        if total == 0: return
        
        valid_count = len(self.new_sub_list) + len(self.new_clash_list) + len(self.new_v2_list)
        failed_count = len(self.failed_sub_list)
        
        logger.info('='*60)
        logger.info('📊 订阅抓取统计报告')
        logger.info('='*60)
        logger.info(f'✅ 有效订阅: {valid_count} 个')
        logger.info(f'   - Clash 订阅: {len(self.new_clash_list)} 个')
        logger.info(f'   - V2Ray 订阅: {len(self.new_v2_list)} 个')
        logger.info(f'   - 机场订阅: {len(self.new_sub_list)} 个')
        
        if self.enable_quality_check:
            logger.info(f'\n🔍 质量控制统计:')
            logger.info(f'   - 检查总数: {total} 个')
            
            low_quality_total = (self.quality_stats['empty_subscription'] + 
                                self.quality_stats['low_quality'] + 
                                self.quality_stats['spam_content'])
            if low_quality_total > 0:
                logger.info(f'   - 低质量订阅: {low_quality_total} 个')
        
        if failed_count > 0:
            logger.info(f'\n❌ 失效订阅: {failed_count} 个')
        logger.info('='*60)

    @logger.catch
    def url_check_valid(self, target, url, bar):
        # 注意：这里移除了 @retry 装饰器，改由内部循环处理重试和故障转移
        # 这样可以确保遍历所有后端，而不是只重试某一个
        
        success = False
        url_encode = quote(url, safe='')
        
        # 遍历所有配置的后端 API
        for api_url in self.check_url_list:
            try:
                check_url_string = self.check_node_url_str.format(api_url, target, url_encode)
                headers = {'User-Agent': self.get_random_ua()}
                
                # 设置较短的超时时间，加快轮询速度
                res = requests.get(check_url_string, headers=headers, timeout=self.request_timeout, proxies=self.proxies)
                
                if res.status_code == 200:
                    with self.lock:
                        self.airport_list.append(url)
                    success = True
                    break # 成功则停止轮询
            except requests.RequestException:
                continue # 当前 API 失败，尝试下一个
            except Exception as e:
                logger.debug(f'解析失败: {api_url} - {type(e).__name__}')
                continue
                
        if not success:
            logger.warning(f'所有节点转换 API 均不可用或检测失败: {self.mask_url(url)[:30]}...')
            # 如果是列表为空导致没有循环，也属于失败
            if not self.check_url_list:
                logger.warning('所有节点转换 API 均不可用，请检查配置文件')
        
        bar.update(1)

    def write_url_config(self, url_file, url_list, target):
        logger.info('检测订阅节点有效性')
        self.airport_list = []
        bar = tqdm(total=len(url_list), desc='节点检测：')
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.url_check_valid, target, url, bar) for url in url_list]
            concurrent.futures.wait(futures)
            
        bar.close()
        logger.info('检测订阅节点有效性完成')

        direct_nodes = []
        if os.path.exists(self.collected_nodes_path):
            with open(self.collected_nodes_path, 'r', encoding='utf-8') as f:
                direct_nodes = f.read().splitlines()
        
        final_list = self.airport_list + direct_nodes
        write_str = '\n'.join(str(item) for item in final_list)

        output_file = url_file.replace('sub_store', target)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(write_str)

    def write_sub_store(self, yaml_file):
        logger.info('写入 sub_store 文件--')
        dict_url = self.load_sub_yaml(yaml_file)
        abs_yaml_file = self.get_abs_path(yaml_file)

        play_list = dict_url['开心玩耍']
        play_url_list = re.findall(self.re_str, str(play_list))
        
        sub_list = dict_url['机场订阅']
        sub_url_list = re.findall(self.re_str, str(sub_list))
        
        write_str = "-- play_list --\n\n\n" + '\n'.join(str(item) for item in play_url_list)
        write_str += "\n\n\n-- sub_list --\n\n\n" + '\n'.join(str(item) for item in sub_url_list)

        url_file = abs_yaml_file.replace('.yaml','_sub_store.txt')
        with open(url_file, 'w', encoding='utf-8') as f:
            f.write(write_str)
        
        self.write_url_config(url_file, play_url_list, 'loon')
        self.write_url_config(url_file, sub_url_list, 'clash')

    def write_merge_files(self, yaml_file):
        """生成合并后的文件"""
        
        # 1. 汇总所有节点
        final_nodes = list(self.unique_nodes) # 包含从订阅中解析的所有节点
        
        # 2. 合并直接采集的节点 (虽然 sub_check 已经把订阅里的节点加进去了，但 collected_nodes_set 来自网页爬取)
        final_nodes.extend(list(self.collected_nodes_set))
        
        # 3. 再次去重并排序
        final_nodes = sorted(list(set(final_nodes)))
        
        # 4. 写入 sub_merge.txt (节点列表)
        content_merge = '\n'.join(final_nodes)
        path_merge = os.path.join(self.base_dir, 'sub_merge.txt')
        with open(path_merge, 'w', encoding='utf-8') as f:
            f.write(content_merge)
        
        # 5. 写入 _url_check.txt (同样使用去重后的节点集合，满足用户需求)
        # 注意：这里我们使用 yaml_file 的路径来确定 _url_check.txt 的位置，或者直接覆盖
        abs_path_yaml = self.get_abs_path(yaml_file)
        url_check_path = abs_path_yaml.replace('.yaml','_url_check.txt')
        with open(url_check_path, 'w', encoding='utf-8') as f:
            f.write(content_merge)
            
        # 6. 写入 base64 版本
        path_base64 = os.path.join(self.base_dir, 'sub_merge_base64.txt')
        with open(path_base64, 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(content_merge.encode('utf-8')).decode('utf-8'))
            
        logger.info(f'合并完成: {len(final_nodes)} 个唯一节点已写入 sub_merge.txt')

        # 6. 更新 sub_all.yaml (仍然保留有效的订阅链接作为历史记录)
        # 注意：这里的 new_sub_list 等是在 run() 流程中 populated 的
        # 如果是 merge_sub 调用 sub_update，这些 list 包含了当前有效的所有订阅
        # 我们需要读取 yaml_file, 然后更新它
        pass # write_sub_store 已经负责写入 yaml，这里不需要重复写入 yaml

    def get_url_form_yaml(self, yaml_file):
        dict_url = self.load_sub_yaml(yaml_file)
        url_list = []
        for key in ['机场订阅', 'clash订阅', 'v2订阅', '开心玩耍']:
            url_list.extend(dict_url.get(key, []))
        
        url_list = re.findall(self.re_str, str(url_list))
        return [url for url in url_list if self.is_safe_url(url)]

    def get_url_form_channel(self):
        logger.info('读取config成功')
        url_list = []
        
        if self.list_tg:
            logger.info(f'开始抓取 {len(self.list_tg)} 个 Telegram 频道...')
            for channel_url in self.list_tg:
                temp_list = self.fetch_urls_from_page(channel_url)
                if temp_list: url_list.extend(temp_list)
        
        if self.list_web_fuzz:
            logger.info(f'开始模糊抓取 {len(self.list_web_fuzz)} 个网页...')
            for web_url in self.list_web_fuzz:
                temp_list = self.fetch_urls_from_page(web_url)
                if temp_list: url_list.extend(temp_list)

        if self.list_subscribe:
            logger.info(f'加载 {len(self.list_subscribe)} 个直连订阅源...')
            url_list.extend(self.list_subscribe)

        self.save_collected_nodes()
        return url_list

    def run(self):
        start_time = time.time()
        try:
            # 1. Update Today's Sub
            url_list = self.get_url_form_channel()
            path_yaml = pre_check() # pre_check returns relative path
            self.sub_update(url_list, path_yaml)
            
            # 2. Merge Sub
            all_yaml = get_sub_all() # returns relative path
            # pre_check was called above, so path_yaml is valid
            
            merge_url_list = []
            merge_url_list.extend(self.get_url_form_yaml(all_yaml))
            merge_url_list.extend(self.get_url_form_yaml(path_yaml))
            
            self.sub_update(merge_url_list, all_yaml)
            self.write_sub_store(all_yaml)
            self.write_merge_files(all_yaml)
            
            # 3. Notification
            runtime = time.time() - start_time
            runtime_str = f"{int(runtime // 60)}分{int(runtime % 60)}秒"
            
            try:
                from notification import send_notification, format_notification_message
                stats_data = {
                    'valid_count': len(self.new_sub_list) + len(self.new_clash_list) + len(self.new_v2_list),
                    'clash_count': len(self.new_clash_list),
                    'v2ray_count': len(self.new_v2_list),
                    'airport_count': len(self.new_sub_list),
                    'total_checked': self.quality_stats.get('total_checked', 0),
                    'low_quality_count': (self.quality_stats.get('low_quality', 0) + 
                                         self.quality_stats.get('empty_subscription', 0) + 
                                         self.quality_stats.get('spam_content', 0)),
                    'failed_count': len(self.failed_sub_list),
                    'runtime': runtime_str
                }
                message = format_notification_message(stats_data)
                send_notification(message, "CollectSub 运行成功")
            except Exception as e:
                logger.warning(f'发送通知失败: {e}')
                
            logger.info('✅ 所有任务执行完成')
            
        except Exception as e:
            logger.error(f'❌ 运行失败: {e}')
            try:
                from notification import send_notification, format_error_notification
                error_msg = format_error_notification(str(e))
                send_notification(error_msg, "CollectSub 运行失败")
            except:
                pass
            raise

if __name__ == '__main__':
    collector = SubscriptionCollector()
    collector.run()
