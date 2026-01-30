#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import yaml

ALLOWED_PROTOCOLS = {'vmess', 'ss', 'trojan', 'vless', 'hysteria2'}

def warn(msg):
    print(f'WARN: {msg}')

def error(msg):
    print(f'ERROR: {msg}')

def _load_config(path):
    if not os.path.exists(path):
        error(f'config not found: {path}')
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            error('config.yaml is not a mapping')
            return None
        return data
    except Exception as exc:
        error(f'failed to read config.yaml: {exc}')
        return None

def _check_protocols(config):
    nodes = config.get('nodes', {})
    protocols = nodes.get('protocols', [])
    if not protocols:
        warn('nodes.protocols is empty')
        return 1
    invalid = [p for p in protocols if str(p).lower() not in ALLOWED_PROTOCOLS]
    if invalid:
        warn(f'unsupported protocols in nodes.protocols: {invalid}')
        return 1
    return 0

def _check_dynamic_probe(config):
    dyn = config.get('dynamic_probe', {})
    supported = dyn.get('supported_protocols', [])
    if not supported:
        return 0
    invalid = [p for p in supported if str(p).lower() not in ALLOWED_PROTOCOLS]
    if invalid:
        warn(f'unsupported protocols in dynamic_probe.supported_protocols: {invalid}')
        return 1
    return 0

def _dedupe_report(name, items):
    if not items:
        return 0
    seen = set()
    dupes = 0
    for item in items:
        key = str(item).strip().lower()
        if not key:
            continue
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
    if dupes:
        warn(f'{name} has {dupes} duplicate entries')
    return dupes

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, '..', 'config.yaml')
    config = _load_config(config_path)
    if config is None:
        return 1

    warnings = 0
    warnings += _check_protocols(config)
    warnings += _check_dynamic_probe(config)

    warnings += _dedupe_report('tgchannel', config.get('tgchannel', []))
    warnings += _dedupe_report('subscribe', config.get('subscribe', []))
    warnings += _dedupe_report('web_pages', config.get('web_pages', []))
    warnings += _dedupe_report('subconverter_backends', config.get('subconverter_backends', []))
    warnings += _dedupe_report('sub_convert_apis', config.get('sub_convert_apis', []))

    if warnings:
        print(f'SELF-CHECK OK (with {warnings} warning(s))')
    else:
        print('SELF-CHECK OK')

    summary_path = os.getenv('GITHUB_STEP_SUMMARY')
    if summary_path:
        try:
            with open(summary_path, 'a', encoding='utf-8') as f:
                f.write('### Self Check\n')
                f.write(f'- Warnings: {warnings}\n')
        except Exception:
            pass
    return 0

if __name__ == '__main__':
    sys.exit(main())
