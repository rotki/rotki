import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

export const useDecodingStatusStore = defineStore('history/decoding-status', () => {
  const { matchChain } = useSupportedChains();

  /**
   * Resolve a chain identifier to the canonical id everything else in the app uses.
   *
   * Producers disagree on spelling: the EVM decoder reports `ChainID.to_name()` (`ethereum`), a
   * chain reporting through `SupportedBlockchain` sends the enum value (`BTC`), the frontend uses
   * the chain id (`eth`). Keyed raw, one chain occupies several entries.
   *
   * `matchChain`, not `getChain`: the latter answers `Blockchain.ETH` for anything it does not
   * recognise, filing that chain's counts under Ethereum and sending Ethereum's id to the decode
   * endpoint. A chain the backend ships first is always unmatched, so it keeps a stable lowercase
   * key instead, which is what the backend calls it anyway.
   */
  const canonicalChain = (chain: string): string => matchChain(chain) ?? chain.toLowerCase();

  const undecodedTransactionsStatus = shallowRef<Record<string, EvmUnDecodedTransactionsData>>({});

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    const key = canonicalChain(data.chain);
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [key]: { ...data, chain: key },
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
  };

  const resetUndecodedTransactionsStatus = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] =>
    Object.values(get(undecodedTransactionsStatus));

  return {
    decodingStatus,
    getUndecodedTransactionStatus,
    resetUndecodedTransactionsStatus,
    setUndecodedTransactionsStatus,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDecodingStatusStore, import.meta.hot));
