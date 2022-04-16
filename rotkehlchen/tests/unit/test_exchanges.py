from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.exchanges.ftx import Ftx
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.types import Location


def test_exchanges_filtering(database, exchange_manager, function_scope_messages_aggregator):
    kraken1 = MockKraken(
        name='mockkraken_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    kraken2 = MockKraken(
        name='mockkraken_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    ftx1 = Ftx(
        name='mockftx_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ftx_subaccount=None,
    )
    ftx2 = Ftx(
        name='mockftx_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ftx_subaccount=None,
    )

    exchange_manager.initialize_exchanges({}, database)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken1)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken2)
    exchange_manager.connected_exchanges[Location.FTX].append(ftx1)
    exchange_manager.connected_exchanges[Location.FTX].append(ftx2)
    assert set(exchange_manager.iterate_exchanges()) == {kraken1, kraken2, ftx1, ftx2}

    database.set_settings(ModifiableDBSettings(
        non_syncing_exchanges=[kraken1.location_id(), kraken2.location_id()],
    ))
    assert set(exchange_manager.iterate_exchanges()) == {ftx1, ftx2}

    database.set_settings(ModifiableDBSettings(
        non_syncing_exchanges=[ftx1.location_id()],
    ))
    assert set(exchange_manager.iterate_exchanges()) == {ftx2, kraken1, kraken2}
