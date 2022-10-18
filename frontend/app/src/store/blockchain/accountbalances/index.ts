import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { ComputedRef, Ref } from 'vue';
import {
  AssetBreakdown,
  BlockchainAccountWithBalance
} from '@/store/balances/types';
import { useBtcAccountBalancesStore } from '@/store/blockchain/accountbalances/btc';
import { useChainAccountBalancesStore } from '@/store/blockchain/accountbalances/chain';
import { useEthAccountBalancesStore } from '@/store/blockchain/accountbalances/eth';
import { BlockchainTotal } from '@/types/blockchain';
import { sortDesc } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

export const useAccountBalancesStore = defineStore(
  'blockchain/accountbalances',
  () => {
    const ethStore = useEthAccountBalancesStore();
    const btcStore = useBtcAccountBalancesStore();
    const chainStore = useChainAccountBalancesStore();
    const { ethAccounts, eth2Accounts, ethTotals } = storeToRefs(ethStore);
    const { btcAccounts, bchAccounts, bitcoinTotals } = storeToRefs(btcStore);
    const { ksmAccounts, dotAccounts, avaxAccounts, chainTotals } =
      storeToRefs(chainStore);

    const accounts: ComputedRef<GeneralAccount[]> = computed(() => {
      return get(ethAccounts)
        .concat(get(btcAccounts))
        .concat(get(bchAccounts))
        .concat(get(ksmAccounts))
        .concat(get(dotAccounts))
        .concat(get(avaxAccounts))
        .filter((account: BlockchainAccountWithBalance) => !!account.address)
        .map((account: BlockchainAccountWithBalance) => ({
          chain: account.chain,
          address: account.address,
          label: account.label,
          tags: account.tags
        }));
    });

    const getAccountByAddress = (
      address: string
    ): ComputedRef<GeneralAccount | undefined> =>
      computed(() => {
        return get(accounts).find(acc => acc.address === address);
      });

    const getAccountsByChain = (blockchain: Blockchain): string[] => {
      const mapping: Record<Blockchain, Ref<BlockchainAccountWithBalance[]>> = {
        [Blockchain.ETH]: ethAccounts,
        [Blockchain.ETH2]: eth2Accounts,
        [Blockchain.BTC]: btcAccounts,
        [Blockchain.BCH]: bchAccounts,
        [Blockchain.KSM]: ksmAccounts,
        [Blockchain.DOT]: dotAccounts,
        [Blockchain.AVAX]: avaxAccounts
      };

      const accounts = get(mapping[blockchain]);
      return accounts
        .map(account => {
          const acc = [account.address.toLocaleLowerCase()];
          if ('xpub' in account) {
            acc.push(account.xpub);
          }
          return acc;
        })
        .flat()
        .filter(uniqueStrings);
    };

    const blockchainTotals: ComputedRef<BlockchainTotal[]> = computed(() => {
      return get(ethTotals)
        .concat(get(bitcoinTotals))
        .concat(get(chainTotals))
        .filter(item => item.usdValue.gt(0))
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
    });

    const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
      computed(() =>
        get(ethStore.getBreakdown(asset))
          .concat(get(btcStore.getBreakdown(asset)))
          .concat(get(chainStore.getBreakdown(asset)))
      );

    return {
      accounts,
      blockchainTotals,
      getAccountByAddress,
      getAccountsByChain,
      getBreakdown
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountBalancesStore, import.meta.hot)
  );
}
