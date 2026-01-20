import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    get_or_create_evm_token,
    get_single_underlying_token,
    token_normalized_value,
    token_raw_value_decimals,
)
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.utils import get_vault_price
from rotkehlchen.chain.evm.utils import maybe_notify_cache_query_status
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import (
    InputError,
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.cache import (
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Price,
    Timestamp,
)
from rotkehlchen.utils.network import request_get

from .constants import BEEFY_CLM_VAULT_ABI, BEEFY_VAULT_ABI, CPT_BEEFY_FINANCE

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.inquirer import Inquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BEEFY_API_BASE_URL: Final = 'https://api.beefy.finance'


def _get_chain_name_for_api(chain: ChainID) -> str:
    """Convert a chain id to the name used in the Beefy API.
    See the names used in the response of https://api.beefy.finance/config
    """
    if chain == ChainID.POLYGON_POS:
        return 'polygon'
    elif chain == ChainID.ARBITRUM_ONE:
        return 'arbitrum'
    elif chain == ChainID.BINANCE_SC:
        return 'bsc'

    return chain.name.lower()


def _query_beefy_vaults_api(chain: ChainID) -> list[dict[str, Any]] | None:
    """Query Beefy finance API for all vaults on the given chain."""
    try:
        vaults: list[dict[str, Any]] = request_get(  # type: ignore  # we get a list of dicts from the api
            url=f'{BEEFY_API_BASE_URL}/vaults/all/{chain.value}',
        )
        vaults.extend(request_get(
            url=f'{BEEFY_API_BASE_URL}/boosts/{_get_chain_name_for_api(chain)}',
        ))
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve Beefy vaults for {chain} due to {e!s}')
        return None

    return vaults


def _process_beefy_vault(
        database: 'DBHandler',  # pylint: disable=unused-argument
        vault: dict[str, Any],
        evm_inquirer: 'EvmNodeInquirer',
) -> str | None:
    """Process Beefy finance vault data from the API and prepare cache entries.
    May raise:
    - DeserializationError
    - KeyError
    """
    if (vault_type := vault.get('type')) is None or vault_type in ('standard', 'gov'):
        # in boost (no type key), standard, and gov vaults the `tokenAddress` is the vault address,
        # so add it as the earned token's underlying token to be used when querying the price.
        if (raw_token_address := vault.get('tokenAddress')) is not None:
            underlying_token_address = deserialize_evm_address(raw_token_address)
        else:
            # For vaults without tokenAddress field (native token vaults like ETH, BNB, MATIC),
            # use the chain's wrapped native token as the underlying asset
            underlying_token_address = evm_inquirer.wrapped_native_token.evm_address
    elif vault_type == 'cowcentrated':
        # CLM vaults use the vault token itself and do not have underlying tokens.
        underlying_token_address = deserialize_evm_address(vault['earnContractAddress'])
    else:
        log.warning(f'Unknown Beefy vault type {vault_type} for vault {vault}')
        return None

    vault_token_address = deserialize_evm_address(vault['earnContractAddress'])
    is_legacy = '1' if vault.get('version') == 1 else '0'
    return f'{vault_token_address},{underlying_token_address},{is_legacy}'


def query_beefy_vaults(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query list of Beefy finance vaults and cache their token relationships."""
    if (vault_list := _query_beefy_vaults_api(evm_inquirer.chain_id)) is None:
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_update_cache_last_ts(
                write_cursor=write_cursor,
                cache_type=CacheType.BEEFY_VAULTS,
                key_parts=(str(evm_inquirer.chain_id.value),),
            )
        return

    cache_entries: list[str] = []
    last_notified_ts, total_entries = Timestamp(0), len(vault_list)
    for idx, vault in enumerate(vault_list):
        try:
            if (cache_entry := _process_beefy_vault(
                    database=evm_inquirer.database,
                    vault=vault,
                    evm_inquirer=evm_inquirer,
            )) is not None:
                cache_entries.append(cache_entry)
        except (DeserializationError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(
                f'Failed to cache Beefy vault data due to {error}. '
                f'Vault: {vault}. Skipping...',
            )

        last_notified_ts = maybe_notify_cache_query_status(
            msg_aggregator=evm_inquirer.database.msg_aggregator,
            last_notified_ts=last_notified_ts,
            protocol=CPT_BEEFY_FINANCE,
            chain=evm_inquirer.chain_id,
            processed=idx + 1,
            total=total_entries,
        )

    if len(cache_entries) == 0:
        return

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BEEFY_VAULTS, str(evm_inquirer.chain_id.value)),
            values=cache_entries,
        )


def _query_beefy_cow_token_price(
        inquirer: 'Inquirer',
        evm_inquirer: 'EvmNodeInquirer',
        vault_token: 'EvmToken',
) -> Price:
    """Gets the token price for a Beefy cow token (CLM vault).
    Queries the amounts of the underlying tokens that are equivalent to one vault token and
    combines their values to get the price.
    """
    clm_contract = EvmContract(
        address=vault_token.evm_address,
        abi=BEEFY_CLM_VAULT_ABI,
        deployed_block=0,  # not used here
    )
    try:
        call_output = evm_inquirer.multicall(calls=[
            (clm_contract.address, clm_contract.encode(method_name='wants')),
            (clm_contract.address, clm_contract.encode(
                method_name='previewWithdraw',
                arguments=[single_share_raw_amount := token_raw_value_decimals(
                    token_amount=ONE,
                    token_decimals=vault_token.decimals,
                )],
            )),
        ])
    except RemoteError as e:
        log.error(
            'Failed to query tokens and amounts for '
            f'Beefy vault {vault_token} on {evm_inquirer.chain_name} due to {e}',
        )
        return ZERO_PRICE

    if len(call_output) == 2:
        token_addresses = clm_contract.decode(result=call_output[0], method_name='wants')
        token_amounts = clm_contract.decode(
            result=call_output[1],
            method_name='previewWithdraw',
            arguments=[single_share_raw_amount],
        )
    else:  # this error case triggers the if below where the error will be logged.
        token_addresses, token_amounts = (), ()

    if (addr_len := len(token_addresses)) != len(token_amounts) or addr_len == 0:
        log.error(
            f'Unexpected number of tokens and amounts returned from '
            f'Beefy vault {vault_token} on {evm_inquirer.chain_name}',
        )
        return ZERO_PRICE

    usd_price = ZERO
    for underlying_token, amount in zip(token_addresses, token_amounts, strict=False):
        try:
            token = get_or_create_evm_token(
                userdb=evm_inquirer.database,
                evm_address=underlying_token,
                chain_id=evm_inquirer.chain_id,
                encounter=TokenEncounterInfo(description='Querying Beefy vault token price'),
            )
        except (NotERC20Conformant, NotERC721Conformant, InputError) as e:
            log.error(
                f'Failed to get underlying token {underlying_token} '
                f'for Beefy vault {vault_token} on {evm_inquirer.chain_name} due to {e!s}',
            )
            continue

        token_price = inquirer.find_usd_price(token)
        usd_price += token_price * token_normalized_value(amount, token)

    return Price(usd_price)


def query_beefy_vault_price(
        inquirer: 'Inquirer',
        vault_token: 'EvmToken',
        evm_inquirer: 'EvmNodeInquirer',
) -> Price:
    """Gets the token price for a Beefy vault token.

    Handles the following types of vault tokens:
    * moo (standard vault) https://docs.beefy.finance/developer-documentation/vault-contract
    * rmoo (boosted standard vault) https://docs.beefy.finance/beefy-products/boost
    * cow (clm vault) https://docs.beefy.finance/beefy-products/clm
    * rcow (reward pool token for clm vault) https://docs.beefy.finance/beefy-products/clm#how-does-the-clm-pool-work
    * other simple reward pool vault (e.g. rBIFI, etc). The docs don't cover this very well, but
      rBIFI is mentioned here: https://docs.beefy.finance/ecosystem/bifi-token#what-is-usdrbifi
      These seem to be the `"type": "gov"` vaults in the api, which are BeefyRewardPool contracts.

    Note that rmoo and rcow are 1:1 with their underlying moo or cow token, so simply use
    the underlying token as the vault token for these. The simple reward pool vaults are also 1:1
    with their underlying token, but in this case the underlying token is not a beefy vault token.
    """
    if vault_token.symbol.startswith('rmoo') or vault_token.symbol.startswith('rcow'):
        if (underlying_token := get_single_underlying_token(vault_token)) is not None:
            vault_token = underlying_token
        else:
            log.error(
                f'Unexpected underlying tokens {vault_token.underlying_tokens} for '
                f'Beefy token {vault_token} on {evm_inquirer.chain_name}',
            )
            return ZERO_PRICE

    if vault_token.symbol.startswith('moo'):
        return get_vault_price(
            inquirer=inquirer,
            vault_token=vault_token,
            evm_inquirer=evm_inquirer,
            display_name='Beefy finance',
            vault_abi=BEEFY_VAULT_ABI,
            pps_method='getPricePerFullShare',
        )
    elif vault_token.symbol.startswith('cow'):
        return _query_beefy_cow_token_price(
            inquirer=inquirer,
            evm_inquirer=evm_inquirer,
            vault_token=vault_token,
        )
    elif (underlying_token := get_single_underlying_token(vault_token)) is not None:
        return inquirer.find_usd_price(underlying_token)
    else:
        log.error(f'Unexpected Beefy token {vault_token} on {evm_inquirer.chain_name}')

    return ZERO_PRICE
