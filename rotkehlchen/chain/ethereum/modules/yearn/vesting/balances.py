import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address

from .constants import CPT_YEARN_VESTING, VESTING_ESCROW_ABI, VYPER_DONATION_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnVestingBalances(ProtocolWithBalance):
    """Query tokens still held by yearn vesting escrows for tracked recipients.

    The escrows are discovered from the already decoded vesting events (either the
    funding deposit or a claim), and the remaining balance (locked + unclaimed) is
    the escrow's token balance since the escrows only ever hold the vesting token.
    """

    def __init__(
            self,
            evm_inquirer: EthereumInquirer,
            tx_decoder: EthereumTransactionDecoder,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_YEARN_VESTING,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL)},  # noqa: E501
        )

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses_to_events = self.addresses_with_activity(event_types={
            (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_TO_PROTOCOL),
            (HistoryEventType.WITHDRAWAL, HistoryEventSubType.WITHDRAW_FROM_PROTOCOL),
        })
        escrow_to_token: dict[ChecksumEvmAddress, EvmToken] = {}
        for events in addresses_to_events.values():
            for event in events:
                if event.address is not None and event.address != VYPER_DONATION_ADDRESS:
                    escrow_to_token[event.address] = event.asset.resolve_to_evm_token()

        if len(escrow_to_token) == 0:
            return balances

        with self.event_db.db.conn.read_ctx() as cursor:
            tracked_accounts = self.event_db.db.get_blockchain_accounts(cursor).get(
                blockchain=self.evm_inquirer.blockchain,
            )

        escrow_contract = EvmContract(  # only used to encode/decode the escrow calls
            address=(escrows := list(escrow_to_token))[0],
            abi=VESTING_ESCROW_ABI,
            deployed_block=0,
        )
        erc20_contract = EvmContract(  # same here, the encoded call carries the token address
            address=escrows[0],
            abi=self.evm_inquirer.contracts.abi('ERC20_TOKEN'),
            deployed_block=0,
        )
        try:
            results = self.evm_inquirer.multicall(
                calls=[(escrow, escrow_contract.encode(method_name='recipient')) for escrow in escrows] +  # noqa: E501
                [(
                    escrow_to_token[escrow].evm_address,
                    erc20_contract.encode(method_name='balanceOf', arguments=[escrow]),
                ) for escrow in escrows],
            )
        except RemoteError as e:
            log.error('Failed to query yearn vesting escrow balances via multicall due to %s', e)
            return balances

        amounts = []
        for idx, escrow in enumerate(escrows):
            recipient = deserialize_evm_address(escrow_contract.decode(
                result=results[idx],
                method_name='recipient',
            )[0])
            if recipient not in tracked_accounts:
                continue  # the tracked address only funded the escrow of an untracked recipient

            token = escrow_to_token[escrow]
            if (amount := token_normalized_value(
                token_amount=int.from_bytes(results[len(escrows) + idx]),
                token=token,
            )) == 0:
                continue  # fully claimed or revoked escrow

            amounts.append((recipient, token, amount))

        self._add_priced_balances(balances=balances, amounts=amounts)
        return balances
