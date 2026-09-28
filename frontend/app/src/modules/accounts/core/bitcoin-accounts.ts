import type { BitcoinAccounts, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type {
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import { createAccount, createXpubAccount } from '@/modules/accounts/create-account';

export function convertBtcAccounts(
  getNativeAsset: (chain: string) => string,
  chain: string,
  accounts: BitcoinAccounts,
): BlockchainAccount[] {
  const chainInfo = {
    chain,
    nativeAsset: getNativeAsset(chain).toUpperCase(),
  };

  const fromXpub = accounts.xpubs.flatMap((xpub) => {
    const extras = {
      groupId: xpub.derivationPath ? `${xpub.xpub}#${xpub.derivationPath}#${chain}` : `${xpub.xpub}#${chain}`,
      ...chainInfo,
    };
    const group = createXpubAccount(xpub, { ...extras, groupHeader: true });
    return [group, ...(xpub.addresses ? xpub.addresses.map(account => createAccount(account, extras)) : [])];
  });

  const standalone = accounts.standalone.map(account => createAccount(account, chainInfo));

  return [...fromXpub, ...standalone];
}

/**
 * Reshapes the bitcoin balance response into the per-address layout the other chains use.
 *
 * @remarks
 * Standalone and xpub-derived addresses end up side by side; an address listed under both keeps the
 * xpub entry.
 */
export function convertBtcBalances(
  chain: string,
  totals: BlockchainTotals,
  perAccountData: BtcBalances,
): BlockchainBalances {
  const perAddress = [
    ...Object.entries(perAccountData.standalone ?? {}),
    ...(perAccountData.xpubs ?? []).flatMap(xpub => Object.entries(xpub.addresses)),
  ];
  const chainBalances: BlockchainAssetBalances = Object.fromEntries(perAddress.map(([address, value]) => [address, {
    assets: { [chain.toUpperCase()]: { address: value } },
    liabilities: {},
  } satisfies EthBalance]));
  return {
    perAccount: { [chain]: chainBalances },
    totals,
  };
}
