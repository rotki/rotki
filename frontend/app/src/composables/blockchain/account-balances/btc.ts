import { Blockchain } from '@rotki/common/lib/blockchain';
import { Section } from '@/types/status';
import type { BlockchainTotal } from '@/types/blockchain';
import type {
  AssetBreakdown,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

export function useBtcAccountBalances() {
  const { balances } = storeToRefs(useBtcBalancesStore());
  const { btc, bch } = storeToRefs(useBtcAccountsStore());

  const btcAccounts = computed<BlockchainAccountWithBalance[]>(() =>
    btcAccountsWithBalances(get(btc), get(balances).btc, Blockchain.BTC),
  );

  const bchAccounts = computed<BlockchainAccountWithBalance[]>(() =>
    btcAccountsWithBalances(get(bch), get(balances).bch, Blockchain.BCH),
  );

  const { shouldShowLoadingScreen } = useStatusStore();
  const bitcoinTotals: ComputedRef<BlockchainTotal[]> = computed(() => [
    {
      chain: Blockchain.BTC,
      children: [],
      usdValue: sum(get(btcAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.BTC)),
    },
    {
      chain: Blockchain.BCH,
      children: [],
      usdValue: sum(get(bchAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN, Blockchain.BCH)),
    },
  ]);

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
    computed(() => [
      ...(asset === Blockchain.BTC.toUpperCase()
        ? getBtcBreakdown(Blockchain.BTC, get(balances).btc, get(btc))
        : []),
      ...(asset === Blockchain.BCH.toUpperCase()
        ? getBtcBreakdown(Blockchain.BCH, get(balances).bch, get(bch))
        : []),
    ]);

  return {
    btcAccounts,
    bchAccounts,
    bitcoinTotals,
    getBreakdown,
  };
}
