import type { BlockchainAccountBalance, BlockchainAccountWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { ProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import { type AssetBalance, type Balance, Zero } from '@rotki/common';
import { isXpubAccount } from '@/modules/accounts/account-utils';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { balanceSum } from '@/modules/core/common/data/calculation';

export interface AccountAssetPorts {
  readonly isAssetIgnored: (identifier: string) => boolean;
  readonly resolveIdentifier: (identifier: string) => string;
}

/**
 * One row per asset an account holds, summed across its protocols, with ignored assets and empty
 * protocol entries left out.
 *
 * @remarks
 * Identifiers that resolve to the same asset are merged, and the ignore check runs on the resolved one.
 */
export function accountAssetBalances(balances: Record<string, ProtocolBalances>, ports: AccountAssetPorts): AssetBalance[] {
  const byAsset = new Map<string, Balance>();
  for (const [asset, protocols] of Object.entries(balances)) {
    const identifier = ports.resolveIdentifier(asset);
    if (ports.isAssetIgnored(identifier))
      continue;

    for (const balance of Object.values(protocols)) {
      if (balance.amount.isZero())
        continue;
      const held = byAsset.get(identifier);
      byAsset.set(identifier, held ? balanceSum(held, balance) : balance);
    }
  }
  return Array.from(byAsset, ([asset, balance]) => ({ asset, ...balance }));
}

/** An account's tokens reduced to asset, amount and value, highest value first. */
export function topTokens(balances: readonly AssetBalance[]): AssetBalance[] {
  return balances
    .map(({ amount, asset, value }) => ({ amount, asset, value }))
    .sort((a, b) => sortDesc(a.value, b.value));
}

/**
 * The single native-asset row an xpub shows in place of a token list.
 *
 * @remarks
 * An xpub's balance is already summed over its derived addresses in its own native asset, so there
 * is no per-token list to show. Any other row returns `undefined`.
 */
export function xpubNativeHolding(row: BlockchainAccountBalance): AssetBalance | undefined {
  if (!isXpubAccount(row) || !row.nativeAsset)
    return undefined;
  return { amount: row.amount ?? Zero, asset: row.nativeAsset, value: row.value };
}

/** The accounts behind each group, keyed by group id, so a group's members are found without a scan. */
export function accountsByGroup(accounts: readonly BlockchainAccountWithBalance[]): Map<string, BlockchainAccountWithBalance[]> {
  const byGroup = new Map<string, BlockchainAccountWithBalance[]>();
  for (const account of accounts) {
    if (!account.groupId)
      continue;
    const members = byGroup.get(account.groupId);
    if (members)
      members.push(account);
    else
      byGroup.set(account.groupId, [account]);
  }
  return byGroup;
}
