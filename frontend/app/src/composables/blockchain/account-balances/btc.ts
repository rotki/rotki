import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { type BlockchainTotal } from '@/types/blockchain';
import { Section } from '@/types/status';
import {
  type AssetBreakdown,
  type BlockchainAccountWithBalance
} from '@/types/blockchain/accounts';

export const useBtcAccountBalances = () => {
  const { balances } = storeToRefs(useBtcBalancesStore());
  const { btc, bch } = storeToRefs(useBtcAccountsStore());

  const btcAccounts = computed<BlockchainAccountWithBalance[]>(() =>
    btcAccountsWithBalances(get(btc), get(balances).btc, Blockchain.BTC)
  );

  const bchAccounts = computed<BlockchainAccountWithBalance[]>(() =>
    btcAccountsWithBalances(get(bch), get(balances).bch, Blockchain.BCH)
  );

  const { shouldShowLoadingScreen } = useStatusStore();
  const bitcoinTotals: ComputedRef<BlockchainTotal[]> = computed(() => [
    {
      chain: Blockchain.BTC,
      children: [],
      usdValue: sum(get(btcAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_BTC))
    },
    {
      chain: Blockchain.BCH,
      children: [],
      usdValue: sum(get(bchAccounts)),
      loading: get(shouldShowLoadingScreen(Section.BLOCKCHAIN_BCH))
    }
  ]);

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
    computed(() => [
      ...(asset === Blockchain.BTC
        ? getBtcBreakdown(Blockchain.BTC, get(balances).btc, get(btc))
        : []),
      ...(asset === Blockchain.BCH
        ? getBtcBreakdown(Blockchain.BCH, get(balances).bch, get(bch))
        : [])
    ]);

  return {
    btcAccounts,
    bchAccounts,
    bitcoinTotals,
    getBreakdown
  };
};
