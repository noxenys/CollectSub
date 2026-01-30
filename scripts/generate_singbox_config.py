#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import base64
import json
import os
import sys
import urllib.parse

def _add_padding(value):
    return value + '=' * (-len(value) % 4)

def _sanitize_url(url):
    return url.replace('&amp;', '&').strip()

def _parse_query(query):
    params = urllib.parse.parse_qs(query, keep_blank_values=True)
    return {k: v[-1] if v else '' for k, v in params.items()}

def _bool_param(val):
    if val is None:
        return None
    return str(val).lower() in ('1', 'true', 'yes', 'on')

def _split_list(val):
    if not val:
        return []
    return [v.strip() for v in str(val).split(',') if v.strip()]

def _build_transport(params):
    transport = (params.get('type') or params.get('transport') or '').lower()
    if transport == 'ws':
        headers = {}
        host_header = params.get('host') or params.get('hostHeader') or params.get('ws-host')
        if host_header:
            headers['Host'] = host_header
        path = params.get('path') or '/'
        out = {'type': 'ws', 'path': path}
        if headers:
            out['headers'] = headers
        return out
    if transport == 'grpc':
        service = params.get('serviceName') or params.get('service_name') or params.get('grpc_service_name') or params.get('path') or ''
        out = {'type': 'grpc'}
        if service:
            out['service_name'] = service
        return out
    return None

def _build_tls(params, server_name_hint=None):
    security = (params.get('security') or params.get('tls') or '').lower()
    sni = params.get('sni') or params.get('peer') or params.get('servername') or params.get('serverName')
    server_name = sni or server_name_hint
    allow_insecure = _bool_param(params.get('allowInsecure') or params.get('insecure'))
    alpn = _split_list(params.get('alpn'))
    fingerprint = params.get('fp')

    enabled = False
    if security in ('tls', 'reality', 'xtls'):
        enabled = True
    elif server_name:
        enabled = True

    if not enabled:
        return None

    tls = {'enabled': True}
    if server_name:
        tls['server_name'] = server_name
    if allow_insecure is not None:
        tls['insecure'] = bool(allow_insecure)
    if alpn:
        tls['alpn'] = alpn
    if fingerprint:
        tls['utls'] = {'enabled': True, 'fingerprint': fingerprint}

    if security == 'reality' or params.get('pbk'):
        reality = {
            'enabled': True,
            'public_key': params.get('pbk') or '',
            'short_id': params.get('sid') or ''
        }
        tls['reality'] = reality

    return tls

def _parse_vmess(url):
    payload = url[len('vmess://'):]
    payload = _add_padding(payload)
    try:
        decoded = base64.b64decode(payload).decode('utf-8', errors='ignore')
        data = json.loads(decoded)
    except Exception as exc:
        raise ValueError(f'vmess decode failed: {exc}') from exc

    server = data.get('add')
    port = int(data.get('port', 0)) if data.get('port') else 0
    uuid = data.get('id')
    if not server or not port or not uuid:
        raise ValueError('vmess missing server/port/uuid')

    out = {
        'type': 'vmess',
        'tag': 'proxy',
        'server': server,
        'server_port': port,
        'uuid': uuid,
        'security': data.get('scy') or 'auto',
    }
    if data.get('aid'):
        try:
            out['alter_id'] = int(data.get('aid'))
        except Exception:
            pass

    params = {
        'security': data.get('tls') or data.get('security'),
        'sni': data.get('sni') or data.get('servername'),
        'alpn': data.get('alpn'),
        'allowInsecure': data.get('allowInsecure'),
    }

    transport_type = (data.get('net') or '').lower()
    if transport_type == 'ws':
        params.update({'type': 'ws', 'path': data.get('path'), 'host': data.get('host')})
    elif transport_type == 'grpc':
        params.update({'type': 'grpc', 'serviceName': data.get('path')})

    tls = _build_tls(params, server_name_hint=server)
    if tls:
        out['tls'] = tls

    transport = _build_transport(params)
    if transport:
        out['transport'] = transport

    return out

def _parse_vless(url):
    parsed = urllib.parse.urlparse(url)
    params = _parse_query(parsed.query)
    uuid = urllib.parse.unquote(parsed.username or '')
    server = parsed.hostname
    port = parsed.port or 443
    if not uuid or not server:
        raise ValueError('vless missing uuid/server')

    out = {
        'type': 'vless',
        'tag': 'proxy',
        'server': server,
        'server_port': port,
        'uuid': uuid,
    }
    flow = params.get('flow')
    if flow:
        out['flow'] = flow

    tls = _build_tls(params, server_name_hint=server)
    if tls:
        out['tls'] = tls

    transport = _build_transport(params)
    if transport:
        out['transport'] = transport

    return out

def _parse_trojan(url):
    parsed = urllib.parse.urlparse(url)
    params = _parse_query(parsed.query)
    password = urllib.parse.unquote(parsed.username or '')
    server = parsed.hostname
    port = parsed.port or 443
    if not password or not server:
        raise ValueError('trojan missing password/server')

    out = {
        'type': 'trojan',
        'tag': 'proxy',
        'server': server,
        'server_port': port,
        'password': password,
    }

    tls = _build_tls(params, server_name_hint=server)
    if tls:
        out['tls'] = tls

    transport = _build_transport(params)
    if transport:
        out['transport'] = transport

    return out

def _parse_ss(url):
    payload = url[len('ss://'):]
    payload = payload.split('#', 1)[0]
    payload = payload.split('?', 1)[0]

    if '@' not in payload:
        payload = _add_padding(payload)
        decoded = base64.b64decode(payload).decode('utf-8', errors='ignore')
        payload = decoded

    if '@' not in payload:
        raise ValueError('ss missing userinfo')

    userinfo, server_info = payload.rsplit('@', 1)
    if ':' not in userinfo or ':' not in server_info:
        raise ValueError('ss invalid format')

    method, password = userinfo.split(':', 1)
    server, port = server_info.rsplit(':', 1)
    out = {
        'type': 'shadowsocks',
        'tag': 'proxy',
        'server': server,
        'server_port': int(port),
        'method': method,
        'password': password,
    }
    return out

def _parse_hysteria2(url):
    parsed = urllib.parse.urlparse(url)
    params = _parse_query(parsed.query)
    password = urllib.parse.unquote(parsed.username or '')
    server = parsed.hostname
    port = parsed.port or 443
    if not password or not server:
        raise ValueError('hysteria2 missing password/server')

    out = {
        'type': 'hysteria2',
        'tag': 'proxy',
        'server': server,
        'server_port': port,
        'password': password,
    }

    tls = _build_tls(params, server_name_hint=server)
    if tls:
        out['tls'] = tls

    return out

def build_outbound(url):
    url = _sanitize_url(url)
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme == 'vmess':
        return _parse_vmess(url)
    if scheme == 'vless':
        return _parse_vless(url)
    if scheme == 'trojan':
        return _parse_trojan(url)
    if scheme == 'ss':
        return _parse_ss(url)
    if scheme == 'hysteria2':
        return _parse_hysteria2(url)
    raise ValueError(f'unsupported protocol: {scheme}')

def build_config(outbound, http_port, socks_port, log_level):
    return {
        'log': {'level': log_level},
        'inbounds': [
            {'type': 'http', 'tag': 'http-in', 'listen': '127.0.0.1', 'listen_port': http_port},
            {'type': 'socks', 'tag': 'socks-in', 'listen': '127.0.0.1', 'listen_port': socks_port},
        ],
        'outbounds': [
            outbound,
            {'type': 'direct', 'tag': 'direct'},
            {'type': 'block', 'tag': 'block'},
        ],
        'route': {
            'rules': [{'inbound': ['http-in', 'socks-in'], 'outbound': 'proxy'}],
            'final': 'proxy'
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Generate sing-box config from probe_head.json')
    parser.add_argument('--probe-json', default='sub/probe_head.json')
    parser.add_argument('--output', default='sub/singbox-probe.json')
    parser.add_argument('--http-port', type=int, default=7891)
    parser.add_argument('--socks-port', type=int, default=7890)
    parser.add_argument('--log-level', default='info')
    args = parser.parse_args()

    if not os.path.exists(args.probe_json):
        raise SystemExit(f'probe json not found: {args.probe_json}')

    with open(args.probe_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    node = data.get('node', data)
    if isinstance(node, dict):
        url = node.get('url')
    else:
        url = node

    if not url:
        raise SystemExit('probe json missing node url')

    outbound = build_outbound(url)
    outbound['tag'] = 'proxy'

    config = build_config(outbound, args.http_port, args.socks_port, args.log_level)
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=True, indent=2)

    print(args.output)

if __name__ == '__main__':
    main()
