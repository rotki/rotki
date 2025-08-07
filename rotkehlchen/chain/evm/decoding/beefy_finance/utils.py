import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_evm_token, get_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value, token_raw_value_decimals
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.utils import get_vault_price, update_cached_vaults
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import (
    InputError,
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
    UnableToDecryptRemoteData,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_int
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Price,
    TokenKind,
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


def _query_beefy_vaults_api(chain: ChainID) -> list[dict[str, Any]] | None:
    """Query Beefy finance API for all vaults on the given chain."""
    try:
        return request_get(url=f'https://api.beefy.finance/vaults/all/{chain.value}')  # type: ignore[return-value]  # we get a list of dictionaries from the api
    except (RemoteError, UnableToDecryptRemoteData) as e:
        log.error(f'Failed to retrieve Beefy vaults for {chain} due to {e!s}')
        return None


def _process_beefy_vault(
        database: 'DBHandler',
        vault: dict[str, Any],
        evm_inquirer: 'EvmNodeInquirer',
) -> None:
    """Process beefy finance vault data from the api and add its tokens to the database.
    May raise:
    - NotERC20Conformant
    - DeserializationError
    - KeyError
    - InputError if there is an error while editing a token (if the underlying token is the same
      as the vault token for example)
    """
    encounter = TokenEncounterInfo(
        description='Querying Beefy finance vaults',
        should_notify=False,
    )
    if (vault_type := vault['type']) in ('standard', 'gov'):
        # in standard and gov vaults the `tokenAddress` is the vault address, so add it as the
        # earned token's underlying token to be used when querying the price.
        underlying_tokens = [UnderlyingToken(
            address=get_or_create_evm_token(
                userdb=database,
                evm_inquirer=evm_inquirer,
                evm_address=deserialize_evm_address(vault['tokenAddress']),
                chain_id=evm_inquirer.chain_id,
                decimals=deserialize_int(
                    value=vault['tokenDecimals'],
                    location='beefy token decimals',
                ),
                encounter=encounter,
            ).evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )]
    elif vault_type == 'cowcentrated':
        underlying_tokens = None  # CLM vault where the earned token is the vault token itself.
    else:
        log.warning(f'Unknown Beefy vault type {vault_type} for vault {vault}')
        return

    get_or_create_evm_token(
        userdb=database,
        evm_address=deserialize_evm_address(vault['earnContractAddress']),  # this key is present for all vault types  # noqa: E501
        chain_id=evm_inquirer.chain_id,
        evm_inquirer=evm_inquirer,
        protocol=CPT_BEEFY_FINANCE,
        underlying_tokens=underlying_tokens,
        encounter=encounter,
    )


def query_beefy_vaults(evm_inquirer: 'EvmNodeInquirer') -> None:
    """Query list of Beefy finance vaults and add the vault tokens to the global database."""
    update_cached_vaults(
        database=evm_inquirer.database,
        cache_key=(CacheType.BEEFY_VAULTS, str(evm_inquirer.chain_id.value)),
        display_name='Beefy finance',
        chain=evm_inquirer.chain_id,
        query_vaults=lambda: _query_beefy_vaults_api(evm_inquirer.chain_id),
        process_vault=lambda db, entry: _process_beefy_vault(db, entry, evm_inquirer),
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
    """Gets the token price for a Beefy vault."""
    if vault_token.symbol.startswith('moo'):  # standard vault - https://docs.beefy.finance/developer-documentation/vault-contract  # noqa: E501
        return get_vault_price(
            inquirer=inquirer,
            vault_token=vault_token,
            evm_inquirer=evm_inquirer,
            display_name='Beefy finance',
            vault_abi=BEEFY_VAULT_ABI,
            pps_method='getPricePerFullShare',
        )
    elif vault_token.symbol.startswith('cow'):  # clm vault - https://docs.beefy.finance/beefy-products/clm  # noqa: E501
        return _query_beefy_cow_token_price(
            inquirer=inquirer,
            evm_inquirer=evm_inquirer,
            vault_token=vault_token,
        )
    elif vault_token.symbol.startswith('rcow'):  # reward pool token for clm vault - https://docs.beefy.finance/beefy-products/clm#how-does-the-clm-pool-work  # noqa: E501
        if len(vault_token.underlying_tokens) == 1 and (cow_token := get_token(
            evm_address=vault_token.underlying_tokens[0].address,  # rcow token is 1:1 with the underlying cow token  # noqa: E501
            chain_id=evm_inquirer.chain_id,
        )) is not None:
            return _query_beefy_cow_token_price(
                inquirer=inquirer,
                evm_inquirer=evm_inquirer,
                vault_token=cow_token,
            )

        log.error(f'Unexpected underlying tokens for Beefy reward pool token {vault_token} on {evm_inquirer.chain_name}')  # noqa: E501
    else:
        log.error(f'Unexpected Beefy token symbol for token {vault_token} on {evm_inquirer.chain_name}')  # noqa: E501

    return ZERO_PRICE
