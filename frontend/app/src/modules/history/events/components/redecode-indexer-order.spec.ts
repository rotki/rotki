import { describe, expect, it } from 'vitest';
import { FALLBACK_INDEXER_ORDER, initialIndexerOrder } from '@/modules/history/events/components/redecode-indexer-order';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';

describe('initialIndexerOrder', () => {
  it('should prefer the order stored for the chain being redecoded', () => {
    const chainOrders = { ethereum: [EvmIndexer.ROUTESCAN], optimism: [EvmIndexer.BLOCKSCOUT] };

    expect(initialIndexerOrder('optimism', chainOrders, [EvmIndexer.ETHERSCAN])).toEqual([EvmIndexer.BLOCKSCOUT]);
  });

  it('should fall back to the account default when the chain has no order', () => {
    const chainOrders = { ethereum: [EvmIndexer.ROUTESCAN] };

    expect(initialIndexerOrder('optimism', chainOrders, [EvmIndexer.ETHERSCAN])).toEqual([EvmIndexer.ETHERSCAN]);
  });

  it('should fall back to the account default for an event with no chain', () => {
    const chainOrders = { ethereum: [EvmIndexer.ROUTESCAN] };

    expect(initialIndexerOrder(undefined, chainOrders, [EvmIndexer.ETHERSCAN])).toEqual([EvmIndexer.ETHERSCAN]);
  });

  it('should offer every indexer when nothing has been configured', () => {
    expect(initialIndexerOrder(undefined, undefined, undefined)).toEqual([...FALLBACK_INDEXER_ORDER]);
  });

  /** An empty default would leave the redecode no indexer to ask, so it is treated as unset. */
  it('should offer every indexer when the stored default is empty', () => {
    expect(initialIndexerOrder('optimism', {}, [])).toEqual([...FALLBACK_INDEXER_ORDER]);
  });

  /** A chain order is taken as given: that one was chosen for this chain deliberately. */
  it('should honour an empty order stored for the chain', () => {
    expect(initialIndexerOrder('optimism', { optimism: [] }, [EvmIndexer.ETHERSCAN])).toEqual([]);
  });

  it('should copy the stored order rather than hand back the setting', () => {
    const chainOrders = { optimism: [EvmIndexer.BLOCKSCOUT] };

    const order = initialIndexerOrder('optimism', chainOrders, undefined);
    order.push(EvmIndexer.ETHERSCAN);

    expect(chainOrders.optimism).toEqual([EvmIndexer.BLOCKSCOUT]);
  });

  it('should copy the default order rather than hand back the setting', () => {
    const defaultOrder = [EvmIndexer.BLOCKSCOUT];

    const order = initialIndexerOrder(undefined, undefined, defaultOrder);
    order.push(EvmIndexer.ETHERSCAN);

    expect(defaultOrder).toEqual([EvmIndexer.BLOCKSCOUT]);
  });

  it('should copy the fallback rather than hand back the shared constant', () => {
    const order = initialIndexerOrder(undefined, undefined, undefined);
    order.push(EvmIndexer.ETHERSCAN);

    expect(FALLBACK_INDEXER_ORDER).toHaveLength(3);
  });
});
