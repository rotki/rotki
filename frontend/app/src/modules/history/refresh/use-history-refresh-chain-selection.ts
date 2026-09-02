import type { ComputedRef, Ref } from 'vue';
import type { ChainData } from '@/modules/history/refresh/types';
import { getTextToken } from '@rotki/common';
import { cloneDeep, isEqual } from 'es-toolkit';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';

interface UseHistoryRefreshChainSelectionOptions {
  /** The chain whose addresses are being picked individually; undefined lists every chain. */
  chain: Ref<string | undefined>;
  /** The accounts to refresh, kept in sync with the selection. */
  modelValue: Ref<ChainAddress[]>;
  /** The chain-list filter; cleared whenever the drilled-into chain changes. */
  search: Ref<string>;
  /** Called whenever the selection covers everything currently in view, or stops doing so. */
  onAllSelected?: (allSelected: boolean) => void;
}

interface UseHistoryRefreshChainSelectionReturn {
  /** Every address the user holds, per chain, whether selected or not. */
  chainAddresses: ComputedRef<Record<string, string[]>>;
  /** The chains worth listing: the ones with accounts, narrowed by the search. */
  filtered: ComputedRef<ChainData[]>;
  /** The picked addresses per chain, bound per row. */
  modelSelection: Ref<Record<string, string[]>>;
  /**
   * Selects everything in view, or clears it if it is already all selected.
   *
   * @remarks
   * Scoped to the drilled-into chain when there is one, so selecting all inside a chain does not
   * silently select every other chain's addresses too.
   */
  toggleSelectAll: () => void;
}

/**
 * Drives which accounts a history refresh covers.
 *
 * @returns the chain list and the selection; only
 * {@link UseHistoryRefreshChainSelectionReturn.toggleSelectAll} and writes to `modelSelection`
 * change it
 */
export function useHistoryRefreshChainSelection(
  options: UseHistoryRefreshChainSelectionOptions,
): UseHistoryRefreshChainSelectionReturn {
  const { chain: selectedChain, modelValue, onAllSelected, search } = options;

  const modelSelection = ref<Record<string, string[]>>({});

  const { bitcoinChainsData, evmLikeChainsData, solanaChainsData, txEvmChains } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const refreshChains = computed<ChainData[]>(() => [
    ...get(txEvmChains).map(item => ({
      chain: item.id,
      id: item.id,
      name: item.name,
      type: TransactionChainType.EVM,
    })),
    ...get(evmLikeChainsData).map(item => ({
      chain: item.id,
      id: item.id,
      name: item.name,
      type: TransactionChainType.EVMLIKE,
    })),
    ...get(bitcoinChainsData).map(item => ({
      chain: item.id,
      id: item.id,
      name: item.name,
      type: TransactionChainType.BITCOIN,
    })),
    ...get(solanaChainsData).map(item => ({
      chain: item.id,
      id: item.id,
      name: item.name,
      type: TransactionChainType.SOLANA,
    })),
  ]);

  const filtered = computed<ChainData[]>(() => {
    const chains = get(refreshChains).filter(item => getAddresses(item.id)?.length > 0);
    const query = getTextToken(get(search));
    if (!query)
      return chains;

    return chains.filter(item => getTextToken(item.chain).includes(query) || getTextToken(item.name).includes(query));
  });

  const chainAddresses = computed<Record<string, string[]>>(() => {
    const record: Record<string, string[]> = {};
    return get(refreshChains).reduce((acc, item) => {
      acc[item.chain] = getAddresses(item.id) ?? [];
      return acc;
    }, record);
  });

  function getAccounts(record: Record<string, string[]>): ChainAddress[] {
    return Object.entries(record).flatMap(([chainKey, addresses]) => addresses.map((address): ChainAddress => ({
      address,
      chain: chainKey,
    })));
  }

  const selected = computed<number>(() => getAccounts(get(modelSelection)).length);

  function emptySelection(): Record<string, string[]> {
    return Object.fromEntries(get(refreshChains).map(item => [item.chain, []]));
  }

  function updateAllSelected(): void {
    if (isDefined(selectedChain)) {
      const current = get(modelSelection);
      const evmChain = get(selectedChain);
      onAllSelected?.(isEqual(get(chainAddresses)[evmChain], current[evmChain]));
    }
    else {
      onAllSelected?.(isEqual(getAccounts(get(chainAddresses)), getAccounts(get(modelSelection))));
    }
  }

  function updateSelection(newSelection: Record<string, string[]>): void {
    set(modelSelection, newSelection);
    set(modelValue, getAccounts(newSelection));
    updateAllSelected();
  }

  function toggleSpecificChain(chain: string): void {
    const currentSelection = get(modelSelection);
    updateSelection({
      ...currentSelection,
      [chain]: currentSelection[chain].length === 0 ? get(chainAddresses)[chain] : [],
    });
  }

  function toggleAllChains(): void {
    updateSelection(get(selected) === 0 ? cloneDeep(get(chainAddresses)) : emptySelection());
  }

  function toggleSelectAll(): void {
    if (isDefined(selectedChain))
      toggleSpecificChain(get(selectedChain));
    else
      toggleAllChains();
  }

  watch(selectedChain, () => {
    set(search, '');
    updateAllSelected();
  });

  watch(modelSelection, (newSelection) => {
    set(modelValue, getAccounts(newSelection));
    updateAllSelected();
  }, { deep: true });

  updateSelection(emptySelection());

  return {
    chainAddresses,
    filtered,
    modelSelection,
    toggleSelectAll,
  };
}
