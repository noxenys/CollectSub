#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import yaml

REMOVE_REASONS = {'http_404', 'http_410'}

def _load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _dump_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)

def _dedupe_list(items):
    if not items:
        return [], 0
    seen = set()
    deduped = []
    removed = 0
    for item in items:
        key = str(item).strip()
        if not key:
            continue
        key_lower = key.lower()
        if key_lower in seen:
            removed += 1
            continue
        seen.add(key_lower)
        deduped.append(item)
    return deduped, removed

def _load_health(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, '..', 'config.yaml')
    health_path = os.path.join(base_dir, '..', 'sub', 'source_health.json')
    failed_log_path = os.path.join(base_dir, '..', 'failed_subscriptions.log')

    if not os.path.exists(config_path):
        print('config.yaml not found')
        return 1

    config = _load_yaml(config_path)
    if not isinstance(config, dict):
        print('config.yaml invalid')
        return 1

    health = _load_health(health_path)
    remove_set = set()

    if health:
        for item in health.get('failed', []):
            reason = str(item.get('reason', '')).lower()
            url = item.get('url')
            if reason in REMOVE_REASONS:
                remove_set.add(url)
        for item in health.get('low_quality', []):
            url = item.get('url')
            if url:
                remove_set.add(url)
    elif os.path.exists(failed_log_path):
        try:
            with open(failed_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('==='):
                        continue
                    parts = line.split('\t')
                    url = parts[0].strip()
                    reason = parts[1].strip().lower() if len(parts) > 1 else ''
                    if reason in REMOVE_REASONS:
                        remove_set.add(url)
        except Exception:
            pass

    total_removed = 0
    total_deduped = 0

    for key in ['tgchannel', 'subscribe', 'web_pages', 'subconverter_backends', 'sub_convert_apis']:
        items = config.get(key, [])
        if not isinstance(items, list):
            continue

        cleaned = []
        removed = 0
        for item in items:
            if item in remove_set:
                removed += 1
                continue
            cleaned.append(item)

        deduped, deduped_removed = _dedupe_list(cleaned)
        total_removed += removed
        total_deduped += deduped_removed
        config[key] = deduped

    if total_removed == 0 and total_deduped == 0:
        print('No sources removed')
        return 0

    backup_path = config_path + '.bak'
    if not os.path.exists(backup_path):
        _dump_yaml(backup_path, _load_yaml(config_path))

    _dump_yaml(config_path, config)
    print(f'Removed: {total_removed}, Deduped: {total_deduped}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
