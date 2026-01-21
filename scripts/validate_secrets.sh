#!/bin/bash
# Secrets 验证脚本
# 用于验证 GitHub Actions Secrets 是否正确配置

set -e  # 遇到错误立即退出

echo "🔐 开始验证 Secrets 配置..."
echo ""

# ============================================
# 1. 验证必需的 Secrets
# ============================================

echo "📋 检查必需的 Secrets..."

# 检查 GIST_TOKEN（或 GITHUB_TOKEN）
if [ -z "$GIST_TOKEN" ] && [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误: GIST_TOKEN 未配置"
    echo "   请在仓库 Settings → Secrets → Actions 中添加 GIST_TOKEN"
    echo "   获取方式: https://github.com/settings/tokens/new"
    exit 1
fi

# 使用 GIST_TOKEN 或回退到 GITHUB_TOKEN
TOKEN="${GIST_TOKEN:-$GITHUB_TOKEN}"

echo "✅ Token 已配置"

# ============================================
# 2. 验证 Token 有效性
# ============================================

echo ""
echo "🔍 验证 Token 有效性..."

response=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/user)

if echo "$response" | grep -q "Bad credentials"; then
    echo "❌ 错误: Token 无效或已过期"
    echo "   请检查 Token 是否正确"
    exit 1
fi

if echo "$response" | grep -q "login"; then
    username=$(echo "$response" | grep -o '"login":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Token 有效 (用户: $username)"
else
    echo "⚠️  警告: 无法验证用户信息"
fi

# ============================================
# 3. 验证 Gist 权限
# ============================================

echo ""
echo "🔑 验证 Gist 权限..."

# 获取 Token 权限
scopes_header=$(curl -s -I -H "Authorization: token $TOKEN" https://api.github.com/user 2>&1 | grep -i "x-oauth-scopes" || echo "")

if [ -z "$scopes_header" ]; then
    echo "⚠️  警告: 无法获取 Token 权限信息"
    echo "   如果使用默认 GITHUB_TOKEN，Gist 功能可能不可用"
else
    if echo "$scopes_header" | grep -qi "gist"; then
        echo "✅ Token 拥有 gist 权限"
    else
        echo "❌ 警告: Token 缺少 gist 权限"
        echo "   订阅URL生成功能将无法使用"
        echo "   请创建新的 Token 并勾选 'gist' 权限"
        echo ""
        echo "   提示: 使用 GIST_TOKEN 而非默认 GITHUB_TOKEN"
    fi
fi

# ============================================
# 4. 验证 GIST_ID（可选）
# ============================================

echo ""
echo "📌 检查 GIST_ID 配置..."

if [ -z "$GIST_ID" ]; then
    echo "⚠️  GIST_ID 未配置（可选）"
    echo "   每次运行会创建新的 Gist，订阅URL会变化"
    echo "   建议配置 GIST_ID 以固定订阅链接"
else
    echo "✅ GIST_ID 已配置: ${GIST_ID:0:8}..."
    
    # 验证 GIST_ID 是否有效
    gist_response=$(curl -s -H "Authorization: token $TOKEN" "https://api.github.com/gists/$GIST_ID")
    
    if echo "$gist_response" | grep -q "Not Found"; then
        echo "⚠️  警告: GIST_ID 无效或无权访问"
        echo "   将创建新的 Gist"
    else
        echo "✅ GIST_ID 有效且可访问"
    fi
fi

# ============================================
# 5. 检查可选 Secrets
# ============================================

echo ""
echo "📮 检查可选通知配置..."

optional_count=0

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "✅ Telegram 通知已配置"
    optional_count=$((optional_count + 1))
fi

if [ -n "$ABUSEIPDB_API_KEY" ]; then
    echo "✅ AbuseIPDB API Key 已配置"
    optional_count=$((optional_count + 1))
fi

if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    echo "✅ Discord Webhook 已配置"
    optional_count=$((optional_count + 1))
fi

if [ -n "$SERVERCHAN_KEY" ]; then
    echo "✅ Server酱 已配置"
    optional_count=$((optional_count + 1))
fi

if [ -n "$PUSHPLUS_TOKEN" ]; then
    echo "✅ PushPlus 已配置"
    optional_count=$((optional_count + 1))
fi

if [ $optional_count -eq 0 ]; then
    echo "ℹ️  未配置通知服务（可选）"
    echo "   配置后可接收订阅更新通知"
fi

# ============================================
# 总结
# ============================================

echo ""
echo "═══════════════════════════════════════"
echo "✅ Secrets 验证完成"
echo "═══════════════════════════════════════"
echo ""

exit 0
