# -*- coding: utf-8 -*-

"""

通知模块 - 支持多种通知方式

支持的通知方式：

1. Telegram Bot

2. Discord Webhook

3. Server酱（微信推送）

4. PushPlus

使用环境变量配置：

- TELEGRAM_BOT_TOKEN: Telegram Bot Token

- TELEGRAM_CHAT_ID: Telegram Chat ID

- DISCORD_WEBHOOK_URL: Discord Webhook URL

- SERVERCHAN_KEY: Server酱 SendKey

- PUSHPLUS_TOKEN: PushPlus Token

"""

import os

import requests

from loguru import logger

import datetime

def send_notification(message, title="SmartSub 运行通知"):

    """

    统一的通知发送接口

    会尝试所有配置的通知方式

    """

    sent_count = 0

    # 尝试 Telegram

    if send_telegram(message):

        sent_count += 1

    # 尝试 Discord

    if send_discord(message):

        sent_count += 1

    # 尝试 Server酱

    if send_serverchan(title, message):

        sent_count += 1

    # 尝试 PushPlus

    if send_pushplus(title, message):

        sent_count += 1

    if sent_count == 0:

        logger.info('💡 未配置任何通知方式，跳过通知发送')

        logger.info('💡 提示：可在环境变量中配置 Telegram/Discord/Server酱 等通知')

    else:

        logger.info(f'✅ 成功发送 {sent_count} 个通知')

def send_telegram(message):

    """

    发送 Telegram 通知

    需要环境变量：

    - TELEGRAM_BOT_TOKEN: Bot token (从 @BotFather 获取)

    - TELEGRAM_CHAT_ID: Chat ID

    """

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:

        return False

    try:

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

        data = {

            'chat_id': chat_id,

            'text': message,

            'parse_mode': 'Markdown',

            'disable_web_page_preview': True

        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:

            logger.info('✅ Telegram 通知发送成功')

            return True

        else:

            logger.warning(f'⚠️ Telegram 通知失败: HTTP {response.status_code}')

            return False

    except Exception as e:

        logger.error(f'❌ Telegram 通知异常: {e}')

        return False

def send_discord(message):

    """

    发送 Discord Webhook 通知

    需要环境变量：

    - DISCORD_WEBHOOK_URL: Discord Webhook URL

    """

    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:

        return False

    try:

        data = {

            'content': message,

            'username': 'SmartSub Bot',

            'avatar_url': 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png'

        }

        response = requests.post(webhook_url, json=data, timeout=10)

        if response.status_code in [200, 204]:

            logger.info('✅ Discord 通知发送成功')

            return True

        else:

            logger.warning(f'⚠️ Discord 通知失败: HTTP {response.status_code}')

            return False

    except Exception as e:

        logger.error(f'❌ Discord 通知异常: {e}')

        return False

def send_serverchan(title, message):

    """

    发送 Server酱 通知（微信推送）

    需要环境变量：

    - SERVERCHAN_KEY: Server酱 SendKey (从 https://sct.ftqq.com/ 获取)

    """

    key = os.getenv('SERVERCHAN_KEY')

    if not key:

        return False

    try:

        url = f'https://sctapi.ftqq.com/{key}.send'

        data = {

            'title': title,

            'desp': message

        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:

            result = response.json()

            if result.get('code') == 0:

                logger.info('✅ Server酱 通知发送成功')

                return True

            else:

                logger.warning(f'⚠️ Server酱 通知失败: {result.get("message")}')

                return False

        else:

            logger.warning(f'⚠️ Server酱 通知失败: HTTP {response.status_code}')

            return False

    except Exception as e:

        logger.error(f'❌ Server酱 通知异常: {e}')

        return False

def send_pushplus(title, message):

    """

    发送 PushPlus 通知（微信推送）

    需要环境变量：

    - PUSHPLUS_TOKEN: PushPlus Token (从 http://www.pushplus.plus/ 获取)

    """

    token = os.getenv('PUSHPLUS_TOKEN')

    if not token:

        return False

    try:

        url = 'http://www.pushplus.plus/send'

        data = {

            'token': token,

            'title': title,

            'content': message,

            'template': 'markdown'

        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:

            result = response.json()

            if result.get('code') == 200:

                logger.info('✅ PushPlus 通知发送成功')

                return True

            else:

                logger.warning(f'⚠️ PushPlus 通知失败: {result.get("msg")}')

                return False

        else:

            logger.warning(f'⚠️ PushPlus 通知失败: HTTP {response.status_code}')

            return False

    except Exception as e:

        logger.error(f'❌ PushPlus 通知异常: {e}')

        return False

def format_notification_message(stats_data):

    """

    格式化通知消息

    Args:

        stats_data: 包含统计信息的字典

        {

            'valid_count': 有效订阅数,

            'clash_count': Clash订阅数,

            'v2ray_count': V2Ray订阅数,

            'airport_count': 机场订阅数,

            'total_checked': 检查总数,

            'duplicate_count': 重复数,

            'low_quality_count': 低质量数,

            'failed_count': 失效数,

            'runtime': 运行时长

        }

    """

    valid = stats_data.get('valid_count', 0)

    failed = stats_data.get('failed_count', 0)

    total = stats_data.get('total_checked', 0)

    # 计算质量提升

    filtered = (stats_data.get('duplicate_count', 0) + 

                stats_data.get('low_quality_count', 0) + 

                failed)

    quality_improvement = (filtered / (total + filtered) * 100) if (total + filtered) > 0 else 0

    message = f"""🎉 *SmartSub 运行完成*

✅ *有效订阅*: {valid} 个

  • Clash: {stats_data.get('clash_count', 0)}

  • V2Ray: {stats_data.get('v2ray_count', 0)}

  • 机场: {stats_data.get('airport_count', 0)}

🔍 *质量控制*:

  • 检查总数: {total}

  • 重复过滤: {stats_data.get('duplicate_count', 0)}

  • 低质过滤: {stats_data.get('low_quality_count', 0)}

❌ *失效订阅*: {failed} 个

💡 *质量提升*: {quality_improvement:.1f}%

⏰ *运行时间*: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⌚ *耗时*: {stats_data.get('runtime', 'N/A')}

"""

    return message

def format_error_notification(error_message):

    """格式化错误通知消息"""

    message = f"""❌ *SmartSub 运行失败*

⚠️ *错误信息*:

{error_message}

⏰ *时间*: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 请检查日志获取详细信息

"""

    return message
