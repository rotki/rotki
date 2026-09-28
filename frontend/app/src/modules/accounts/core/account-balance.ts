import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { AssetProtocolBalances, BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { type Balance, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { assetSum } from '@/modules/core/common/data/calculation';

interface AccountBalance {
  balance: Balance;
  expansion?: 'assets';
}

export function hasTokens(nativeAsset: string, assetBalances?: AssetProtocolBalances): boolean {
  if (!assetBalances || isEmpty(assetBalances))
    return false;

  return !isEmpty(omit(assetBalances, [nativeAsset]));
}

export function getAccountBalance(account: BlockchainAccount, chainBalances: BlockchainAssetBalances, isAssetIgnored: (asset: string) => boolean): AccountBalance {
  const address = getAccountAddress(account);
  const accountBalances = chainBalances?.[address] ?? {};
  const assets = accountBalances?.assets;
  const nativeAsset = account.nativeAsset;
  const valueSum = assets ? assetSum(assets, isAssetIgnored) : Zero;
  const balance = assets
    ? {
        amount: assets[nativeAsset] && !isEmpty(assets[nativeAsset])
          ? Object.values(assets[nativeAsset]).reduce((previousValue, currentValue) => previousValue.plus(currentValue.amount), Zero)
          : Zero,
        value: valueSum,
      }
    : {
        amount: Zero,
        value: Zero,
      };

  const expandable = hasTokens(nativeAsset, accountBalances.assets)
    || hasTokens(nativeAsset, accountBalances.liabilities);
  return { balance, expansion: expandable ? 'assets' as const : undefined };
}
