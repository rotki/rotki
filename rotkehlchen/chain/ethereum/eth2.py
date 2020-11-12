from collections import defaultdict
from typing import DefaultDict, Dict, List, NamedTuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.manager import EthereumManager, decode_event_data
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

ETH2_DEPOSIT = EthereumConstants().contract('ETH2_DEPOSIT')
ETH2_DEPLOYED_TS = 1602667372

EVENT_ABI = [x for x in ETH2_DEPOSIT.abi if x['type'] == 'event'][0]


class Eth2Deposit(NamedTuple):
    from_address: ChecksumEthAddress
    pubkey: str  # hexstring
    withdrawal_credentials: str  # hexstring
    value: Balance
    validator_index: int  # the validator index
    tx_hash: str  # the transaction hash
    log_index: int


class Eth2DepositResult(NamedTuple):
    deposits: List[Eth2Deposit]
    totals: Dict[ChecksumEthAddress, Balance]


def get_eth2_staked_amount(
        ethereum: EthereumManager,
        addresses: List[ChecksumEthAddress],
        has_premium: bool,
        msg_aggregator: MessagesAggregator,
) -> Eth2DepositResult:
    events = ETH2_DEPOSIT.get_logs(
        ethereum=ethereum,
        event_name='DepositEvent',
        argument_filters={},
        from_block=ETH2_DEPOSIT.deployed_block,
        to_block='latest',
    )
    transactions = ethereum.transactions.query(
        addresses=addresses,
        from_ts=ETH2_DEPLOYED_TS,
        to_ts=ts_now(),
        with_limit=False,
        recent_first=False,
    )
    totals: DefaultDict[ChecksumEthAddress, int] = defaultdict(int)
    deposits = []

    for transaction in transactions:
        if transaction.to_address != ETH2_DEPOSIT.address:
            continue

        tx_hash = '0x' + transaction.tx_hash.hex()
        for event in events:
            # Now find the corresponding event. If no event is found the transaction
            # probably failed or was something other than a deposit
            if event['transactionHash'] == tx_hash:
                decoded_data = decode_event_data(event['data'], EVENT_ABI)
                amount = int.from_bytes(decoded_data[2], byteorder='little')
                usd_price = ZERO
                if has_premium:  # won't show this to non-premium so don't bother
                    usd_price = query_usd_price_zero_if_error(
                        asset=A_ETH,
                        time=transaction.timestamp,
                        location='Eth2 staking query',
                        msg_aggregator=msg_aggregator,
                    )
                normalized_amount = FVal(amount) / 10 ** 9
                deposits.append(Eth2Deposit(
                    from_address=transaction.from_address,
                    pubkey='0x' + decoded_data[0].hex(),
                    withdrawal_credentials='0x' + decoded_data[1].hex(),
                    value=Balance(normalized_amount, usd_price * normalized_amount),
                    validator_index=int.from_bytes(decoded_data[4], byteorder='little'),
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                ))
                totals[transaction.from_address] += amount
                break

    current_usd_price = Inquirer().find_usd_price(A_ETH)
    normalized_totals = {}
    for k, v in totals.items():
        normalized_amount = FVal(v) / 10 ** 9
        normalized_totals[k] = Balance(normalized_amount, normalized_amount * current_usd_price)

    return Eth2DepositResult(
        deposits=deposits,
        totals=normalized_totals,
    )
