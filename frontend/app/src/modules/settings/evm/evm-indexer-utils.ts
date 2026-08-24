import { toCapitalCase } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { PrioritizedListData, type PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import {
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ETHERSCAN_PRIO_LIST_ITEM,
  type PrioritizedListId,
  ROUTESCAN_PRIO_LIST_ITEM,
} from '@/modules/settings/types/prioritized-list-id';

/** Tab id standing for the global default order, as opposed to a per-chain override. */
export const DEFAULT_INDEXER_TAB = 'default';

export interface ChainItem {
  id: string;
  name: string;
}

export interface TabItem {
  id: string;
  isDefault: boolean;
  name?: string;
}

/** Order applied when the backend has no stored default yet. */
export const DEFAULT_INDEXER_ORDER: EvmIndexer[] = [
  EvmIndexer.ETHERSCAN,
  EvmIndexer.BLOCKSCOUT,
  EvmIndexer.ROUTESCAN,
];

const ALL_INDEXER_ITEMS: Array<PrioritizedListItemData<EvmIndexer>> = [
  ETHERSCAN_PRIO_LIST_ITEM,
  BLOCKSCOUT_PRIO_LIST_ITEM,
  ROUTESCAN_PRIO_LIST_ITEM,
];

/** Chains that only a subset of the indexers can serve. Anything absent supports all of them. */
const CHAIN_SUPPORTED_INDEXERS = new Map<string, Array<PrioritizedListItemData<EvmIndexer>>>([
  ['binance_sc', [ETHERSCAN_PRIO_LIST_ITEM]],
]);

const evmIndexerValues: string[] = Object.values(EvmIndexer);

export function isEvmIndexer(value: PrioritizedListId): value is EvmIndexer {
  return evmIndexerValues.includes(value);
}

/** Indexers selectable for a chain; `null` asks for the default tab's full set. */
export function getAvailableIndexersForChain(chainId: string | null): PrioritizedListData<PrioritizedListId> {
  const items = (chainId === null ? undefined : CHAIN_SUPPORTED_INDEXERS.get(chainId)) ?? ALL_INDEXER_ITEMS;
  return new PrioritizedListData<PrioritizedListId>(items);
}

/** Restrict an order to the indexers a chain actually supports, never leaving it empty. */
export function orderForChain(chainId: string, order: PrioritizedListId[]): EvmIndexer[] {
  const available = getAvailableIndexersForChain(chainId);
  const filtered = order.filter(indexer => available.itemDataForId(indexer) !== undefined).filter(isEvmIndexer);
  return filtered.length > 0 ? filtered : [EvmIndexer.ETHERSCAN];
}

/** Chain-id keyed orders as the backend wants them: keyed by evm chain name, indexers only. */
export function toEvmChainNameKeys(
  orders: Record<string, PrioritizedListId[]>,
  getEvmChainName: (chain: string) => string | undefined,
): Record<string, EvmIndexer[]> {
  const result: Record<string, EvmIndexer[]> = {};
  for (const [chain, order] of Object.entries(orders)) {
    const evmChainName = getEvmChainName(chain);
    if (evmChainName)
      result[evmChainName] = order.filter(isEvmIndexer);
  }
  return result;
}

/** The inverse: backend orders keyed by evm chain name, converted to chain ids for local use. */
export function toChainIdKeys(
  orders: Record<string, EvmIndexer[]> | undefined,
  getChain: (evmChainName: string) => string,
): Record<string, PrioritizedListId[]> {
  if (!orders)
    return {};

  const result: Record<string, PrioritizedListId[]> = {};
  for (const [evmChainName, order] of Object.entries(orders))
    result[getChain(evmChainName)] = [...order];

  return result;
}

export function buildTabs(configuredChains: string[], getChainName: (chain: string) => string): TabItem[] {
  return [
    { id: DEFAULT_INDEXER_TAB, isDefault: true },
    ...configuredChains.map(chain => ({
      id: chain,
      isDefault: false,
      name: getChainName(chain),
    })),
  ];
}

/** Chains still available to add, i.e. those without an override of their own. */
export function getAvailableChainItems(chains: ChainItem[], configuredChains: string[]): ChainItem[] {
  return chains
    .filter(chain => !configuredChains.includes(chain.id))
    .map(({ id, name }) => ({ id, name }));
}

/** Chain-specific caveats about the selected order. Keys are resolved by the caller. */
export function getChainIndexerWarnings(tab: string, order: PrioritizedListId[]): MessageKey[] {
  if (tab === DEFAULT_INDEXER_TAB)
    return [];

  const warnings: MessageKey[] = [];

  if (tab === 'optimism' && order.includes(EvmIndexer.BLOCKSCOUT))
    warnings.push(msg.$t('evm_settings.indexer.chain_warnings.optimism_blockscout'));

  if (tab === 'base' && (order.length === 0 || order[0] !== EvmIndexer.BLOCKSCOUT))
    warnings.push(msg.$t('evm_settings.indexer.chain_warnings.base_limited_indexers'));

  if (tab === 'gnosis')
    warnings.push(msg.$t('evm_settings.indexer.chain_warnings.gnosis_key_required'));

  return warnings;
}

/** The indexers whose api key the user is expected to provide themselves. */
const KEYED_INDEXERS: EvmIndexer[] = [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT];

/** First indexer in the order, when it is one the user has to supply a key for. */
export function keyedPrimaryIndexer(order: PrioritizedListId[]): EvmIndexer | undefined {
  const first = order.at(0);
  if (first === undefined || !isEvmIndexer(first) || !KEYED_INDEXERS.includes(first))
    return undefined;

  return first;
}

/** Display name of the primary indexer when it needs a key the user has not entered. */
export function getMissingApiKeyIndexer(
  order: PrioritizedListId[],
  hasApiKey: (indexer: EvmIndexer) => boolean,
): string | undefined {
  const primary = keyedPrimaryIndexer(order);
  if (primary === undefined || hasApiKey(primary))
    return undefined;

  return toCapitalCase(primary);
}
