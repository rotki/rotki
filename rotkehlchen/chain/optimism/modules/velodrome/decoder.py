from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.optimism.modules.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.optimism.modules.velodrome.velodrome_cache import (
    query_velodrome_data,
    read_velodrome_pools_and_gauges_from_cache,
    save_velodrome_data_to_cache,
)
from rotkehlchen.types import CacheType, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class VelodromeDecoder(DecoderInterface, ReloadableDecoderMixin):
    """
    A decoder class for velodrome related events.
    TODO: This is mainly a skeleton for now. It should be implemented properly.
    """

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.pools, self.gauges = read_velodrome_pools_and_gauges_from_cache()

    def _decode_velodrome_events(self) -> None:
        pass

    def _decode_velodrome_gauge_events(self) -> None:
        pass

    def counterparties(self) -> list['CounterpartyDetails']:
        return [CounterpartyDetails(identifier=CPT_VELODROME, label='velodrome_finance', image='velodrome.svg')]  # noqa: E501

    def reload_data(self) -> Optional[Mapping[ChecksumEvmAddress, tuple[Any, ...]]]:
        """Make sure velodrome pools are recently queried from the chain, saved in the DB
        and loaded to the decoder's memory.

        If a query happens and any new mappings are generated they are returned,
        otherwise `None` is returned.
        TODO: consider abstracting this method (it is similar to curve's one)
        """
        self.evm_inquirer.ensure_cache_data_is_updated(  # type: ignore  # mypy doesn't understand that the optimism inquirer is a DSProxyInquirerWithCacheData with an ensure_cache_data_is_updated method  # noqa: E501
            cache_type=CacheType.VELODROME_POOL_ADDRESS,
            query_method=query_velodrome_data,
            save_method=save_velodrome_data_to_cache,
        )
        new_pools, new_gauges = read_velodrome_pools_and_gauges_from_cache()
        pools_diff = new_pools - self.pools
        gauges_diff = new_gauges - self.gauges
        if len(pools_diff) == 0 and len(gauges_diff) == 0:
            return None

        self.pools = new_pools
        self.gauges = new_gauges
        new_mapping: dict[ChecksumEvmAddress, tuple[Any, ...]] = {
            pool_address: (self._decode_velodrome_events,)
            for pool_address in pools_diff
        }
        new_mapping.update({
            # addresses of pools and gauges don't intersect, so combining like this is fine
            gauge_address: (self._decode_velodrome_gauge_events,)
            for gauge_address in gauges_diff
        })
        return new_mapping
