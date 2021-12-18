import sys

from rotkehlchen.usage_analytics import create_usage_analytics
from rotkehlchen.utils.misc import get_system_spec


def test_create_usage_analytics(data_dir):
    analytics = create_usage_analytics(data_dir)

    assert 'system_os' in analytics
    assert 'system_release' in analytics
    assert 'system_version' in analytics
    assert analytics['rotki_version'] == get_system_spec()['rotkehlchen']
    if sys.platform != 'darwin':
        assert analytics['city'] == 'unknown'
    else:
        assert analytics['country'] is not None
        assert analytics['city'] is not None
