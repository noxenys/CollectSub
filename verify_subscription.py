#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本：检查 sub_all 文件是否为正确的 Base64 格式
"""

import base64
import os

def verify_subscription_file(filepath):
    """验证订阅文件格式"""
    print(f"\n{'='*60}")
    print(f"验证文件: {filepath}")
    print(f"{'='*60}")
    
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False
    
    try:
        # 读取文件
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        print(f"✅ 文件大小: {len(content)} 字节")
        
        # 尝试Base64解码
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            lines = [l.strip() for l in decoded.split('\n') if l.strip()]
            
            print(f"✅ Base64解码成功")
            print(f"✅ 总节点数: {len(lines)}")
            
            # 检查节点格式
            protocols = {}
            http_links = []
            
            for line in lines:
                if line.startswith(('http://', 'https://')):
                    http_links.append(line)
                elif '://' in line:
                    protocol = line.split('://')[0]
                    protocols[protocol] = protocols.get(protocol, 0) + 1
            
            # 输出统计
            print(f"\n📊 协议分布:")
            for proto, count in sorted(protocols.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {proto}: {count} 个")
            
            # 检查是否有http链接（不应该有）
            if http_links:
                print(f"\n⚠️ 警告: 发现 {len(http_links)} 个HTTP订阅链接（应为0）")
                for link in http_links[:3]:
                    print(f"   - {link[:50]}...")
                return False
            else:
                print(f"\n✅ 无HTTP订阅链接（正确）")
            
            # 显示示例节点
            if lines:
                print(f"\n📝 示例节点（前3个）:")
                for i, line in enumerate(lines[:3], 1):
                    preview = line if len(line) <= 60 else line[:57] + '...'
                    print(f"   {i}. {preview}")
            
            print(f"\n✅ 验证通过！文件格式正确")
            return True
            
        except Exception as e:
            print(f"❌ Base64解码失败: {e}")
            print(f"   文件内容预览: {content[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Sub_all 订阅文件格式验证工具")
    print("="*60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_check = [
        os.path.join(base_dir, 'sub', 'sub_all_clash.txt'),
        os.path.join(base_dir, 'sub', 'sub_all_loon.txt')
    ]
    
    results = {}
    for filepath in files_to_check:
        results[filepath] = verify_subscription_file(filepath)
    
    # 总结
    print(f"\n{'='*60}")
    print("验证总结")
    print(f"{'='*60}")
    
    for filepath, result in results.items():
        filename = os.path.basename(filepath)
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{filename}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print(f"\n🎉 所有文件验证通过！可以直接导入Clash/Loon使用。")
    else:
        print(f"\n⚠️ 部分文件验证失败，请检查生成逻辑。")
    
    return all_passed

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
