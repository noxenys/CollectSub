#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

Telegram Bot 订阅分发工具

功能：将高质量节点通过Telegram Bot发送，避免在GitHub公开

"""

import os

import base64

import requests

from loguru import logger

def send_file_to_telegram(file_path, caption=""):

    """

    发送文件到Telegram

    Args:

        file_path: 文件路径

        caption: 文件说明

    """

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:

        logger.error('❌ 未配置 Telegram Bot，请设置环境变量：')

        logger.error('   - TELEGRAM_BOT_TOKEN')

        logger.error('   - TELEGRAM_CHAT_ID')

        return False

    try:

        url = f'https://api.telegram.org/bot{bot_token}/sendDocument'

        with open(file_path, 'rb') as f:

            files = {'document': f}

            data = {

                'chat_id': chat_id,

                'caption': caption,

                'parse_mode': 'Markdown'

            }

            response = requests.post(url, data=data, files=files, timeout=30)

        if response.status_code == 200:

            logger.info(f'✅ 文件已通过 Telegram 发送: {os.path.basename(file_path)}')

            return True

        else:

            logger.error(f'❌ Telegram 发送失败: HTTP {response.status_code}')

            logger.error(f'   响应: {response.text}')

            return False

    except Exception as e:

        logger.error(f'❌ Telegram 发送异常: {e}')

        return False

def create_subscription_url(nodes_file):

    """

    创建Base64编码的订阅URL

    Args:

        nodes_file: 节点文件路径

    Returns:

        base64编码的订阅内容

    """

    try:

        with open(nodes_file, 'r', encoding='utf-8') as f:

            nodes = [line.strip() for line in f if line.strip()]

        # 合并所有节点

        content = '\n'.join(nodes)

        # Base64编码

        b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        return b64_content

    except Exception as e:

        logger.error(f'❌ 创建订阅URL失败: {e}')

        return None

def send_subscription_to_telegram(nodes_file, report_file=None):

    """

    发送订阅链接到Telegram

    Args:

        nodes_file: 高质量节点文件路径

        report_file: 质量报告文件路径（可选）

    """

    logger.info('='*60)

    logger.info('📤 开始发送订阅到 Telegram Bot')

    logger.info('='*60)

    # 检查文件存在

    if not os.path.exists(nodes_file):

        logger.error(f'❌ 节点文件不存在: {nodes_file}')

        return False

    # 统计节点数

    with open(nodes_file, 'r', encoding='utf-8') as f:

        node_count = len([line for line in f if line.strip()])

    # 创建Base64订阅

    b64_sub = create_subscription_url(nodes_file)

    if not b64_sub:

        return False

    # 构建消息

    caption = f"""🎉 *高质量节点订阅*

📊 *统计信息*:

  • 节点总数: {node_count} 个

  • 文件大小: {os.path.getsize(nodes_file) / 1024:.2f} KB

💡 *使用方法*:

1. 下载此文件

2. 直接导入到代理客户端

3. 或使用订阅链接（见下方）

⚠️ *注意*: 

- 此订阅为私密分享，请勿公开传播

- 节点质量已筛选，延迟<500ms

- 定期更新，保持订阅最新

"""

    # 发送节点文件

    success = send_file_to_telegram(nodes_file, caption)

    # 发送质量报告（如果存在）

    if report_file and os.path.exists(report_file):

        logger.info('📊 发送质量报告...')

        send_file_to_telegram(report_file, '📈 *节点质量分析报告*')

    # 发送Base64订阅链接（作为文本消息）

    if success:

        # 创建临时订阅文件

        temp_sub_file = nodes_file.replace('.txt', '_base64.txt')

        with open(temp_sub_file, 'w', encoding='utf-8') as f:

            f.write(b64_sub)

        sub_caption = """📋 *Base64订阅内容*

💡 *使用方法*:

将此文件内容复制为订阅链接使用

格式: `订阅转换API?url=<此内容>`

"""

        send_file_to_telegram(temp_sub_file, sub_caption)

        # 清理临时文件

        try:

            os.remove(temp_sub_file)

        except Exception:

            pass

    if success:

        logger.info('='*60)

        logger.info('✅ 订阅已成功发送到 Telegram')

        logger.info('='*60)

        # 询问是否生成订阅URL

        try:

            from generate_subscription_url import SubscriptionURLGenerator

            logger.info('\n🔗 正在生成订阅URL...')

            generator = SubscriptionURLGenerator()

            generator.send_subscription_urls_to_telegram(nodes_file)

        except Exception as e:

            logger.warning(f'⚠️ 订阅URL生成失败: {e}')

            logger.info('💡 提示: 需要配置 GITHUB_TOKEN 才能创建Gist订阅')

    return success

def main():

    """主函数 - 发送高质量节点到Telegram"""

    logger.remove()

    logger.add(lambda msg: print(msg, end=''), colorize=True, 

               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    # 默认路径

    base_dir = os.path.dirname(os.path.abspath(__file__))

    nodes_file = os.path.join(base_dir, 'sub', 'high_quality_nodes.txt')

    report_file = os.path.join(base_dir, 'sub', 'quality_report.json')

    # 发送订阅

    send_subscription_to_telegram(nodes_file, report_file)

if __name__ == '__main__':

    main()
