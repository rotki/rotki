import logging
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_KFEE, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.manual_price_oracles import ManualPriceOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

from .types import HistoricalPriceOracle, HistoricalPriceOracleInstance

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_usd_price_or_use_default(
        asset: Asset,
        time: Timestamp,
        default_value: FVal,
        location: str,
) -> Price:
    try:
        usd_price = PriceHistorian().query_historical_price(
            from_asset=asset,
            to_asset=A_USD,
            timestamp=time,
        )
    except (RemoteError, NoPriceForGivenTimestamp):
        log.error(
            f'Could not query usd price for {asset.identifier} and time {time} '
            f'when processing {location}. Assuming price of ${str(default_value)}',
        )
        usd_price = Price(default_value)

    return usd_price


def query_usd_price_zero_if_error(
        asset: Asset,
        time: Timestamp,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> Price:
    try:
        usd_price = PriceHistorian().query_historical_price(
            from_asset=asset,
            to_asset=A_USD,
            timestamp=time,
        )
    except (RemoteError, NoPriceForGivenTimestamp):
        msg_aggregator.add_error(
            f'Could not query usd price for {str(asset)} and time {time} '
            f'when processing {location}. Using zero price',
        )
        usd_price = Price(ZERO)

    return usd_price


class PriceHistorian():
    __instance: Optional['PriceHistorian'] = None
    _cryptocompare: 'Cryptocompare'
    _coingecko: 'Coingecko'
    _defillama: 'Defillama'
    _manual: ManualPriceOracle  # This is used when iterating through all oracles
    _oracles: Optional[List[HistoricalPriceOracle]] = None
    _oracle_instances: Optional[List[HistoricalPriceOracleInstance]] = None

    def __new__(
            cls,
            data_directory: Path = None,
            cryptocompare: 'Cryptocompare' = None,
            coingecko: 'Coingecko' = None,
            defillama: 'Defillama' = None,
    ) -> 'PriceHistorian':
        if PriceHistorian.__instance is not None:
            return PriceHistorian.__instance

        error_msg = 'arguments should be given at the first instantiation'
        assert data_directory, error_msg
        assert cryptocompare, error_msg
        assert coingecko, error_msg
        assert defillama, error_msg

        PriceHistorian.__instance = object.__new__(cls)
        PriceHistorian._cryptocompare = cryptocompare
        PriceHistorian._coingecko = coingecko
        PriceHistorian._defillama = defillama
        PriceHistorian._manual = ManualPriceOracle()

        return PriceHistorian.__instance

    @staticmethod
    def set_oracles_order(oracles: List[HistoricalPriceOracle]) -> None:
        assert len(oracles) != 0 and len(oracles) == len(set(oracles)), (
            'Oracles can\'t be empty or have repeated items'
        )
        instance = PriceHistorian()
        instance._oracles = oracles
        instance._oracle_instances = [getattr(instance, f'_{str(oracle)}') for oracle in oracles]

    @staticmethod
    def get_price_for_special_asset(
        from_asset: Asset,
        to_asset: Asset,
        timestamp: Timestamp,
    ) -> Optional[Price]:
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`
        for the case where `from_asset` needs a special handling.

        Can return None if the from asset is not in the list of special cases

        Args:
            from_asset: The ticker symbol of the asset for which we want to know
                        the price.
            to_asset: The ticker symbol of the asset against which we want to
                      know the price.
            timestamp: The timestamp at which to query the price

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        """
        if from_asset == A_KFEE:
            # For KFEE the price is fixed at 0.01$
            usd_price = Price(FVal(0.01))
            if to_asset == A_USD:
                return usd_price

            price_mapping = PriceHistorian().query_historical_price(
                from_asset=A_USD,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            return Price(usd_price * price_mapping)
        return None

    @staticmethod
    def query_historical_price(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`.
        So how much `to_asset` does 1 unit of `from_asset` cost.

        Args:
            from_asset: The ticker symbol of the asset for which we want to know
                        the price.
            to_asset: The ticker symbol of the asset against which we want to
                      know the price.
            timestamp: The timestamp at which to query the price

        May raise:
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        """
        log.debug(
            'Querying historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if from_asset == to_asset:
            return Price(FVal('1'))

        special_asset_price = PriceHistorian().get_price_for_special_asset(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if special_asset_price is not None:
            return special_asset_price

        # Querying historical forex data is attempted first via the external apis
        # and then via any price oracle that has fiat to fiat.
        try:
            from_asset = from_asset.resolve_to_fiat_asset()
            to_asset = from_asset.resolve_to_fiat_asset()
            price = Inquirer().query_historical_fiat_exchange_rates(
                from_fiat_currency=from_asset,
                to_fiat_currency=to_asset,
                timestamp=timestamp,
            )
            if price is not None:
                return price
        except (UnknownAsset, WrongAssetType):
            pass  # else cryptocompare also has historical fiat to fiat data

        instance = PriceHistorian()
        oracles = instance._oracles
        oracle_instances = instance._oracle_instances
        assert isinstance(oracles, list) and isinstance(oracle_instances, list), (
            'PriceHistorian should never be called before setting the oracles'
        )
        rate_limited = False
        for oracle, oracle_instance in zip(oracles, oracle_instances):
            can_query_history = oracle_instance.can_query_history(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            if can_query_history is False:
                continue

            try:
                price = oracle_instance.query_historical_price(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
            except (
                PriceQueryUnsupportedAsset,
                NoPriceForGivenTimestamp,
                UnknownAsset,
                WrongAssetType,
            ):
                continue
            except RemoteError as e:
                # Raise the flag if any of the services was rate limited
                rate_limited = (
                    rate_limited is True or
                    e.error_code == HTTPStatus.TOO_MANY_REQUESTS
                )
                continue

            log.debug(
                f'Historical price oracle {oracle} got price',
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )
            return price

        raise NoPriceForGivenTimestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            time=timestamp,
            rate_limited=rate_limited,
        )
