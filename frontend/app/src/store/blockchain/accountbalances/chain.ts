import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';

import {
  type AccountWithBalance,
  type AssetBreakdown
} from '@/store/balances/types';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';
import { useChainBalancesStore } from '@/store/blockchain/balances/chains';
import { type BlockchainTotal } from '@/types/blockchain';
import { Section } from '@/types/status';
import {
  accountsWithBalances,
  getBlockchainBreakdown,
  sum
} from '@/utils/balances';

export const useChainAccountBalancesStore = defineStore(
  'blockchain/accountbalances/chain',
  () => {
    const { ksm, dot, avax, optimism } = storeToRefs(useChainsAccountsStore());
    const { balances } = storeToRefs(useChainBalancesStore());

    const ksmAccounts: ComputedRef<AccountWithBalance[]> = computed(() => {
      return accountsWithBalances(get(ksm), get(balances).KSM, Blockchain.KSM);
    });

    const dotAccounts: ComputedRef<AccountWithBalance[]> = computed(() => {
      return accountsWithBalances(get(dot), get(balances).DOT, Blockchain.DOT);
    });

    const avaxAccounts: ComputedRef<AccountWithBalance[]> = computed(() => {
      return accountsWithBalances(
        get(avax),
        get(balances).AVAX,
        Blockchain.AVAX
      );
    });

    const optimismAccounts: ComputedRef<AccountWithBalance[]> = computed(() => {
      return accountsWithBalances(
        get(optimism),
        get(balances).OPTIMISM,
        Blockchain.OPTIMISM
      );
    });

    const { shouldShowLoadingScreen } = useSectionLoading();
    const chainTotals: ComputedRef<BlockchainTotal[]> = computed(() => {
      return [
        {
          chain: Blockchain.KSM,
          children: [],
          usdValue: sum(get(ksmAccounts)),
          loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_KSM))
        },
        {
          chain: Blockchain.DOT,
          children: [],
          usdValue: sum(get(dotAccounts)),
          loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_DOT))
        },
        {
          chain: Blockchain.AVAX,
          children: [],
          usdValue: sum(get(avaxAccounts)),
          loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_AVAX))
        },
        {
          chain: Blockchain.OPTIMISM,
          children: [],
          usdValue: sum(get(optimismAccounts)),
          loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_OPTIMISM))
        }
      ];
    });

    const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
      computed(() => [
        ...getBlockchainBreakdown(
          Blockchain.KSM,
          get(balances).KSM,
          get(ksmAccounts),
          asset
        ),
        ...getBlockchainBreakdown(
          Blockchain.DOT,
          get(balances).DOT,
          get(dotAccounts),
          asset
        ),
        ...getBlockchainBreakdown(
          Blockchain.AVAX,
          get(balances).AVAX,
          get(dotAccounts),
          asset
        ),
        ...getBlockchainBreakdown(
          Blockchain.OPTIMISM,
          get(balances).OPTIMISM,
          get(optimismAccounts),
          asset
        )
      ]);

    return {
      ksmAccounts,
      dotAccounts,
      avaxAccounts,
      optimismAccounts,
      chainTotals,
      getBreakdown
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useChainAccountBalancesStore, import.meta.hot)
  );
}
