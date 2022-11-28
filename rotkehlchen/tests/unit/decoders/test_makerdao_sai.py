import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.makerdao.sai.constants import CPT_SAI
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_SAI, A_WETH
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTransaction, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

A_PETH = Asset('eip155:1/erc20:0xf53AD2c6851052A81B42133467480961B2321C09')


@pytest.mark.parametrize('ethereum_accounts', [['0x01349510117dC9081937794939552463F5616dfb']])  # noqa: E501
def test_makerdao_sai_new_cdp(ethereum_transaction_decoder):
    """
    Data for cdp creation is taken from
    https://etherscan.io/tx/0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0
    """
    tx_hex = '0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=evmhash,
        timestamp=1513958719,
        block_number=4777541,
        from_address='0x01349510117dC9081937794939552463F5616dfb',
        to_address='0x448a5065aeBB8E423F0896E6c5D525C040f59af3',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xfcfff16f'),
        nonce=1021,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=21,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004fcfff16f'),  # noqa: E501
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xfcfff16f00000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000001349510117dc9081937794939552463f5616dfb'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=22,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000083'),  # noqa: E501
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x89b8893b806db50897c8e2362c71571cfaeb9761ee40727f683f1793cda9df16'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000001349510117dc9081937794939552463f5616dfb'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        events = ethereum_transaction_decoder.decode_transaction(
            write_cursor=cursor,
            transaction=transaction,
            tx_receipt=receipt,
        )

    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=0,
            timestamp=1513958719000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.00393701451)),
            location_label='0x01349510117dC9081937794939552463F5616dfb',
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(tx_hex),
            sequence_index=23,
            timestamp=1513958719000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x01349510117dC9081937794939552463F5616dfb',
            notes='Create CDP 131',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xD5684Ae2a4a722B8B31168AcF6fF3477617073ea']])  # noqa: E501
def test_makerdao_sai_borrow_sai(database, ethereum_inquirer):
    """
    Data for sai borrow is taken from
    https://etherscan.io/tx/0x4aed2d2fe5712a5b65cb6866c51ae672a53e39fa25f343e4c6ebaa8eae21de80
    """
    tx_hex = '0x4aed2d2fe5712a5b65cb6866c51ae672a53e39fa25f343e4c6ebaa8eae21de80'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513957014000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00508884')),
            location_label='0xD5684Ae2a4a722B8B31168AcF6fF3477617073ea',
            notes='Burned 0.00508884 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=45,
            timestamp=1513957014000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            balance=Balance(amount=FVal('1000')),
            location_label='0xD5684Ae2a4a722B8B31168AcF6fF3477617073ea',
            notes='Borrow 1000 SAI from CDP 118',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x277E4b7F5DaB01C8E4389B930d3Bd1c9690CE1E8']])  # noqa: E501
def test_makerdao_sai_close_cdp(database, ethereum_inquirer):
    """
    Data for cdp closure is taken from
    https://etherscan.io/tx/0xc851e18df6dec02ac2efff000298001e839dde3d6e99d25d1d98ecb0d390c9a6
    """
    tx_hex = '0xc851e18df6dec02ac2efff000298001e839dde3d6e99d25d1d98ecb0d390c9a6'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513954042000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0037108')),
            location_label='0x277E4b7F5DaB01C8E4389B930d3Bd1c9690CE1E8',
            notes='Burned 0.0037108 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=33,
            timestamp=1513954042000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x277E4b7F5DaB01C8E4389B930d3Bd1c9690CE1E8',
            notes='Close CDP 101',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=36,
            timestamp=1513954042000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_PETH,
            balance=Balance(amount=FVal('10.916302181726036571')),
            location_label='0x277E4b7F5DaB01C8E4389B930d3Bd1c9690CE1E8',
            notes='Decrease CDP collateral by 10.916302181726036571 PETH',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xB4be361f092D9d5edFE8606fD53260eCED3b776E']])  # noqa: E501
def test_makerdao_sai_repay_sai(database, ethereum_inquirer):
    """
    Data for repayment of sai loan is taken from
    https://etherscan.io/tx/0xe964cb12f4bbfa1ba4b6db8464eb3f2d4234ceafb0b5ec5f4a2188b0264bab27
    """
    tx_hex = '0xe964cb12f4bbfa1ba4b6db8464eb3f2d4234ceafb0b5ec5f4a2188b0264bab27'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513958625000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00515524')),
            location_label='0xB4be361f092D9d5edFE8606fD53260eCED3b776E',
            notes='Burned 0.00515524 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=21,
            timestamp=1513958625000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
            balance=Balance(amount=FVal('100')),
            location_label='0xB4be361f092D9d5edFE8606fD53260eCED3b776E',
            notes='Repay 100 SAI to CDP 103',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=29,
            timestamp=1513958625000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
            balance=Balance(amount=FVal('0.000002135014342194')),
            location_label='0xB4be361f092D9d5edFE8606fD53260eCED3b776E',
            notes='Send 0.000002135014342194 MKR from 0xB4be361f092D9d5edFE8606fD53260eCED3b776E to 0x69076e44a9C70a67D5b79d95795Aba299083c275',  # noqa: E501
            counterparty='0x69076e44a9C70a67D5b79d95795Aba299083c275',
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89']])  # noqa: E501
def test_makerdao_sai_deposit_weth(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af
    """
    tx_hex = '0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513955555000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0037036')),
            location_label='0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89',
            notes='Burned 0.0037036 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=4,
            timestamp=1513955555000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal('90.02006235538821461')),
            location_label='0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89',
            notes='Supply 90.02006235538821461 WETH to Sai vault',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=5,
            timestamp=1513955555000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            balance=Balance(amount=FVal('90')),
            location_label='0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89',
            notes='Receive 90 PETH from Sai Vault',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89']])  # noqa: E501
def test_makerdao_sai_deposit_peth(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0xc8bd1d3556706e659e907b515185ce7e139777229f257e79a6b0b26e2a536e2c
    """
    tx_hex = '0xc8bd1d3556706e659e907b515185ce7e139777229f257e79a6b0b26e2a536e2c'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513955635000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00138008')),
            location_label='0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89',
            notes='Burned 0.00138008 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=32,
            timestamp=1513955635000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_PETH,
            balance=Balance(amount=FVal('90')),
            notes='Increase CDP collateral by 90 PETH',
            location_label='0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x005e157Ae9708c55dB34e3e936CD3ebEE7265Fbc']])  # noqa: E501
def test_makerdao_sai_liquidation(database, ethereum_inquirer):
    """
    Data for liquidation is taken from
    https://etherscan.io/tx/0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba
    """
    tx_hex = '0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1513952436000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00478524')),
            location_label='0x005e157Ae9708c55dB34e3e936CD3ebEE7265Fbc',
            notes='Burned 0.00478524 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=24,
            timestamp=1513952436000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=A_PETH,
            balance=Balance(amount=FVal('0.041523220093200014')),
            location_label='0x005e157Ae9708c55dB34e3e936CD3ebEE7265Fbc',
            notes='Liquidate 0.041523220093200014 PETH for CDP 80',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xb0e83C2D71A991017e0116d58c5765Abc57384af']])  # noqa: E501
def test_makerdao_sai_collateral_removal(database, ethereum_inquirer):
    """
    Data for abstracted collateral removal is taken from
    https://etherscan.io/tx/0x8c95ecc864db038a42c6cd9d6cab17e12f1f56332b140d903948a69d8b9e4308
    """
    tx_hex = '0x8c95ecc864db038a42c6cd9d6cab17e12f1f56332b140d903948a69d8b9e4308'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1514047441000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.003528768')),
            location_label='0xb0e83C2D71A991017e0116d58c5765Abc57384af',
            notes='Burned 0.003528768 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=33,
            timestamp=1514047441000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_PETH,
            balance=Balance(amount=FVal(3)),
            location_label='0xb0e83C2D71A991017e0116d58c5765Abc57384af',
            notes='Decrease CDP collateral by 3 PETH',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x153685A03c2025b6825AE164e2ff5681EE487667']])  # noqa: E501
def test_makerdao_sai_underlying_collateral_removal(database, ethereum_inquirer):
    """
    Data for underlying collateral removal is taken from
    https://etherscan.io/tx/0x6467c080d5c0af9756681a368417fb802206d832f51d20b19c08d7c46a4216b0
    """
    tx_hex = '0x6467c080d5c0af9756681a368417fb802206d832f51d20b19c08d7c46a4216b0'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1663338359000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001070825480009344')),
            location_label='0x153685A03c2025b6825AE164e2ff5681EE487667',
            notes='Burned 0.001070825480009344 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=359,
            timestamp=1663338359000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal('0.065061280268047522')),
            location_label='0x153685A03c2025b6825AE164e2ff5681EE487667',
            notes='Withdraw 0.065061280268047522 WETH from Sai vault',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x6D1723Af1727d857964d12f19ed92E63736c8dA2', '0x720972Dc53741a72fEE22400828122836640a74b']])  # noqa: E501
def test_makerdao_sai_proxy_interaction(database, ethereum_inquirer):
    """
    Data for proxy interaction is taken from
    https://etherscan.io/tx/0xf4203a8b507b0b382903bd8d35dcff29aea98de76b89f745d94705d54b67646f
    """
    tx_hex = '0xf4203a8b507b0b382903bd8d35dcff29aea98de76b89f745d94705d54b67646f'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 6
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002845233')),
            location_label='0x6D1723Af1727d857964d12f19ed92E63736c8dA2',
            notes='Burned 0.002845233 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x526af336D614adE5cc252A407062B8861aF998F5',
            notes='Create CDP 66482',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=59,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPLOY,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x6D1723Af1727d857964d12f19ed92E63736c8dA2',
            notes='Create DSR proxy 0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B with owner 0x6D1723Af1727d857964d12f19ed92E63736c8dA2',  # noqa: E501
            counterparty='0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=62,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.006')),
            location_label='0x6D1723Af1727d857964d12f19ed92E63736c8dA2',
            notes='Supply 0.006 ETH to Sai vault',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=66,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            balance=Balance(amount=FVal('0.005751993711424072')),
            location_label='0x526af336D614adE5cc252A407062B8861aF998F5',
            notes='Receive 0.005751993711424072 PETH from Sai Vault',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=77,
            timestamp=1565146195000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.06')),
            location_label='0x6D1723Af1727d857964d12f19ed92E63736c8dA2',
            notes='Borrow 0.06 SAI from CDP 66482',
            counterparty=CPT_SAI,
            extra_data={'cdp_id': 66482},
        ),
    ]
    assert events == expected_events

    # sai repayment
    # https://etherscan.io/tx/0x96c8d55100427de5edbf33fb41623b42966f7ae7273b55edaf6f7a5178d93594
    tx_hex = '0x96c8d55100427de5edbf33fb41623b42966f7ae7273b55edaf6f7a5178d93594'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1588030530000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00043181')),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Burned 0.00043181 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=85,
            timestamp=1588030530000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_SAI,
            balance=Balance(amount=FVal(2)),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Repay 2 SAI to CDP 155361',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events

    # proxy interaction
    # https://etherscan.io/tx/0x3c85624d0103f946e02c76bf4f801e72e6a753679601611c13ba2d736db1c004
    tx_hex = '0x3c85624d0103f946e02c76bf4f801e72e6a753679601611c13ba2d736db1c004'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 5
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1588035170000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000937104')),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Burned 0.000937104 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1588035170000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Create CDP 155362',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=101,
            timestamp=1588035170000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.08')),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Supply 0.08 ETH to Sai vault',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=106,
            timestamp=1588035170000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            balance=Balance(amount=FVal('0.076059582212675065')),
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Receive 0.076059582212675065 PETH from Sai Vault',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=117,
            timestamp=1588035170000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            balance=Balance(amount=FVal(5)),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Borrow 5 SAI from CDP 155362',
            counterparty=CPT_SAI,
            extra_data={'cdp_id': 155362},
        ),
    ]
    assert events == expected_events

    # another proxy interaction
    # https://etherscan.io/tx/0x4e569aa1f23dc771f1c9ad05ab7cdb0af2607358b166a8137b702f81b88e37b9
    tx_hex = '0x4e569aa1f23dc771f1c9ad05ab7cdb0af2607358b166a8137b702f81b88e37b9'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1588030595000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000571796')),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Burned 0.000571796 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1588030595000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.030000004449579884')),
            location_label='0x720972Dc53741a72fEE22400828122836640a74b',
            notes='Withdraw 0.030000004449579884 ETH from CDP 155361',
            counterparty=CPT_SAI,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=90,
            timestamp=1588030595000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Close CDP 155361',
            counterparty=CPT_SAI,
        ),
    ]
    assert events == expected_events
