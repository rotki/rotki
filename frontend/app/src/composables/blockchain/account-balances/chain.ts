import { Blockchain } from '@rotki/common/lib/blockchain';
import { Section } from '@/types/status';
import type { BlockchainTotal } from '@/types/blockchain';
import type {
  AccountWithBalance,
  AssetBreakdown,
} from '@/types/blockchain/accounts';

export function useChainAccountBalances() {
  const { ksm, dot, avax, optimism, polygon, arbitrum, base, gnosis, scroll }
    = storeToRefs(useChainsAccountsStore());
  const { balances } = storeToRefs(useChainBalancesStore());

  const ksmAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(ksm), get(balances).ksm, Blockchain.KSM),
  );

  const dotAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(dot), get(balances).dot, Blockchain.DOT),
  );

  const avaxAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(avax), get(balances).avax, Blockchain.AVAX),
  );

  const optimismAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(
      get(optimism),
      get(balances).optimism,
      Blockchain.OPTIMISM,
    ),
  );

  const polygonAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(
      get(polygon),
      get(balances).polygon_pos,
      Blockchain.POLYGON_POS,
    ),
  );

  const arbitrumAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(
      get(arbitrum),
      get(balances).arbitrum_one,
      Blockchain.ARBITRUM_ONE,
    ),
  );

  const baseAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(base), get(balances).base, Blockchain.BASE),
  );

  const gnosisAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(gnosis), get(balances).gnosis, Blockchain.GNOSIS),
  );

  const scrollAccounts: ComputedRef<AccountWithBalance[]> = computed(() =>
    accountsWithBalances(get(scroll), get(balances).scroll, Blockchain.SCROLL),
  );

  const { shouldShowLoadingScreen } = useStatusStore();
  const chainTotals: ComputedRef<BlockchainTotal[]> = computed(() => [
    {
      chain: Blockchain.KSM,
      children: [],
      usdValue: sum(get(ksmAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.KSM)),
    },
    {
      chain: Blockchain.DOT,
      children: [],
      usdValue: sum(get(dotAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.DOT)),
    },
    {
      chain: Blockchain.AVAX,
      children: [],
      usdValue: sum(get(avaxAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.AVAX)),
    },
    {
      chain: Blockchain.OPTIMISM,
      children: [],
      usdValue: sum(get(optimismAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.OPTIMISM)),
    },
    {
      chain: Blockchain.POLYGON_POS,
      children: [],
      usdValue: sum(get(polygonAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.POLYGON_POS)),
    },
    {
      chain: Blockchain.ARBITRUM_ONE,
      children: [],
      usdValue: sum(get(arbitrumAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.ARBITRUM_ONE)),
    },
    {
      chain: Blockchain.BASE,
      children: [],
      usdValue: sum(get(baseAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.BASE)),
    },
    {
      chain: Blockchain.GNOSIS,
      children: [],
      usdValue: sum(get(gnosisAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.GNOSIS)),
    },
    {
      chain: Blockchain.SCROLL,
      children: [],
      usdValue: sum(get(scrollAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.SCROLL)),
    },
  ]);

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
    computed(() => [
      ...getBlockchainBreakdown(
        Blockchain.KSM,
        get(balances).ksm,
        get(ksmAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.DOT,
        get(balances).dot,
        get(dotAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.AVAX,
        get(balances).avax,
        get(dotAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.OPTIMISM,
        get(balances).optimism,
        get(optimismAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.POLYGON_POS,
        get(balances).polygon_pos,
        get(polygonAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.ARBITRUM_ONE,
        get(balances).arbitrum_one,
        get(arbitrumAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.BASE,
        get(balances).base,
        get(baseAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.GNOSIS,
        get(balances).gnosis,
        get(gnosisAccounts),
        asset,
      ),
      ...getBlockchainBreakdown(
        Blockchain.SCROLL,
        get(balances).scroll,
        get(scrollAccounts),
        asset,
      ),
    ]);

  return {
    ksmAccounts,
    dotAccounts,
    avaxAccounts,
    optimismAccounts,
    polygonAccounts,
    arbitrumAccounts,
    baseAccounts,
    gnosisAccounts,
    scrollAccounts,
    chainTotals,
    getBreakdown,
  };
}
