from collections import defaultdict
from typing import DefaultDict, Dict, List, NamedTuple

from rotkehlchen.chain.ethereum.manager import EthereumManager, decode_event_data
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.misc import ts_now

ETH2_DEPOSIT = EthereumConstants().contract('ETH2_DEPOSIT')
ETH2_DEPLOYED_TS = 1602667372

EVENT_ABI = [x for x in ETH2_DEPOSIT.abi if x['type'] == 'event'][0]


class Eth2Deposit(NamedTuple):
    from_address: ChecksumEthAddress
    pubkey: str  # hexstring
    withdrawal_credentials: str  # hexstring
    amount: int  # Saved in gwei of ETH
    validator_index: int  # the validator index
    tx_hash: str  # the transaction hash
    log_index: int


class Eth2DepositResult(NamedTuple):
    deposits: List[Eth2Deposit]
    totals: Dict[ChecksumEthAddress, FVal]


def get_eth2_staked_amount(
        ethereum: 'EthereumManager',
        addresses: List[ChecksumEthAddress],
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

    last_event = events[-1]
    decoded_data = decode_event_data(last_event['data'], EVENT_ABI)
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
                deposits.append(Eth2Deposit(
                    from_address=transaction.from_address,
                    pubkey='0x' + decoded_data[0].hex(),
                    withdrawal_credentials='0x' + decoded_data[1].hex(),
                    amount=amount,
                    validator_index=int.from_bytes(decoded_data[4], byteorder='little'),
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                ))
                totals[transaction.from_address] += amount
                break

    return Eth2DepositResult(
        deposits=deposits,
        totals={k: FVal(v) / 10 ** 9 for k, v in totals.items()},
    )
