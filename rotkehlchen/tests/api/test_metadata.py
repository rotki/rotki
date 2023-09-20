from typing import TYPE_CHECKING

import requests

from rotkehlchen.chain.ethereum.airdrops import AIRDROPS
from rotkehlchen.chain.ethereum.defi.protocols import DEFI_PROTOCOLS
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_metadata_endpoint(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that all the endpoints that query mappings or metadata from the backend work fine"""

    # testing the airdrops metadata endpoint
    airdrops_expected_result = [
        {
            'identifier': identifier,
            'name': airdrop.name,
            'icon': airdrop.icon,
        }
        for identifier, airdrop in AIRDROPS.items()
    ]
    airdrops_response = requests.get(
        api_url_for(rotkehlchen_api_server, 'airdropsmetadataresource'),
    )
    airdrops_result = assert_proper_response_with_result(airdrops_response)
    assert airdrops_result == airdrops_expected_result

    # testing the defi metadata endpoint
    defi_expected_result = [
        {
            'identifier': identifier,
            'name': protocol.name,
            'icon': protocol.icon,
        }
        for identifier, protocol in DEFI_PROTOCOLS.items()
    ]
    defi_response = requests.get(api_url_for(rotkehlchen_api_server, 'defimetadataresource'))
    defi_result = assert_proper_response_with_result(defi_response)
    assert defi_result == defi_expected_result

    # testing the supported chains endpoint
    supported_chains_response = requests.get(
        api_url_for(rotkehlchen_api_server, 'supportedchainsresource'),
    )
    supported_chains_result = assert_proper_response_with_result(supported_chains_response)
    for entry in SupportedBlockchain:
        for result_entry in supported_chains_result:
            if (
                entry.serialize() == result_entry['id'] and
                str(entry) == result_entry['name'] and
                entry.get_chain_type() == result_entry['type']
            ):
                if entry.is_evm() is True:
                    assert result_entry['evm_chain_name'] == entry.to_chain_id().to_name()
                assert result_entry['native_token'] == entry.get_native_token_id()

                break  # found
        else:  # internal for loop found nothing
            raise AssertionError(f'Did not find {entry!s} in the supported chains result')
