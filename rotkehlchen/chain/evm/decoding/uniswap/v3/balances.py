import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.constants import ONE
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import UNISWAPV3_PROTOCOL, ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.misc import get_chunks

from .constants import (
    UNISWAP_V3_ARBISCAN_CHUNK_SIZE,
    UNISWAP_V3_CHUNK_SIZE,
    UNISWAP_V3_ERROR_MSG,
    UNISWAP_V3_ETHERSCAN_CHUNK_SIZE,
    UNISWAP_V3_NFT_MANAGER_ADDRESSES,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UniswapV3Balances(ProtocolWithBalance):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_UNISWAP_V3,
            deposit_event_types={(HistoryEventType.DEPLOY, HistoryEventSubType.NFT)},
        )
        self.uniswap_v3_nft_manager = self.evm_inquirer.contracts.contract(UNISWAP_V3_NFT_MANAGER_ADDRESSES[self.evm_inquirer.chain_id])  # noqa: E501

    def _get_lp_token_ids(self, address: ChecksumEvmAddress) -> list[int]:
        """Fetch token IDs of all the Uniswap V3 LP positions for the specified address.
        1. Use the NFT Positions contract to call the `balanceOf` method to get number of positions.
        2. Loop through from 0 to (positions - 1) using the index and address to call
        `tokenOfOwnerByIndex` method which gives the NFT ID that represents an LP position.
        3. Use the token ID gotten above to call the `positions` method to get the current state of the
        liquidity position.
        4. Return list of token IDs that have liquidity (open positions).

        May raise RemoteError if querying NFT manager contract fails.
        """  # noqa: E501
        nft_token_ids: list[int] = []
        try:
            amount_of_positions = self.uniswap_v3_nft_manager.call(
                node_inquirer=self.evm_inquirer,
                method_name='balanceOf',
                arguments=[address],
            )
        except RemoteError as e:
            raise RemoteError(
                f'Error calling nft manager contract to fetch LP positions count for '
                f'an address with properties: {e!s}',
            ) from e

        if amount_of_positions == 0:
            return nft_token_ids

        chunk_size, call_order = get_chunk_size_call_order(
            evm_inquirer=self.evm_inquirer,
            web3_node_chunk_size=UNISWAP_V3_CHUNK_SIZE,
            etherscan_chunk_size=UNISWAP_V3_ETHERSCAN_CHUNK_SIZE,
            arbiscan_chunksize=UNISWAP_V3_ARBISCAN_CHUNK_SIZE,
        )
        chunks = list(get_chunks(list(range(amount_of_positions)), n=chunk_size))
        for chunk in chunks:
            try:
                # Get tokens IDs from the Positions NFT contract using the user address and
                # the indexes i.e from 0 to (total number of user positions in the chunk - 1)
                tokens_ids_multicall = self.evm_inquirer.multicall_2(
                    require_success=False,
                    calls=[
                        (
                            self.uniswap_v3_nft_manager.address,
                            self.uniswap_v3_nft_manager.encode('tokenOfOwnerByIndex', [address, index]),  # noqa: E501
                        )
                        for index in chunk
                    ],
                    call_order=call_order,
                )
            except RemoteError as e:
                log.error(UNISWAP_V3_ERROR_MSG.format('nft contract token ids', str(e)))
                continue

            tokens_ids = [
                self.uniswap_v3_nft_manager.decode(
                    result=data[1],
                    method_name='tokenOfOwnerByIndex',
                    arguments=[address, index],
                )[0]
                for index, data in enumerate(tokens_ids_multicall) if data[0] is True
            ]

            try:  # Get the user liquidity position using the token ID retrieved.
                positions_multicall = self.evm_inquirer.multicall_2(
                    require_success=False,
                    calls=[
                        (
                            self.uniswap_v3_nft_manager.address,
                            self.uniswap_v3_nft_manager.encode('positions', [token_id]),
                        )
                        for token_id in tokens_ids
                    ],
                    call_order=call_order,
                )
            except RemoteError as e:
                log.error(UNISWAP_V3_ERROR_MSG.format('nft contract positions', str(e)))
                continue

            positions = [
                self.uniswap_v3_nft_manager.decode(
                    result=data[1],
                    method_name='positions',
                    arguments=[tokens_ids[index]],
                )
                for index, data in enumerate(positions_multicall) if data[0] is True
            ]

            for index, position in enumerate(positions):
                if position[7] != 0:  # only show positions with liquidity
                    nft_token_ids.append(tokens_ids[index])

        return nft_token_ids

    def query_balances(self) -> 'BalancesSheetType':
        """Query Uniswap V3 LP positions."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := self.addresses_with_deposits(products=None)) == 0:
            return balances

        for user_address in addresses_with_deposits:
            if len(collectible_ids := self._get_lp_token_ids(address=user_address)) == 0:
                continue

            for collectible_id in collectible_ids:
                token = get_or_create_evm_token(
                    userdb=self.evm_inquirer.database,
                    evm_address=self.uniswap_v3_nft_manager.address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=EvmTokenKind.ERC721,
                    collectible_id=str(collectible_id),
                    protocol=UNISWAPV3_PROTOCOL,
                )
                if (usd_value := Inquirer.find_usd_price(token)) == ZERO_PRICE:
                    continue

                balances[user_address].assets[token][self.counterparty] += Balance(
                    amount=ONE,
                    usd_value=usd_value,
                )

        return balances
