import { Blockchain } from '@rotki/common/lib/blockchain';
import { ComputedRef } from 'vue';
import { useSectionLoading } from '@/composables/common';
import { AccountWithBalance, AssetBreakdown } from '@/store/balances/types';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';
import { useChainBalancesStore } from '@/store/blockchain/balances/chains';
import { BlockchainTotal } from '@/types/blockchain';
import { Section } from '@/types/status';
import {
  accountsWithBalances,
  getBlockchainBreakdown,
  sum
} from '@/utils/balances';

export const useChainAccountBalancesStore = defineStore(
  'blockchain/accountbalances/chain',
  () => {
    const { ksm, dot, avax } = storeToRefs(useChainsAccountsStore());
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
        )
      ]);

    return {
      ksmAccounts,
      dotAccounts,
      avaxAccounts,
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
