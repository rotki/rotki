import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import type { SettingValue } from '@/modules/settings/use-setting';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';

/**
 * Every indexer the dialog can offer, in the order it falls back to.
 *
 * @remarks
 * Listed here rather than read from a setting so the dialog still offers a choice on an account
 * that has never configured one.
 */
export const FALLBACK_INDEXER_ORDER: readonly PrioritizedListId[] = [
  EvmIndexer.ETHERSCAN,
  EvmIndexer.BLOCKSCOUT,
  EvmIndexer.ROUTESCAN,
];

/**
 * The indexer order the redecode dialog opens with: the chain's own order, else the account-wide
 * default, else every indexer.
 *
 * @remarks
 * An empty stored default is treated as unset, because an order with nothing in it would leave the
 * redecode no indexer to ask. A chain order is taken as given, empty or not: that one was chosen
 * for this chain deliberately.
 *
 * @param chainName - the EVM chain being redecoded, absent for a non-EVM event
 * @param chainOrders - the per-chain orders, as stored in settings
 * @param defaultOrder - the account-wide order, as stored in settings
 * @returns a fresh array the caller may reorder in place
 */
export function initialIndexerOrder(
  chainName: string | undefined,
  chainOrders: SettingValue<'evmIndexersOrder'> | undefined,
  defaultOrder: SettingValue<'defaultEvmIndexerOrder'> | undefined,
): PrioritizedListId[] {
  if (chainName && chainOrders?.[chainName])
    return [...chainOrders[chainName]];

  if (defaultOrder && defaultOrder.length > 0)
    return [...defaultOrder];

  return [...FALLBACK_INDEXER_ORDER];
}
