import {
  type AssetBalance,
  type AssetBalanceWithPrice,
  type Balance,
  type BigNumber,
  type HasBalance
} from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { groupBy } from 'lodash';
import { bigNumberSum } from '@/filters';
import {
  type BtcAccountData,
  type GeneralAccountData
} from '@/services/types-api';
import {
  type AccountWithBalance,
  type AssetBreakdown,
  type BlockchainAccountWithBalance
} from '@/store/balances/types';
import { type AssetBalances } from '@/types/balances';
import {
  type BlockchainAssetBalances,
  type BtcBalances
} from '@/types/blockchain/balances';
import { NoPrice, Zero, sortDesc, zeroBalance } from '@/utils/bignumbers';
import { assetSum, balanceSum } from '@/utils/calculation';
import { getTags } from '@/utils/tags';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

export const removeZeroAssets = (entries: AssetBalances): AssetBalances => {
  const balances = { ...entries };
  for (const asset in entries) {
    if (balances[asset].amount.isZero()) delete balances[asset];
  }
  return balances;
};

export const mergeAssociatedAssets = (
  totals: MaybeRef<AssetBalances>,
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>
): ComputedRef<AssetBalances> =>
  computed(() => {
    const ownedAssets: AssetBalances = {};

    for (const [asset, value] of Object.entries(get(totals))) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);
      const ownedAsset = ownedAssets[associatedAsset];
      if (!ownedAsset) {
        ownedAssets[associatedAsset] = { ...value };
      } else {
        ownedAssets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
      }
    }
    return ownedAssets;
  });

export const mergeAssetBalances = (
  a: AssetBalances,
  b: AssetBalances
): AssetBalances => {
  const merged = { ...a };
  for (const [asset, value] of Object.entries(b)) {
    if (merged[asset]) {
      merged[asset] = { ...balanceSum(merged[asset], value) };
    } else {
      merged[asset] = value;
    }
  }
  return merged;
};

export const appendAssetBalance = (
  value: AssetBalance,
  assets: AssetBalances,
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>
): void => {
  const identifier = getAssociatedAssetIdentifier(value.asset);
  const associatedAsset: string = get(identifier);
  const ownedAsset = assets[associatedAsset];
  if (!ownedAsset) {
    assets[associatedAsset] = { ...value };
  } else {
    assets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
  }
};

export const sumAssetBalances = (
  balances: AssetBalances[],
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>
): AssetBalances => {
  const summed: AssetBalances = {};
  for (const balance of balances) {
    for (const [asset, value] of Object.entries(balance)) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);

      if (summed[associatedAsset]) {
        summed[associatedAsset] = balanceSum(value, summed[associatedAsset]);
      } else {
        summed[associatedAsset] = { ...value };
      }
    }
  }
  return summed;
};

const toSortedAndGroupedArray = <T extends Balance>(
  ownedAssets: AssetBalances,
  isIgnored: (asset: string) => boolean,
  groupMultiChain: boolean,
  map: (asset: string) => T & { asset: string }
): T[] => {
  const { assetInfo } = useAssetInfoRetrieval();
  const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());

  const data = Object.keys(ownedAssets)
    .filter(asset => !isIgnored(asset))
    .map(map);

  if (!groupMultiChain)
    return data.sort((a, b) => sortDesc(a.usdValue, b.usdValue));

  const groupedBalances = groupBy(data, balance => {
    const info = get(assetInfo(balance.asset));

    if (info?.collectionId) {
      return `collection-${info.collectionId}`;
    }

    return balance.asset;
  });

  const mapped: T[] = [];

  Object.keys(groupedBalances).forEach(key => {
    const grouped = groupedBalances[key];
    const isAssetCollection = key.startsWith('collection-');
    const collectionKey = key.split('collection-')[1];
    const assetCollectionInfo = !isAssetCollection
      ? false
      : get(fetchedAssetCollections)?.[collectionKey];

    if (assetCollectionInfo && grouped.length > 1) {
      const sumBalance = grouped.reduce(
        (accumulator, currentBalance) =>
          balanceSum(accumulator, currentBalance),
        zeroBalance()
      );

      const parent: T = {
        ...grouped[0],
        ...sumBalance,
        breakdown: grouped
      };

      mapped.push(parent);
    } else {
      mapped.push(...grouped);
    }
  });

  return mapped.sort((a, b) => sortDesc(a.usdValue, b.usdValue));
};

export const toSortedAssetBalanceWithPrice = (
  ownedAssets: AssetBalances,
  isIgnored: (asset: string) => boolean,
  getPrice: (asset: string) => ComputedRef<BigNumber | null | undefined>,
  groupMultiChain = true
): AssetBalanceWithPrice[] => {
  return toSortedAndGroupedArray(
    ownedAssets,
    isIgnored,
    groupMultiChain,
    asset => ({
      asset,
      amount: ownedAssets[asset].amount,
      usdValue: ownedAssets[asset].usdValue,
      usdPrice: get(getPrice(asset)) ?? NoPrice
    })
  );
};

export const toSortedAssetBalanceArray = (
  ownedAssets: AssetBalances,
  isIgnored: (asset: string) => boolean,
  groupMultiChain = false
): AssetBalance[] =>
  toSortedAndGroupedArray(ownedAssets, isIgnored, groupMultiChain, asset => ({
    asset,
    amount: ownedAssets[asset].amount,
    usdValue: ownedAssets[asset].usdValue
  }));

const getNativeAsset = (chain: Blockchain) => {
  if (chain === Blockchain.OPTIMISM) {
    return 'eip155:10/erc20:0x4200000000000000000000000000000000000042';
  }
  return chain;
};

export const accountsWithBalances = (
  accounts: GeneralAccountData[],
  balances: BlockchainAssetBalances,
  blockchain: Exclude<Blockchain, 'BTC'>
): AccountWithBalance[] => {
  const data: AccountWithBalance[] = [];
  for (const account of accounts) {
    const accountAssets = balances[account.address];
    const nativeAsset = getNativeAsset(blockchain);

    const balance: Balance = accountAssets
      ? {
          amount: accountAssets?.assets[nativeAsset]?.amount ?? Zero,
          usdValue: assetSum(accountAssets.assets)
        }
      : zeroBalance();

    data.push({
      address: account.address,
      label: account.label ?? '',
      tags: account.tags ?? [],
      chain: blockchain,
      nativeAsset: nativeAsset !== blockchain ? nativeAsset : undefined,
      balance
    });
  }
  return data;
};

export const btcAccountsWithBalances = (
  accountsData: BtcAccountData,
  balances: BtcBalances,
  blockchain: Blockchain.BTC | Blockchain.BCH
): BlockchainAccountWithBalance[] => {
  const accounts: BlockchainAccountWithBalance[] = [];

  const { standalone, xpubs } = accountsData;
  for (const { address, label, tags } of standalone) {
    const balance = balances.standalone?.[address] ?? zeroBalance();
    accounts.push({
      address,
      label: label ?? '',
      tags: tags ?? [],
      chain: blockchain,
      balance
    });
  }

  for (const { addresses, derivationPath, label, tags, xpub } of xpubs) {
    accounts.push({
      chain: blockchain,
      xpub,
      derivationPath: derivationPath ?? '',
      address: '',
      label: label ?? '',
      tags: tags ?? [],
      balance: zeroBalance()
    });

    if (!addresses) {
      continue;
    }

    for (const { address, label, tags } of addresses) {
      const { xpubs } = balances;
      if (!xpubs) {
        continue;
      }
      const index = xpubs.findIndex(xpub => xpub.addresses[address]) ?? -1;
      const balance =
        index >= 0 ? xpubs[index].addresses[address] : zeroBalance();
      accounts.push({
        chain: blockchain,
        xpub,
        derivationPath: derivationPath ?? '',
        address,
        label: label ?? '',
        tags: tags ?? [],
        balance
      });
    }
  }

  return accounts;
};

export const sum = (accounts: HasBalance[]): BigNumber => {
  return bigNumberSum(accounts.map(account => account.balance.usdValue));
};

export const getBlockchainBreakdown = (
  blockchain: Blockchain,
  balances: BlockchainAssetBalances,
  accounts: GeneralAccountData[],
  asset: string
): AssetBreakdown[] => {
  const breakdown: AssetBreakdown[] = [];
  for (const address in balances) {
    const balance = balances[address];
    const assetBalance = balance.assets[asset];
    if (!assetBalance) {
      continue;
    }
    const tags = getTags(accounts, address);
    breakdown.push({
      address,
      location: blockchain,
      balance: assetBalance,
      tags
    });
  }
  return breakdown;
};

export const getBtcBreakdown = (
  blockchain: Blockchain,
  balances: BtcBalances,
  accounts: BtcAccountData
): AssetBreakdown[] => {
  const breakdown: AssetBreakdown[] = [];
  const { standalone, xpubs } = balances;
  if (standalone) {
    for (const address in standalone) {
      const balance = standalone[address];
      const tags = getTags(accounts.standalone, address);
      breakdown.push({
        address,
        location: blockchain,
        balance,
        tags
      });
    }
  }

  if (xpubs) {
    for (const [i, xpub] of xpubs.entries()) {
      const addresses = xpub.addresses;
      const tags = accounts?.xpubs[i].tags;
      for (const address in addresses) {
        const balance = addresses[address];

        breakdown.push({
          address,
          location: blockchain,
          balance,
          tags
        });
      }
    }
  }
  return breakdown;
};
