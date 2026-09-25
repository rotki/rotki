import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { blockchainValue } from '@/modules/balances/aggregation/core/location-totals';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

export interface HoldingsInputs {
  readonly contributions: ComputedRef<SourceContribution[]>;
  /** NFT value in the main currency, or `undefined` when NFTs do not count toward net worth. */
  readonly nfts: ComputedRef<BigNumber | undefined>;
  readonly liabilities: ComputedRef<BigNumber>;
  readonly locationOfChain: (chain: string) => string | undefined;
}

/**
 * Reads every balance source the dashboard breaks net worth into.
 *
 * @remarks
 * Each value leaves ignored assets out, as net worth does, so the sources minus liabilities add up
 * to the headline. That is not true of every existing per-source total: the blockchain card summed
 * ignored assets, and so does `manualBalanceByLocation`.
 */
export function useHoldingsContributions(): HoldingsInputs {
  const { balances, manualBalances } = storeToRefs(useBalancesStore());
  const { nftValue } = storeToRefs(useStatisticsStore());
  const { isAssetIgnored } = useAssetsStore();
  const { isPricePending } = usePriceUtils();
  const { useLiabilities } = useAggregatedBalances();
  const { exchanges } = useExchangeData();
  const { banks } = useBankData();
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();
  const nftsInNetValue = useSetting('nftsInNetValue');
  const liabilityBalances = useLiabilities();

  const chainLocations = computed<Map<string, string>>(() => {
    const byChain = new Map<string, string>();
    for (const { identifier } of get(tradeLocations)) {
      const chain = matchChain(identifier);
      if (chain && !byChain.has(chain))
        byChain.set(chain, identifier);
    }
    return byChain;
  });

  function isChainPricePending(accounts: Balances[string]): boolean {
    return Object.values(accounts).some(({ assets }) => Object.keys(assets ?? {})
      .some(asset => !isAssetIgnored(asset) && isPricePending(asset)));
  }

  function chainContribution(chain: string, accounts: Balances[string]): SourceContribution {
    return {
      chain,
      kind: SourceKind.BLOCKCHAIN,
      loading: isChainPricePending(accounts),
      value: blockchainValue({ [chain]: accounts }, isAssetIgnored),
    };
  }

  const contributions = computed<SourceContribution[]>(() => [
    ...Object.entries(get(balances)).map(([chain, accounts]) => chainContribution(chain, accounts)),
    ...get(exchanges).map(({ location, total }): SourceContribution => ({ kind: SourceKind.EXCHANGE, loading: false, location, value: total })),
    ...get(banks).map(({ location, total }): SourceContribution => ({ kind: SourceKind.BANK, loading: false, location, value: total })),
    ...get(manualBalances)
      .filter(({ asset }) => !isAssetIgnored(asset))
      .map(({ location, value }): SourceContribution => ({ kind: SourceKind.MANUAL, loading: false, location, value })),
  ]);

  return {
    contributions,
    liabilities: computed<BigNumber>(() => bigNumberSum(get(liabilityBalances).map(({ value }) => value))),
    locationOfChain: chain => get(chainLocations).get(chain),
    nfts: computed<BigNumber | undefined>(() => (get(nftsInNetValue) ? get(nftValue) : undefined)),
  };
}
