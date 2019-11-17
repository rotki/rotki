from rotkehlchen.usage_analytics import create_usage_analytics
from rotkehlchen.utils.misc import get_system_spec


def test_create_usage_analytics():
    analytics = create_usage_analytics()

    assert 'system_os' in analytics
    assert 'system_release' in analytics
    assert 'system_version' in analytics
    assert analytics['rotki_version'] == get_system_spec()['rotkehlchen']
    assert analytics['country'] != 'unknown'
    assert analytics['city'] != 'unknown'
