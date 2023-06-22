import logging
from typing import TYPE_CHECKING, Any, Callable, Optional

from web3.types import BlockIdentifier

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool
from rotkehlchen.chain.ethereum.interfaces.ammswap.utils import decode_result
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_DECODING_OUTPUT, DecodingOutput
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price
from rotkehlchen.utils.misc import get_chunks

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def uniswap_lp_token_balances(
        userdb: 'DBHandler',
        address: ChecksumEvmAddress,
        ethereum: 'EthereumInquirer',
        lp_addresses: list[ChecksumEvmAddress],
) -> list[LiquidityPool]:
    """Query uniswap token balances from ethereum chain

    The number of addresses to query in one call depends a lot on the node used.
    With an infura node we saw the following:
    500 addresses per call took on average 43 seconds for 20450 addresses
    2000 addresses per call took on average 36 seconds for 20450 addresses
    4000 addresses per call took on average 32.6 seconds for 20450 addresses
    5000 addresses timed out a few times
    """
    zerion_contract = EvmContract(
        address=ZERION_ADAPTER_ADDRESS,
        abi=ethereum.contracts.abi('ZERION_ADAPTER'),
        deployed_block=1586199170,
    )
    if (own_node_info := ethereum.get_own_node_info()) is not None:
        chunks = list(get_chunks(lp_addresses, n=4000))
        call_order = [WeightedNode(node_info=own_node_info, weight=ONE, active=True)]
    else:
        chunks = list(get_chunks(lp_addresses, n=700))
        call_order = ethereum.default_call_order(skip_etherscan=True)

    balances = []
    for chunk in chunks:
        result = zerion_contract.call(
            node_inquirer=ethereum,
            method_name='getAdapterBalance',
            arguments=[address, '0x4EdBac5c8cb92878DD3fd165e43bBb8472f34c3f', chunk],
            call_order=call_order,
        )

        for entry in result[1]:
            balances.append(decode_result(userdb, entry))

    return balances


def find_uniswap_v2_lp_price(
        ethereum: 'EthereumInquirer',
        token: EvmToken,
        token_price_func: Callable,
        token_price_func_args: list[Any],
        block_identifier: BlockIdentifier,
) -> Optional[Price]:
    """
    Calculate the price for a uniswap v2 LP token. That is
    value = (Total value of liquidity pool) / (Current suply of LP tokens)
    We need:
    - Price of token 0
    - Price of token 1
    - Pooled amount of token 0
    - Pooled amount of token 1
    - Total supply of of pool token
    """
    address = token.evm_address
    abi = ethereum.contracts.abi('UNISWAP_V2_LP')
    contract = EvmContract(address=address, abi=abi, deployed_block=0)
    methods = ['token0', 'token1', 'totalSupply', 'getReserves', 'decimals']
    multicall_method = ethereum.multicall_2  # choose which multicall to use
    if isinstance(block_identifier, int):
        if block_identifier <= 7929876:
            log.error(
                f'No multicall contract at the block {block_identifier}. Uniswap v2 LP '
                f'query failed. Should implement direct queries',
            )
            return None

        if block_identifier <= 12336033:
            multicall_method = ethereum.multicall

    try:
        output = multicall_method(
            require_success=True,
            calls=[(address, contract.encode(method_name=method)) for method in methods],
            block_identifier=block_identifier,
        )
    except RemoteError as e:
        log.error(
            f'Remote error calling multicall contract for uniswap v2 lp '
            f'token {token.evm_address} properties: {e!s}',
        )
        return None

    # decode output
    decoded = []
    for (method_output, method_name) in zip(output, methods):
        call_success = True
        if multicall_method == ethereum.multicall_2:
            call_success = method_output[0]
            call_result = method_output[1]
        else:
            call_result = method_output  # type: ignore
        if call_success and len(call_result) != 0:
            decoded_method = contract.decode(call_result, method_name)
            if len(decoded_method) == 1:
                # https://github.com/PyCQA/pylint/issues/4739
                decoded.append(decoded_method[0])
            else:
                decoded.append(decoded_method)
        else:
            log.debug(
                f'Multicall to Uniswap V2 LP failed to fetch field {method_name} '
                f'for token {token.evm_address}',
            )
            return None

    try:
        token0 = EvmToken(ethaddress_to_identifier(decoded[0]))
        token1 = EvmToken(ethaddress_to_identifier(decoded[1]))
    except (UnknownAsset, WrongAssetType):
        log.debug(f'Unknown assets while querying uniswap v2 lp price {decoded[0]} {decoded[1]}')
        return None

    try:
        token0_supply = FVal(decoded[3][0] * 10**-token0.decimals)
        token1_supply = FVal(decoded[3][1] * 10**-token1.decimals)
        total_supply = FVal(decoded[2] * 10 ** - decoded[4])
    except ValueError as e:
        log.debug(
            f'Failed to deserialize token amounts for token {address} '
            f'with values {decoded!s}. f{e!s}',
        )
        return None
    token0_price = token_price_func(token0, *token_price_func_args)
    token1_price = token_price_func(token1, *token_price_func_args)

    if ZERO in (token0_price, token1_price):
        log.debug(
            f'Couldnt retrieve non zero price information for tokens {token0}, {token1} '
            f'with result {token0_price}, {token1_price}',
        )
    numerator = token0_supply * token0_price + token1_supply * token1_price
    share_value = numerator / total_supply
    return Price(share_value)


def decode_basic_uniswap_info(
        amount_sent: int,
        amount_received: int,
        decoded_events: list['EvmEvent'],
        counterparty: str,
        notify_user: Callable[['EvmEvent', str], None],
) -> DecodingOutput:
    """
    Check last three events and if they are related to the swap, label them as such.
    We check three events because potential events are: spend, (optionally) approval, receive.
    Earlier events are not related to the current swap.
    """
    spend_event, approval_event, receive_event = None, None, None
    for event in reversed(decoded_events):
        try:
            crypto_asset = event.asset.resolve_to_crypto_asset()
        except (UnknownAsset, WrongAssetType):
            notify_user(event, counterparty)
            return DEFAULT_DECODING_OUTPUT

        if (
            event.event_type == HistoryEventType.INFORMATIONAL and
            event.event_subtype == HistoryEventSubType.APPROVE and
            approval_event is None
        ):
            approval_event = event
        elif (
            event.balance.amount == asset_normalized_value(amount=amount_sent, asset=crypto_asset) and  # noqa: E501
            event.event_type == HistoryEventType.SPEND and
            # don't touch ETH since there may be multiple ETH transfers
            # and they are better handled by the aggregator decoder.
            event.asset != A_ETH and
            spend_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = counterparty
            event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in {counterparty}'  # noqa: E501
            spend_event = event
        elif (
            event.balance.amount == asset_normalized_value(amount=amount_received, asset=crypto_asset) and  # noqa: E501
            event.event_type == HistoryEventType.RECEIVE and
            event.asset != A_ETH and
            receive_event is None
        ):
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = counterparty
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} as a result of a {counterparty} swap'  # noqa: E501
            receive_event = event
        elif (
            event.counterparty in {CPT_UNISWAP_V2, CPT_UNISWAP_V3} and
            event.event_type == HistoryEventType.TRADE
        ):
            # The structure of swaps is the following:
            # 1.1 Optional approval event
            # 1.2 Optional spend event
            # 1.3 Optional receive event
            # 1.4 SWAP_SIGNATURE event
            # 2.1 Optional approval event
            # 2.2 Optional spend event
            # 2.3 Optional receive event
            # 2.4 SWAP_SIGNATURE event
            # etc.
            # So if we are at SWAP_SIGNATURE № 2 then all events that are before SWAP_SIGNATURE № 1
            # should have already been decoded, have counterparty set and have type Trade.
            break
        else:
            # If what described in the comment above is not met then it is an error.
            log.debug(
                f'Found unexpected event {event.serialize()} during decoding a uniswap swap in '
                f'transaction {event.tx_hash.hex()}. Either uniswap router or an aggregator was '
                f'used and decoding needs to happen in the aggregator-specific decoder.',
            )
            break

    # Make sure that the approval event is NOT between the spend and receive events.
    maybe_reshuffle_events(
        ordered_events=[approval_event, spend_event, receive_event],
        events_list=decoded_events,
    )
    return DEFAULT_DECODING_OUTPUT
