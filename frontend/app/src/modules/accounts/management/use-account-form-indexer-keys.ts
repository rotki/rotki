import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { camelCase } from 'es-toolkit';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { keyedPrimaryIndexer } from '@/modules/settings/evm/evm-indexer-utils';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useSetting } from '@/modules/settings/use-setting';

type KeyedIndexer = EvmIndexer.ETHERSCAN | EvmIndexer.BLOCKSCOUT;

interface UseAccountFormIndexerKeysReturn {
  /** Chain names whose history query waits on a Blockscout key, named in its warning. */
  blockscoutKeyChainNames: ComputedRef<string[]>;
  missingIndexerKeys: ComputedRef<Array<'etherscan' | 'blockscout'>>;
}

/**
 * The indexer keys an account being added on `chain` is missing. `active` is false where no
 * transaction history is queried for the account, such as a validator or an edit.
 */
export function useAccountFormIndexerKeys(
  chain: MaybeRefOrGetter<string | undefined>,
  active: MaybeRefOrGetter<boolean>,
): UseAccountFormIndexerKeysReturn {
  const { getChainName, isEvm, txEvmChains } = useSupportedChains();
  const { getApiKey } = useExternalApiKeys();

  const defaultEvmIndexerOrder = useSetting('defaultEvmIndexerOrder');
  const evmIndexersOrder = useSetting('evmIndexersOrder');

  /** The indexer order a chain is queried with: its own override, else the default order. */
  function indexerOrderFor(chainId: string): EvmIndexer[] {
    const chainOrders = get(evmIndexersOrder);
    const evmChainName = camelCase(get(txEvmChains).find(c => c.id === chainId)?.evmChainName ?? '');
    return evmChainName && chainOrders[evmChainName]
      ? chainOrders[evmChainName]
      : get(defaultEvmIndexerOrder);
  }

  /** The EVM chains the selection queries transactions for; 'all' stands for every one of them. */
  function selectedEvmChainIds(selectedChain: string): string[] {
    if (selectedChain === 'all')
      return get(txEvmChains).map(item => item.id);

    return isEvm(selectedChain) ? [selectedChain] : [];
  }

  /**
   * Chains queried first by an indexer whose key is missing. A keyless lead is skipped for the next
   * indexer, and where Blockscout leads (Optimism, Base, Gnosis) the free tier of Etherscan does not
   * serve the chain either, so without that key their history is not queried at all.
   */
  function chainsLedWithoutKey(indexer: KeyedIndexer): string[] {
    const selectedChain = toValue(chain);
    if (!toValue(active) || !selectedChain || getApiKey(indexer))
      return [];

    return selectedEvmChainIds(selectedChain).filter(id => keyedPrimaryIndexer(indexerOrderFor(id)) === indexer);
  }

  const blockscoutKeyChains = computed<string[]>(() => chainsLedWithoutKey(EvmIndexer.BLOCKSCOUT));

  const blockscoutKeyChainNames = computed<string[]>(() => get(blockscoutKeyChains).map(id => getChainName(id)));

  const missingIndexerKeys = computed<Array<'etherscan' | 'blockscout'>>(() => {
    const services: Array<'etherscan' | 'blockscout'> = [];
    if (chainsLedWithoutKey(EvmIndexer.ETHERSCAN).length > 0)
      services.push('etherscan');
    if (get(blockscoutKeyChains).length > 0)
      services.push('blockscout');
    return services;
  });

  return {
    blockscoutKeyChainNames,
    missingIndexerKeys,
  };
}
