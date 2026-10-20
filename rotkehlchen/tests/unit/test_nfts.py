from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, Nft
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.balances import BlockchainBalancesUpdate
from rotkehlchen.chain.evm.tokens import ERC721OwnershipResult
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_USD, A_USDC
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price, SupportedBlockchain, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.evm.tokens import EvmTokens
    from rotkehlchen.db.drivers.sqlite import DBCursor

TEST_ACC1 = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # yabir.eth
TEST_ACC2 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'  # lefteris.eth
OPENSEA_STOREFRONT = string_to_evm_address('0x495f947276749Ce646f68AC8c248420045cb7b5e')  # ERC1155
PENGUIN_7535 = Asset('eip155:1/erc721:0x524cAB2ec69124574082676e6F654a18df49A048/7535')


def _add_nft_module_entry(
        write_cursor: DBCursor,
        nft_id: str,
        owner_address: ChecksumEvmAddress,
        usd_price: str,
) -> None:
    """Store an NFT in the nfts table as if the NFT module had queried it"""
    write_cursor.execute('INSERT INTO assets(identifier) VALUES(?)', (nft_id,))
    write_cursor.execute(
        'INSERT INTO nfts(identifier, name, last_price, last_price_asset, manual_price, '
        'owner_address, is_lp) VALUES(?, ?, ?, ?, ?, ?, ?)',
        (nft_id, 'Pudgy Penguin', usd_price, A_USD.identifier, 0, owner_address, 0),
    )


def _queried_tokens(
        tokens: EvmTokens,
        address: ChecksumEvmAddress,
) -> tuple[dict[ChecksumEvmAddress, list[EvmToken]], list[tuple[ChecksumEvmAddress, EvmToken]]]:
    """Query the token balances of the address without querying the chain.

    Returns the tokens sent to the balanceOf query and the ones sent to the ownerOf query.
    """
    with (
        patch('rotkehlchen.chain.evm.tokens.generate_multicall_chunks', return_value=[]) as chunks_mock,  # noqa: E501
        patch(
            'rotkehlchen.chain.evm.tokens.query_owned_erc721_tokens',
            return_value=ERC721OwnershipResult(owned=set(), failed=set(), reverted=set()),
        ) as ownership_mock,
    ):
        tokens.query_tokens_for_addresses(addresses=[address])

    return (
        chunks_mock.call_args.kwargs['addresses_to_tokens'],
        ownership_mock.call_args.kwargs['candidates'],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_addresses_queried_for_nfts(blockchain):
    """Tests that nfts are only queried for addresses stored in the database preventing the
    IntegrityError described in https://github.com/rotki/rotki/issues/4456
    """
    nft_module = blockchain.get_module('nfts')
    nft_module.query_balances(addresses=[TEST_ACC1, TEST_ACC2])
    balances = nft_module.get_db_nft_balances(filter_query=NFTFilterQuery.make())['entries']
    assert any(x['name'] == 'yabir.eth' for x in balances)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1143fd695a33ac740C84B93fd57f1f8396C1Af05']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nfts_floor_prices(
        blockchain: ChainsAggregator,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test that if the floor price is given in something else than ETH we correctly
    represent it.
    """
    nft_module = blockchain.get_module('nfts')
    assert nft_module is not None
    nfts = nft_module.opensea.get_account_nfts(ethereum_accounts[0])
    assert len(nfts) == 1
    assert nfts[0].collection is not None
    assert nfts[0].collection.floor_price == FVal(599)
    assert nfts[0].collection.floor_price_asset == Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')  # USDC.e on polygon # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize('mocked_current_prices', [{A_ETH: 3600}])
def test_nfts_of_collection_without_floor_price(
        blockchain: ChainsAggregator,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test that the NFTs of a collection with a zero floor price are not dropped.

    Opensea's collection stats no longer contain average_price, and a collection
    without listings, like GasHawk NFTs here, has a floor_price of 0.0.
    """
    nft_module = blockchain.get_module('nfts')
    assert nft_module is not None
    nfts = nft_module.opensea.get_account_nfts(ethereum_accounts[0])
    assert len(nfts) == 3
    gashawk = next(
        nft for nft in nfts
        if nft.collection is not None and nft.collection.name == 'GasHawk NFTs'
    )
    assert gashawk.collection is not None
    assert gashawk.collection.floor_price is None
    assert gashawk.price_in_asset == ZERO


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize('mocked_current_prices', [{A_USDC.identifier: 1, A_ETH: 3600}])
def test_sorting_nfts(blockchain: ChainsAggregator):
    """Test that if we have NFTs priced using different currencies then they are properly sorted
    by usd price when queried from the database.
    Regression test for https://github.com/rotki/rotki/issues/8022
    """
    with blockchain.database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO assets(identifier) VALUES(?)',
            (
                ('_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65',),
                ('_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041',),
            ),
        )
        write_cursor.executemany(
            'INSERT INTO nfts (identifier, name, last_price, last_price_asset, '
            'manual_price, owner_address, is_lp, image_url, '
            'collection_name, usd_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                ('_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'GasHawk Nest NFT', '1', 'ETH', '0', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'https://ipfs.io/ipfs/bafkreiadpakefxttuc5ry74hoswmlcp7ju5tq25lyghw2epa64u4nag3k4', 'GasHawk NFTs', '0.0'),  # noqa: E501
                ('_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041', 'yabir.eth', '20', 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '1', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0', 'https://metadata.ens.domains/mainnet/0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85/0x3ad5e1887ef8024efa6d5070ccfda4868783a5343e1089e47fda9b4f7ce4f2b9/image', 'ENS: Ethereum Name Service', '0.0'),  # noqa: E501
            ],
        )

    nft_module = blockchain.get_module('nfts')
    balances = nft_module.get_db_nft_balances(filter_query=NFTFilterQuery.make(order_by_rules=[('usd_price', False)]))['entries']  # type: ignore  # noqa: E501
    assert balances[0]['id'] == '_nft_0xfd9d8036f899ed5a9fd8cac7968e5f24d3db2a64_1_0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # gashawk with higher price first # noqa: E501
    assert balances[1]['id'] == '_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041'  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA2a6D337e042009EbAC0f0c398Fef08Dc1074f19']])
@pytest.mark.freeze_time('2026-01-01 00:00:00 GMT')
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_duplicate_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts,
        gnosis_accounts,
        allow_gnosis_etherscan: None,
):
    """Checks that we don't have duplicate balances for NFTs in balances.

    If an NFT is tracked only as a token and not in the NFT table we query it
    but if we track them from opensea as NFTs from the NFT module we avoid
    having duplicates.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    blockchain = rotki.chains_aggregator
    nft_token = get_or_create_evm_token(  # penguins NFT
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
    )
    gnosis_pay_nft_token = get_or_create_evm_token(  # gnosis OG NFT
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0x88997988a6A5aAF29BA973d298D276FE75fb69ab'),
        chain_id=ChainID.GNOSIS,
        token_kind=TokenKind.ERC721,
    )
    with blockchain.database.user_write() as write_cursor:
        blockchain.database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=ethereum_accounts[0],
            blockchain=blockchain.ethereum.node_inquirer.chain_id.to_blockchain(),
            tokens=[nft_token],
        )
        blockchain.database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=gnosis_accounts[0],
            blockchain=blockchain.gnosis.node_inquirer.chain_id.to_blockchain(),
            tokens=[gnosis_pay_nft_token],
        )
    nft_module = blockchain.get_module('nfts')
    assert nft_module is not None
    nft_module.query_balances(addresses=ethereum_accounts)
    balances = rotki.query_balances()
    assert Asset('eip155:1/erc721:0x524cAB2ec69124574082676e6F654a18df49A048') not in balances['assets']  # noqa: E501
    assert Asset('_nft_0x524cAB2ec69124574082676e6F654a18df49A048_7535') in balances['assets']
    assert Asset('eip155:100/erc721:0x88997988a6A5aAF29BA973d298D276FE75fb69ab') in balances['assets']  # noqa: E501


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_add_and_delete_nft_custom_price(blockchain: ChainsAggregator):
    """Test that adding and deleting a custom price for an NFT works correctly.

    Regression test: delete_price_for_nft used to set last_price and last_price_asset to NULL,
    which violated the NOT NULL constraints added in the v43-to-v44 DB upgrade.
    """
    nft_id = '_nft_0x524cAB2ec69124574082676e6F654a18df49A048_7535'
    with blockchain.database.user_write() as write_cursor:
        write_cursor.execute('INSERT INTO assets(identifier) VALUES(?)', (nft_id,))
        write_cursor.execute(
            'INSERT INTO nfts (identifier, name, last_price, last_price_asset, '
            'manual_price, owner_address, is_lp, image_url, '
            'collection_name, usd_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (nft_id, 'Test NFT', '0', 'ETH', 0, TEST_ACC1, 0, '', 'Test Collection', 0.0),
        )

    nft_module = blockchain.get_module('nfts')
    assert nft_module is not None
    assert nft_module.add_nft_with_price(  # set a custom price
        from_asset=(nft_asset := Asset(nft_id)),
        to_asset=A_ETH,
        price=Price(FVal('1.5')),
    ) is True
    with blockchain.database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT last_price, last_price_asset, manual_price FROM nfts WHERE identifier=?',
            (nft_id,),
        ).fetchone() == ('1.5', 'ETH', 1)

    # delete the custom price (this used to fail with NOT NULL constraint)
    assert nft_module.delete_price_for_nft(asset=nft_asset) is True
    with blockchain.database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT last_price, last_price_asset, manual_price FROM nfts WHERE identifier=?',
            (nft_id,),
        ).fetchone() == ('0', 'ETH', 0)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('is_erc1155', [False, True])
def test_nft_module_excludes_only_its_own_tokens(
        blockchain: ChainsAggregator,
        ethereum_accounts: list[ChecksumEvmAddress],
        is_erc1155: bool,
) -> None:
    """Regression test for https://github.com/rotki/rotki/issues/13295

    An NFT queried by the NFT module should only exclude its own ERC721 token from the
    token balance query and not every token of the same collection. A collection level
    token stays excluded since the NFT module covers the whole collection. An ERC1155 NFT
    has no ERC721 token, so it only excludes the collection level token.
    """
    db = blockchain.database
    penguins = string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048')
    tokens = [get_or_create_evm_token(
        userdb=db,
        evm_address=penguins,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id=collectible_id,
    ) for collectible_id in (None, '7535', '7536')]
    with db.user_write() as write_cursor:
        db.save_tokens_for_address(
            write_cursor=write_cursor,
            address=(user_address := ethereum_accounts[0]),
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=tokens,
        )
        _add_nft_module_entry(
            write_cursor=write_cursor,
            nft_id=f'_nft_{penguins}_7535' + (f'_{user_address}' if is_erc1155 else ''),
            owner_address=user_address,
            usd_price='3',
        )

    # the collection token and the ERC721 #7535 are covered by the NFT module
    assert _queried_tokens(blockchain.ethereum.tokens, user_address) == (
        {user_address: []},
        [(user_address, token) for token in (tokens[1:] if is_erc1155 else [tokens[2]])],
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('optimism_accounts', [[TEST_ACC1]])
def test_nft_module_excludes_no_tokens_of_other_chains(
        blockchain: ChainsAggregator,
        optimism_accounts: list[ChecksumEvmAddress],
) -> None:
    """The NFT module only queries Ethereum NFTs, so its NFTs should not exclude tokens of
    another chain with the same contract address from that chain's token balance query.
    """
    db = blockchain.database
    penguins = string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048')
    tokens = [get_or_create_evm_token(
        userdb=db,
        evm_address=penguins,
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC721,
        collectible_id=collectible_id,
    ) for collectible_id in (None, '7535')]
    with db.user_write() as write_cursor:
        db.save_tokens_for_address(
            write_cursor=write_cursor,
            address=(user_address := optimism_accounts[0]),
            blockchain=SupportedBlockchain.OPTIMISM,
            tokens=tokens,
        )
        _add_nft_module_entry(  # the blockchain of an nfts row is always Ethereum
            write_cursor=write_cursor,
            nft_id=f'_nft_{penguins}_7535',
            owner_address=user_address,
            usd_price='3',
        )

    # #7535 is checked on its own with ownerOf and the collection token with balanceOf
    assert _queried_tokens(blockchain.optimism.tokens, user_address) == (
        {user_address: [tokens[0]]},
        [(user_address, tokens[1])],
    )


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
def test_disabled_nft_module_excludes_no_tokens(
        blockchain: ChainsAggregator,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Regression test for https://github.com/rotki/rotki/issues/13340

    The NFTs that a disabled NFT module had stored are not added to the balances anymore,
    so they should not exclude any token from the token balance query.
    """
    db = blockchain.database
    penguins = string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048')
    tokens = [get_or_create_evm_token(
        userdb=db,
        evm_address=penguins,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id=collectible_id,
    ) for collectible_id in (None, '7535')]
    with db.user_write() as write_cursor:
        db.save_tokens_for_address(
            write_cursor=write_cursor,
            address=(user_address := ethereum_accounts[0]),
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=tokens,
        )
        _add_nft_module_entry(
            write_cursor=write_cursor,
            nft_id=f'_nft_{penguins}_7535',
            owner_address=user_address,
            usd_price='3',
        )
        db.set_settings(write_cursor, ModifiableDBSettings(active_modules=[]))

    # #7535 is checked on its own with ownerOf and the collection token with balanceOf
    assert _queried_tokens(blockchain.ethereum.tokens, user_address) == (
        {user_address: [tokens[0]]},
        [(user_address, tokens[1])],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA2a6D337e042009EbAC0f0c398Fef08Dc1074f19']])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
@pytest.mark.parametrize(('mocked_current_prices', 'expected_value'), [
    ({(PENGUIN_7535, DEFAULT_TESTS_MAIN_CURRENCY): ZERO, (A_ETH, DEFAULT_TESTS_MAIN_CURRENCY): FVal(3)}, FVal(6)),  # noqa: E501
    ({(PENGUIN_7535, DEFAULT_TESTS_MAIN_CURRENCY): FVal(5), (A_ETH, DEFAULT_TESTS_MAIN_CURRENCY): FVal(3)}, FVal(5)),  # noqa: E501
])
def test_disabled_nft_module_keeps_nft_in_balances(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
        expected_value: FVal,
) -> None:
    """Regression test for https://github.com/rotki/rotki/issues/13340

    After the NFT module is disabled, an NFT that token detection found is counted once in
    the balances. Its value comes from the manual price set for it in the NFT module, unless
    its ERC721 token has a price of its own, such as a manual price set after disabling.
    The account is the owner of #7535, so the recorded ownerOf query counts it.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    nft_token = get_or_create_evm_token(
        userdb=rotki.data.db,
        evm_address=string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id='7535',
    )
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.save_tokens_for_address(
            write_cursor=write_cursor,
            address=(user_address := ethereum_accounts[0]),
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[nft_token],
        )
        _add_nft_module_entry(
            write_cursor=write_cursor,
            nft_id=(nft_id := f'_nft_{nft_token.evm_address}_7535'),
            owner_address=user_address,
            usd_price='0',
        )

    assert (nft_module := rotki.chains_aggregator.get_module('nfts')) is not None
    nft_module.add_nft_with_price(from_asset=Asset(nft_id), to_asset=A_ETH, price=Price(FVal(2)))
    rotki.set_settings(ModifiableDBSettings(active_modules=[]))

    # saving the snapshot would query the main currency's USD rate online
    with patch.object(rotki.data.db, 'should_save_balances', return_value=False):
        assets = rotki.query_balances()['assets']

    assert assets[nft_token]['amount'] == ONE
    assert assets[nft_token]['value'] == expected_value
    assert Asset(nft_id) not in assets


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_nft_balance_updates_only_its_own_token(
        rotkehlchen_api_server: APIServer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Regression test for https://github.com/rotki/rotki/issues/13295

    When the balance query adds the NFT module's NFTs, an NFT that is also in the chain
    balances as an ERC721 token should update the value of its own token and not of another
    token of the same collection. An ERC1155 NFT has no ERC721 token and is added as is.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    penguins = string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048')
    # #7536 is created first so that it is the first token of the contract in the DB
    other_token, nft_token = (get_or_create_evm_token(
        userdb=rotki.data.db,
        evm_address=penguins,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC721,
        collectible_id=collectible_id,
    ) for collectible_id in ('7536', '7535'))
    with rotki.data.db.user_write() as write_cursor:
        _add_nft_module_entry(
            write_cursor=write_cursor,
            nft_id=(nft_id := f'_nft_{penguins}_7535'),
            owner_address=ethereum_accounts[0],
            usd_price='3',
        )
        _add_nft_module_entry(
            write_cursor=write_cursor,
            nft_id=(erc1155_nft_id := f'_nft_{OPENSEA_STOREFRONT}_1_{ethereum_accounts[0]}'),
            owner_address=ethereum_accounts[0],
            usd_price='2',
        )

    totals = BalanceSheet()
    totals.assets[other_token][DEFAULT_BALANCE_LABEL] = Balance(amount=ONE, value=FVal(5))
    totals.assets[nft_token][DEFAULT_BALANCE_LABEL] = Balance(amount=ONE, value=ZERO)
    with patch.object(
        rotki.chains_aggregator,
        'query_balances',
        return_value=BlockchainBalancesUpdate(
            given_chain=None,
            per_account=rotki.chains_aggregator.balances,
            totals=totals,
        ),
    ):
        assets = rotki.query_balances()['assets']

    assert (nft_module := rotki.chains_aggregator.get_module('nfts')) is not None
    nft_prices = {entry['id']: entry['price'] for entry in nft_module.get_db_nft_balances(
        filter_query=NFTFilterQuery.make(),
    )['entries']}
    assert assets[nft_token]['value'] == nft_prices[nft_id]
    assert assets[other_token]['value'] == FVal(5)
    assert Asset(nft_id) not in assets
    assert assets[Asset(erc1155_nft_id)]['value'] == nft_prices[erc1155_nft_id]


def test_nft_to_erc721_identifier() -> None:
    """An ERC721 NFT maps to its ERC721 token. An ERC1155 NFT, whose identifier also has
    the owner address, has no ERC721 token."""
    penguins = string_to_evm_address('0x524cAB2ec69124574082676e6F654a18df49A048')
    assert Nft(f'_nft_{penguins}_7535').to_erc721_identifier() == (
        f'eip155:1/erc721:{penguins}/7535'
    )
    assert Nft(f'_nft_{OPENSEA_STOREFRONT}_1_{TEST_ACC1}').to_erc721_identifier() is None
