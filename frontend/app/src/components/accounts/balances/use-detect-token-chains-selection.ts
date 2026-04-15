import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { EvmChainInfo } from '@/modules/api/types/chains';
import { getTextToken } from '@rotki/common';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

interface UseDetectTokenChainsSelectionReturn {
  /** EVM chains with accounts, filtered by the search query. */
  filtered: ComputedRef<EvmChainInfo[]>;
  /** Number of currently selected chains. */
  selectedCount: ComputedRef<number>;
  /** Whether at least one chain is selected. */
  hasSelection: ComputedRef<boolean>;
  /** Whether a token detection task is currently running. */
  isDetectingTokens: ComputedRef<boolean>;
  /** Whether every available chain (with accounts) is selected. */
  isAllSelected: ComputedRef<boolean>;
  /** Check whether a specific chain is currently selected. */
  isSelected: (chain: string) => boolean;
  /** Toggle a single chain's selection, or toggle-all when called without arguments. */
  toggle: (chain?: string) => void;
  /** Clear all selected chains. */
  reset: () => void;
  /**
   * Trigger token detection for a single chain or the current selection.
   * @returns `true` when all available chains were selected (caller should emit redetect:all).
   */
  detectChains: (chain?: string) => Promise<boolean>;
}

export function useDetectTokenChainsSelection(search: MaybeRefOrGetter<string>): UseDetectTokenChainsSelectionReturn {
  const { isTaskRunning, useIsTaskRunning } = useTaskStore();
  const { txEvmChains } = useSupportedChains();
  const { addresses } = useAccountAddresses();
  const { massDetectTokens } = useBalanceRefresh();

  const selectedChains = ref<string[]>([]);

  const chainsWithAccounts = computed<EvmChainInfo[]>(() => {
    const addressesValue = get(addresses);
    return get(txEvmChains).filter(chain => (addressesValue[chain.id] ?? []).length > 0);
  });

  const filtered = computed<EvmChainInfo[]>(() => {
    const chains = get(chainsWithAccounts);
    const query = getTextToken(toValue(search));
    if (!query)
      return chains;

    return chains.filter(item => getTextToken(item.evmChainName).includes(query) || getTextToken(item.name).includes(query));
  });

  const isDetectingTokens = useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS);

  const selectedCount = computed<number>(() => get(selectedChains).length);

  const hasSelection = computed<boolean>(() => get(selectedChains).length > 0);

  const isAllSelected = computed<boolean>(() => {
    const length = get(selectedChains).length;
    return length > 0 && length === get(chainsWithAccounts).length;
  });

  function isSelected(chain: string): boolean {
    return get(selectedChains).includes(chain);
  }

  function toggle(chain?: string): void {
    if (chain) {
      if (isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, { chain }))
        return;
      const chains = [...get(selectedChains)];
      const index = chains.indexOf(chain);
      if (index === -1)
        chains.push(chain);
      else
        chains.splice(index, 1);

      set(selectedChains, chains);
    }
    else {
      if (isTaskRunning(TaskType.FETCH_DETECTED_TOKENS))
        return;
      const filteredVal = get(filtered);
      if (get(selectedChains).length < filteredVal.length)
        set(selectedChains, filteredVal.map(item => item.id));
      else
        reset();
    }
  }

  function reset(): void {
    set(selectedChains, []);
  }

  /**
   * Triggers detection for the given chain or for all selected chains.
   * @returns `true` if all available chains were selected (caller should emit redetect:all).
   */
  async function detectChains(chain?: string): Promise<boolean> {
    if (chain) {
      await massDetectTokens([chain]);
      return false;
    }

    const selected = get(selectedChains);
    if (get(isAllSelected)) {
      return true;
    }

    await massDetectTokens(selected);
    return false;
  }

  return {
    detectChains,
    filtered,
    hasSelection,
    isAllSelected,
    isDetectingTokens,
    isSelected,
    reset,
    selectedCount,
    toggle,
  };
}
