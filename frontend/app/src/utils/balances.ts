import type {
  AssetBalance,
  Balance,
  BigNumber,
  HasBalance,
} from '@rotki/common';
import type { Blockchain } from '@rotki/common/lib/blockchain';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBalances } from '@/types/balances';
import type {
  BlockchainAssetBalances,
  BtcBalances,
} from '@/types/blockchain/balances';
import type {
  AccountWithBalance,
  AssetBreakdown,
  BlockchainAccountWithBalance,
  BtcAccountData,
  GeneralAccountData,
} from '@/types/blockchain/accounts';
import type { Writeable } from '@/types';

export function removeZeroAssets(entries: AssetBalances): AssetBalances {
  const balances = { ...entries };
  for (const asset in entries) {
    if (balances[asset].amount.isZero())
      delete balances[asset];
  }
  return balances;
}

export function mergeAssociatedAssets(totals: MaybeRef<AssetBalances>, getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>): ComputedRef<AssetBalances> {
  return computed(() => {
    const ownedAssets: AssetBalances = {};

    for (const [asset, value] of Object.entries(get(totals))) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);
      const ownedAsset = ownedAssets[associatedAsset];
      if (!ownedAsset)
        ownedAssets[associatedAsset] = { ...value };
      else
        ownedAssets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
    }
    return ownedAssets;
  });
}

export function mergeAssetBalances(a: AssetBalances, b: AssetBalances): AssetBalances {
  const merged = { ...a };
  for (const [asset, value] of Object.entries(b)) {
    if (merged[asset])
      merged[asset] = { ...balanceSum(merged[asset], value) };
    else
      merged[asset] = value;
  }
  return merged;
}

export function groupAssetBreakdown(breakdowns: AssetBreakdown[], groupBy: (item: AssetBreakdown) => string = (item: AssetBreakdown) =>
  item.location + item.address): AssetBreakdown[] {
  const initial: Record<string, Writeable<AssetBreakdown>> = {};
  const grouped = breakdowns.reduce((acc, breakdown) => {
    const key = groupBy(breakdown);
    if (!acc[key])
      acc[key] = { ...breakdown, balance: zeroBalance(), ...zeroBalance() };

    const balance = balanceSum(acc[key].balance, breakdown.balance);
    acc[key].balance = balance;
    acc[key].amount = balance.amount;
    acc[key].usdValue = balance.usdValue;
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) =>
    sortDesc(a.balance.usdValue, b.balance.usdValue),
  );
}

export function appendAssetBalance(value: AssetBalance, assets: AssetBalances, getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>): void {
  const identifier = getAssociatedAssetIdentifier(value.asset);
  const associatedAsset: string = get(identifier);
  const ownedAsset = assets[associatedAsset];
  if (!ownedAsset)
    assets[associatedAsset] = { ...value };
  else
    assets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
}

export function sumAssetBalances(balances: AssetBalances[], getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>): AssetBalances {
  const summed: AssetBalances = {};
  for (const balance of balances) {
    for (const [asset, value] of Object.entries(balance)) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);

      if (summed[associatedAsset])
        summed[associatedAsset] = balanceSum(value, summed[associatedAsset]);
      else
        summed[associatedAsset] = { ...value };
    }
  }
  return summed;
}

export function accountsWithBalances(accounts: GeneralAccountData[], balances: BlockchainAssetBalances, blockchain: Exclude<Blockchain, Blockchain.BTC>): AccountWithBalance[] {
  const data: AccountWithBalance[] = [];
  const { getNativeAsset } = useSupportedChains();
  const nativeAsset = getNativeAsset(blockchain);

  for (const account of accounts) {
    const accountAssets = balances[account.address];

    const balance: Balance = accountAssets
      ? {
          amount: accountAssets?.assets[nativeAsset]?.amount ?? Zero,
          usdValue: assetSum(accountAssets.assets),
        }
      : zeroBalance();

    data.push({
      address: account.address,
      label: account.label ?? '',
      tags: account.tags ?? [],
      chain: blockchain,
      nativeAsset: nativeAsset !== blockchain ? nativeAsset : undefined,
      balance,
      ...balance,
    });
  }
  return data;
}

export function btcAccountsWithBalances(accountsData: BtcAccountData, balances: BtcBalances, blockchain: Blockchain.BTC | Blockchain.BCH): BlockchainAccountWithBalance[] {
  const accounts: BlockchainAccountWithBalance[] = [];

  const { standalone, xpubs } = accountsData;
  for (const { address, label, tags } of standalone) {
    const balance = balances.standalone?.[address] ?? zeroBalance();
    accounts.push({
      address,
      label: label ?? '',
      tags: tags ?? [],
      chain: blockchain,
      balance,
      ...balance,
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
      balance: zeroBalance(),
    });

    if (!addresses)
      continue;

    for (const { address, label, tags } of addresses) {
      const { xpubs } = balances;
      if (!xpubs)
        continue;

      const index = xpubs.findIndex(xpub => xpub.addresses[address]) ?? -1;
      const balance
        = index >= 0 ? xpubs[index].addresses[address] : zeroBalance();
      accounts.push({
        chain: blockchain,
        xpub,
        derivationPath: derivationPath ?? '',
        address,
        label: label ?? '',
        tags: tags ?? [],
        balance,
      });
    }
  }

  return accounts;
}

export function sum(accounts: HasBalance[]): BigNumber {
  return bigNumberSum(accounts.map(account => account.balance.usdValue));
}

export function getBlockchainBreakdown(blockchain: Blockchain, balances: BlockchainAssetBalances, accounts: GeneralAccountData[], asset: string): AssetBreakdown[] {
  const breakdown: AssetBreakdown[] = [];
  for (const address in balances) {
    const balance = balances[address];
    const assetBalance = balance.assets[asset];
    if (!assetBalance)
      continue;

    const tags = getTags(accounts, address);
    breakdown.push({
      address,
      location: blockchain,
      balance: assetBalance,
      tags,
    });
  }
  return breakdown;
}

export function getBtcBreakdown(blockchain: Blockchain, balances: BtcBalances, accounts: BtcAccountData): AssetBreakdown[] {
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
        tags,
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
          tags,
        });
      }
    }
  }
  return breakdown;
}

export function balanceUsdValueSum(balances: HasBalance[]): BigNumber {
  return balances.reduce((sum, balance) => sum.plus(balance.balance.usdValue), Zero);
}
