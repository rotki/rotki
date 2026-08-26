import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

export interface DecodingStatusEntry extends EvmUnDecodedTransactionsData {
  cancelled?: boolean;
}

export const useDecodingStatusStore = defineStore('history/decoding-status', () => {
  const { matchChain } = useSupportedChains();

  /**
   * Resolve a chain identifier to the canonical id everything else in the app uses.
   *
   * Producers disagree on spelling: the EVM decoder reports `ChainID.to_name()` (`ethereum`), a
   * chain reporting through `SupportedBlockchain` sends the enum value (`BTC`), the frontend uses
   * the chain id (`eth`). Keyed raw, one chain occupies several entries and
   * `markDecodingCancelled` misses the one it means to cancel.
   *
   * `matchChain`, not `getChain`: the latter answers `Blockchain.ETH` for anything it does not
   * recognise, filing that chain's progress under Ethereum and sending Ethereum's id to the decode
   * endpoint. A chain the backend ships first is always unmatched, so it keeps a stable lowercase
   * key instead, which is what the backend calls it anyway.
   */
  const canonicalChain = (chain: string): string => matchChain(chain) ?? chain.toLowerCase();

  const undecodedTransactionsStatus = shallowRef<Record<string, EvmUnDecodedTransactionsData>>({});
  const decodingSyncProgress = shallowRef<Record<string, DecodingStatusEntry>>({});
  const decodingSyncing = shallowRef<boolean>(false);

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  const decodingSyncStatus = computed<DecodingStatusEntry[]>(() =>
    Object.values(get(decodingSyncProgress)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    const key = canonicalChain(data.chain);
    const entry: EvmUnDecodedTransactionsData = { ...data, chain: key };

    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [key]: entry,
    });

    if (!get(decodingSyncing))
      return;

    const currentSync = get(decodingSyncProgress);
    if (currentSync[key]?.cancelled)
      return;

    set(decodingSyncProgress, {
      ...currentSync,
      [key]: entry,
    });
  };

  const updateUndecodedTransactionsStatus = (data: Record<string, EvmUnDecodedTransactionsData>): void => {
    const canonical = Object.fromEntries(
      Object.entries(data).map(([chain, status]) => {
        const key = canonicalChain(chain);
        return [key, { ...status, chain: key }];
      }),
    );

    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      ...canonical,
    });

    if (!get(decodingSyncing))
      return;

    const currentSyncProgress = get(decodingSyncProgress);
    const updatedSyncProgress = { ...currentSyncProgress };
    let hasChanges = false;

    for (const [chain, status] of Object.entries(canonical)) {
      const existing = currentSyncProgress[chain];
      if (existing?.cancelled)
        continue;

      if (!existing || status.processed >= existing.processed) {
        updatedSyncProgress[chain] = status;
        hasChanges = true;
      }
    }

    if (hasChanges)
      set(decodingSyncProgress, updatedSyncProgress);
  };

  const markDecodingCancelled = (chain: string): void => {
    const key = canonicalChain(chain);
    const current = get(decodingSyncProgress);
    const existing = current[key];
    if (existing) {
      set(decodingSyncProgress, {
        ...current,
        [key]: { ...existing, cancelled: true },
      });
    }
  };

  const resetUndecodedTransactionsStatus = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const resetDecodingSyncProgress = (): void => {
    set(decodingSyncProgress, {});
    set(decodingSyncing, true);
  };

  /**
   * Re-arm the progress gate without discarding what is already recorded.
   *
   * `decodingSyncing` is the only gate on both writers of `decodingSyncProgress`, and
   * `stopDecodingSyncProgress` runs whenever a sync's run settles. A follow-up wave of the *same*
   * sync therefore has to turn it back on or its decode is invisible — the panel would sit on the
   * earlier wave's finished rows and read complete while work was still running. It must not clear
   * `decodingSyncProgress`, which is exactly what makes this distinct from
   * {@link resetDecodingSyncProgress}.
   */
  const resumeDecodingSyncProgress = (): void => {
    set(decodingSyncing, true);
  };

  const stopDecodingSyncProgress = (): void => {
    set(decodingSyncing, false);
  };

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] =>
    Object.values(get(undecodedTransactionsStatus));

  return {
    decodingStatus,
    decodingSyncProgress,
    decodingSyncStatus,
    decodingSyncing,
    getUndecodedTransactionStatus,
    markDecodingCancelled,
    resetDecodingSyncProgress,
    resetUndecodedTransactionsStatus,
    resumeDecodingSyncProgress,
    setUndecodedTransactionsStatus,
    stopDecodingSyncProgress,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDecodingStatusStore, import.meta.hot));
