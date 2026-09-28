import type { BitcoinAccounts, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type {
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import { createAccount, createXpubAccount } from '@/modules/accounts/create-account';

/** Each xpub followed by the addresses derived from it, then the standalone addresses. */
export function convertBtcAccounts(chain: string, accounts: BitcoinAccounts): BlockchainAccount[] {
  const fromXpub = accounts.xpubs.flatMap((data) => {
    const xpub = createXpubAccount(data, chain);
    const parent = { derivationPath: xpub.derivationPath, xpub: xpub.xpub };
    return [xpub, ...(data.addresses ?? []).map(account => createAccount(account, chain, parent))];
  });

  const standalone = accounts.standalone.map(account => createAccount(account, chain));

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
