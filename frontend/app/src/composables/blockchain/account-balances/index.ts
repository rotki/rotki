import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef, type Ref } from 'vue';
import { type BlockchainTotal } from '@/types/blockchain';
import { sortDesc } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';
import {
  type AssetBreakdown,
  type BlockchainAccountWithBalance
} from '@/types/blockchain/accounts';

export const useAccountBalances = () => {
  const ethStore = useEthAccountBalances();
  const btcStore = useBtcAccountBalances();
  const chainStore = useChainAccountBalances();
  const { ethAccounts, eth2Accounts, ethTotals } = ethStore;
  const { btcAccounts, bchAccounts, bitcoinTotals } = btcStore;
  const {
    ksmAccounts,
    dotAccounts,
    avaxAccounts,
    optimismAccounts,
    chainTotals
  } = chainStore;

  const accounts: ComputedRef<GeneralAccount[]> = computed(() =>
    get(ethAccounts)
      .concat(get(btcAccounts))
      .concat(get(bchAccounts))
      .concat(get(ksmAccounts))
      .concat(get(dotAccounts))
      .concat(get(avaxAccounts))
      .concat(get(optimismAccounts))
      .filter((account: BlockchainAccountWithBalance) => !!account.address)
      .map((account: BlockchainAccountWithBalance) => ({
        chain: account.chain,
        address: account.address,
        label: account.label,
        tags: account.tags
      }))
  );

  const getAccountByAddress = (
    address: string,
    location: string
  ): ComputedRef<GeneralAccount | undefined> =>
    computed(() =>
      get(accounts).find(
        acc => acc.address === address && acc.chain === location
      )
    );

  const getAccountsByChain = (blockchain: Blockchain): string[] => {
    const mapping: Record<Blockchain, Ref<BlockchainAccountWithBalance[]>> = {
      [Blockchain.ETH]: ethAccounts,
      [Blockchain.ETH2]: eth2Accounts,
      [Blockchain.BTC]: btcAccounts,
      [Blockchain.BCH]: bchAccounts,
      [Blockchain.KSM]: ksmAccounts,
      [Blockchain.DOT]: dotAccounts,
      [Blockchain.AVAX]: avaxAccounts,
      [Blockchain.OPTIMISM]: optimismAccounts
    };

    const accounts = get(mapping[blockchain]);
    return accounts
      .flatMap(account => {
        const acc = [account.address.toLocaleLowerCase()];
        if ('xpub' in account) {
          acc.push(account.xpub);
        }
        return acc;
      })
      .filter(uniqueStrings);
  };

  const blockchainTotals: ComputedRef<BlockchainTotal[]> = computed(() =>
    get(ethTotals)
      .concat(get(bitcoinTotals))
      .concat(get(chainTotals))
      .filter(item => item.usdValue.gt(0))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue))
  );

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
};
