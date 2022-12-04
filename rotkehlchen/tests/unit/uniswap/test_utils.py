import json
from pathlib import Path

from rotkehlchen.utils.hashing import file_md5


def test_uniswapv2_lp_tokens_json_meta():
    """Test that uniswapv2_lp_tokens.json md5 matches and that if md5 changes since last
    time then version is also bumped"""
    last_meta = {'md5': '7f5030c986505a81ecc06f31614231d7', 'version': 3}
    data_dir = Path(__file__).resolve().parent.parent.parent.parent / 'data'
    data_md5 = file_md5(data_dir / 'uniswapv2_lp_tokens.json')

    with open(data_dir / 'uniswapv2_lp_tokens.meta') as f:
        saved_meta = json.loads(f.read())

    assert data_md5 == saved_meta['md5']

    if data_md5 != last_meta['md5']:
        msg = (
            'The md5 has changed since the last time uniswapv2_lp_tokens.json'
            '  was edited and the version has not been bumped',
        )
        assert saved_meta['version'] == last_meta['version'] + 1, msg
