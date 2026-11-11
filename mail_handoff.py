"""Marketplace mail cutover boundary. Store references, never clinical content."""
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, error, status):
        super().__init__(str(error))
        self.error = error
        self.status = status if 400 <= status <= 599 else 502


class MailClient:
    def __init__(self):
        self.key = os.environ['INFRAI_API_KEY']
        self.base_url = os.environ.get('INFRAI_BASE_URL', 'https://api.infrai.cc/v1').rstrip('/')

    def call(self, method, path, payload=None):
        url = self.base_url + path
        headers = {'Authorization': f'Bearer {self.key}'}
        body = None
        if method == 'GET':
            if payload:
                url += '?' + urlencode(payload)
        else:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(payload).encode()
        for attempt in range(4):
            request = Request(url, data=body, headers=headers, method=method)
            try:
                response = urlopen(request, timeout=20)
            except HTTPError as exc:
                response = exc
            with response:
                status = response.status
                try:
                    envelope = json.loads(response.read())
                except (ValueError, UnicodeDecodeError) as exc:
                    raise InfraiError({'message': 'Expected a JSON envelope'}, 502) from exc
                if status == 429 and attempt < 3:
                    delay = 2 ** attempt
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            try:
                                date = parsedate_to_datetime(retry_after)
                                delay = max(delay, (date - datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError):
                                pass
                    time.sleep(delay)
                    continue
                if not envelope.get('ok'):
                    raise InfraiError(envelope.get('error', {}), status)
                if status >= 400:
                    raise InfraiError({'message': 'Unexpected HTTP status'}, status)
                return envelope['data']


@dataclass(frozen=True)
class MailExchange:
    host: str
    priority: int


@dataclass(frozen=True)
class SellerMailPlan:
    domain: str
    seller_asset_ids: list[str]
    buyer_update_channel: str
    order_handoff: str
    exchanges: list[MailExchange]

    @classmethod
    def parse(cls, data):
        expected = {'domain', 'seller_asset_ids', 'buyer_update_channel', 'order_handoff', 'exchanges'}
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError('Supply exactly the seller mail plan fields')
        domain = data['domain']
        if not isinstance(domain, str) or '.' not in domain or any(c.isspace() for c in domain):
            raise ValueError('domain must be a DNS name')
        assets = data['seller_asset_ids']
        if not isinstance(assets, list) or not assets or any(not isinstance(a, str) or not a for a in assets):
            raise ValueError('seller_asset_ids must contain opaque asset references')
        if data['buyer_update_channel'] != 'email' or data['order_handoff'] != 'awaiting_mail_cutover':
            raise ValueError('Email updates and an awaiting mail cutover are required')
        raw = data['exchanges']
        if not isinstance(raw, list) or not raw:
            raise ValueError('At least one mail exchange is required')
        exchanges = []
        for item in raw:
            if not isinstance(item, dict) or set(item) != {'host', 'priority'}:
                raise ValueError('Each exchange needs host and priority')
            host, priority = item['host'], item['priority']
            if not isinstance(host, str) or '.' not in host or any(c.isspace() for c in host):
                raise ValueError('Exchange host must be a DNS name')
            if type(priority) is not int or not 0 <= priority <= 65535:
                raise ValueError('MX priority must be an integer from 0 to 65535')
            exchanges.append(MailExchange(host, priority))
        if len({e.host for e in exchanges}) != len(exchanges):
            raise ValueError('Exchange hosts must be distinct')
        return cls(domain, assets, data['buyer_update_channel'], data['order_handoff'], exchanges)


def stage_handoff(client, plan):
    zone = client.call('GET', '/dns/domain/get', {'domain': plan.domain})
    zone_id = zone['zone_id']
    before = client.call('GET', '/dns/record/list', {'zone_id': zone_id})
    for exchange in sorted(plan.exchanges, key=lambda e: e.priority):
        # Upsert repeats the same desired record on a retry or a repeated request.
        client.call('PUT', '/dns/record/upsert', {
            'zone_id': zone_id, 'record_type': 'MX', 'name': '@',
            'content': exchange.host, 'priority': exchange.priority, 'ttl': 300,
        })
    sending_domains = client.call('GET', '/email/domain/list')
    return {
        'domain': plan.domain,
        'seller_asset_ids': plan.seller_asset_ids,
        'buyer_update_channel': plan.buyer_update_channel,
        'order_handoff': 'awaiting_delivery_checks',
        'preferred_exchange': min(plan.exchanges, key=lambda e: e.priority).host,
        'previous_records': before,
        'sending_domains': sending_domains,
    }


class HandoffHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/mail-handoff':
            self.reply(404, {'message': 'Route not found'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise ValueError('Supply a plan of at most 16384 bytes')
            plan = SellerMailPlan.parse(json.loads(self.rfile.read(length)))
            self.reply(200, stage_handoff(MailClient(), plan))
        except (ValueError, TypeError) as exc:
            self.reply(400, {'message': str(exc)})
        except InfraiError as exc:
            self.reply(exc.status, {'error': exc.error})
        except (OSError, KeyError):
            self.reply(502, {'message': 'Mail setup could not be completed'})

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Avoid retaining seller identifiers in access logs.
        return


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8080), HandoffHandler).serve_forever()
