import pytest
from mail_handoff import SellerMailPlan, stage_handoff


def seller_plan():
    return {
        'domain': 'market.example.org', 'seller_asset_ids': ['asset_42'],
        'buyer_update_channel': 'email', 'order_handoff': 'awaiting_mail_cutover',
        'exchanges': [{'host': 'backup.mail.example.org', 'priority': 20},
                      {'host': 'primary.mail.example.org', 'priority': 10}],
    }


class Provider:
    def __init__(self):
        self.calls = []

    def call(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == '/dns/domain/get':
            return {'zone_id': 'zone_42'}
        return []


def test_priority_and_delivery_hold():
    provider = Provider()
    result = stage_handoff(provider, SellerMailPlan.parse(seller_plan()))
    assert result['preferred_exchange'] == 'primary.mail.example.org'
    assert result['order_handoff'] == 'awaiting_delivery_checks'
    assert result['seller_asset_ids'] == ['asset_42']
    writes = [call for call in provider.calls if call[0] == 'PUT']
    assert [call[2]['priority'] for call in writes] == [10, 20]
    assert all(call[2]['zone_id'] == 'zone_42' for call in writes)
    assert provider.calls[-1] == ('GET', '/email/domain/list', None)


def test_rejects_handoff_already_released():
    data = seller_plan()
    data['order_handoff'] = 'released'
    with pytest.raises(ValueError, match='awaiting mail cutover'):
        SellerMailPlan.parse(data)
