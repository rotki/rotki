import type {
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import { type BitcoinAccounts, type BlockchainAccount, XpubAddressType } from '@/modules/accounts/blockchain-accounts';
import { createAccount, createXpubAccount } from '@/modules/accounts/create-account';

/** The bech32m prefix of a mainnet Taproot address. */
const TAPROOT_PREFIX = 'bc1p';

/**
 * The kind of address an xpub derives.
 *
 * @remarks
 * A ypub or zpub names its type. An xpub key is stored the same way for Legacy and for Taproot, so
 * its derived addresses settle which one it is, and with none derived yet it stays `undefined`.
 * Bitcoin Cash has only Legacy keys.
 *
 * @param xpub - the key as stored, prefix included
 * @param addresses - the addresses derived from it
 */
export function xpubAddressType(xpub: string, addresses: string[]): XpubAddressType | undefined {
  if (xpub.startsWith('zpub'))
    return XpubAddressType.NATIVE_SEGWIT;
  if (xpub.startsWith('ypub'))
    return XpubAddressType.SEGWIT;
  if (!xpub.startsWith('xpub') || addresses.length === 0)
    return undefined;
  return addresses.some(address => address.startsWith(TAPROOT_PREFIX)) ? XpubAddressType.TAPROOT : XpubAddressType.LEGACY;
}

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
