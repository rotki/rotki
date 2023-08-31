import { Blockchain } from '@rotki/common/lib/blockchain';
import { type AssetBalance } from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import isEmpty from 'lodash/isEmpty';
import { type BlockchainAssetBalances } from '@/types/blockchain/balances';

export const useAccountDetails = (
  blockchain: MaybeRef<Blockchain>,
  address: MaybeRef<string> = ''
) => {
  const ethBalancesStore = useEthBalancesStore();
  const { getLoopringAssetBalances } = ethBalancesStore;
  const { balances: ethBalances, loopring } = storeToRefs(ethBalancesStore);
  const { balances: chainBalances } = storeToRefs(useChainBalancesStore());
  const { isAssetIgnored } = useIgnoredAssetsStore();

  const balances: ComputedRef<BlockchainAssetBalances> = computed(() => {
    const chain = get(blockchain);
    if (chain === Blockchain.ETH) {
      return get(ethBalances)[chain];
    } else if (chain === Blockchain.OPTIMISM) {
      return get(chainBalances)[chain];
    } else if (chain === Blockchain.POLYGON_POS) {
      return get(chainBalances)[chain];
    } else if (chain === Blockchain.ARBITRUM_ONE) {
      return get(chainBalances)[chain];
    }
    return {};
  });

  const assets: ComputedRef<AssetBalance[]> = computed(() => {
    const accountAddress = get(address);
    const ethAccount = get(balances)[accountAddress];
    if (!ethAccount || isEmpty(ethAccount)) {
      return [];
    }

    return Object.entries(ethAccount.assets)
      .filter(([asset]) => !get(isAssetIgnored(asset)))
      .map(
        ([asset, { amount, usdValue }]) =>
          ({
            asset,
            amount,
            usdValue
          }) as AssetBalance
      );
  });

  const liabilities: ComputedRef<AssetBalance[]> = computed(() => {
    const accountAddress = get(address);
    const account = get(balances)[accountAddress];
    if (!account || isEmpty(account)) {
      return [];
    }

    return Object.entries(account.liabilities)
      .filter(([asset]) => !get(isAssetIgnored(asset)))
      .map(
        ([asset, { amount, usdValue }]) =>
          ({
            asset,
            amount,
            usdValue
          }) as AssetBalance
      );
  });

  const hasDetails = (address: MaybeRef<string>) => {
    const accountAddress = get(address);
    const account = get(balances)[accountAddress];

    if (!account || isEmpty(account)) {
      return false;
    }

    const totalAssets = Object.entries(account.assets).length;
    const totalLiabilities = Object.entries(account.liabilities).length;
    let totalLoopringBalances = 0;
    if (get(blockchain) === Blockchain.ETH) {
      const loopringBalance = get(loopring)[accountAddress] || {};
      totalLoopringBalances = Object.entries(loopringBalance).length;
    }

    return totalAssets + totalLiabilities + totalLoopringBalances > 0;
  };

  const getLoopringBalances = (
    address: MaybeRef<string>
  ): ComputedRef<AssetBalance[]> =>
    computed(() => {
      if (get(blockchain) !== Blockchain.ETH) {
        return [];
      }
      const ownedAssets = getLoopringAssetBalances(address);
      return toSortedAssetBalanceArray(get(ownedAssets), asset =>
        get(isAssetIgnored(asset))
      );
    });

  const loopringBalances: ComputedRef<AssetBalance[]> =
    getLoopringBalances(address);

  return {
    assets,
    liabilities,
    loopringBalances,
    getLoopringBalances,
    hasDetails
  };
};
