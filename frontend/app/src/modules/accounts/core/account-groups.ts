import type {
  Accounts,
  Balances,
  BlockchainAccount,
  BlockchainAccountGroupWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { AccountCategory } from '@/modules/core/api/types/chains';
import { type Balance, Blockchain, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { getAccountAddress, getAccountLabel } from '@/modules/accounts/account-utils';
import { getAccountBalance, hasTokens } from '@/modules/accounts/core/account-balance';
import { assetSum } from '@/modules/core/common/data/calculation';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { deduplicateTags } from '@/modules/tags/tag-utils';

export interface AccountGroupPorts {
  readonly isAssetIgnored: (identifier: string) => boolean;
  /** The account category a chain belongs to, or undefined for a chain the backend did not report. */
  readonly accountType: (chain: string) => AccountCategory | undefined;
}

function pushTo<T>(index: Map<string, T[]>, key: string, item: T): void {
  const items = index.get(key);
  if (items)
    items.push(item);
  else
    index.set(key, [item]);
}

/** Every account under each address, across chains, in chain order. */
function accountsByAddress(accounts: Accounts): Map<string, BlockchainAccount[]> {
  const index = new Map<string, BlockchainAccount[]>();
  for (const chainAccounts of Object.values(accounts)) {
    for (const account of chainAccounts)
      pushTo(index, getAccountAddress(account), account);
  }
  return index;
}

/** Every non-empty balance entry under each address, across chains, in chain order. */
function balancesByAddress(balances: Balances): Map<string, EthBalance[]> {
  const index = new Map<string, EthBalance[]>();
  for (const chainBalances of Object.values(balances)) {
    for (const [address, balance] of Object.entries(chainBalances)) {
      if (Object.keys(balance).length > 0)
        pushTo(index, address, balance);
    }
  }
  return index;
}

function expansionOf(chains: readonly string[], hasAssets: boolean): 'accounts' | 'assets' | undefined {
  if (chains.length > 1)
    return 'accounts';
  return hasAssets ? 'assets' : undefined;
}

/**
 * One row per address, merging the address's accounts on every chain it is tracked on.
 *
 * @remarks
 * Only addresses with an account outside an xpub or other group get a row; those groups have their
 * own header in {@link xpubGroups}. A lone account keeps its own data and expands to its tokens,
 * several expand to their per-chain accounts. An address on a chain without a category is left out,
 * since no accounts page could list it.
 */
function addressGroups(accounts: Accounts, balances: Balances, ports: AccountGroupPorts): BlockchainAccountGroupWithBalance[] {
  const byAddress = accountsByAddress(accounts);
  const balancesOf = balancesByAddress(balances);
  const addresses = Object.values(accounts)
    .flatMap(chainAccounts => chainAccounts.filter(account => !account.groupId))
    .map(account => getAccountAddress(account))
    .filter(uniqueStrings);

  return addresses.flatMap((address) => {
    const addressAccounts = byAddress.get(address) ?? [];
    const category = ports.accountType(addressAccounts[0].chain);
    if (!category)
      return [];

    return [addressGroup(address, addressAccounts, balancesOf.get(address) ?? [], { category, isAssetIgnored: ports.isAssetIgnored })];
  });
}

function addressGroup(
  address: string,
  addressAccounts: BlockchainAccount[],
  addressBalances: EthBalance[],
  context: { category: AccountCategory; isAssetIgnored: (identifier: string) => boolean },
): BlockchainAccountGroupWithBalance {
  const [first] = addressAccounts;
  const single = addressAccounts.length === 1 ? first : undefined;
  const chains = addressAccounts.map(account => account.chain);
  const tags = addressAccounts.flatMap(account => account.tags ?? []).filter(uniqueStrings);
  const hasAssets = single ? hasTokens(single.nativeAsset, addressBalances[0]?.assets ?? {}) : false;

  return {
    category: context.category,
    chains,
    data: single ? single.data : { address, type: 'address' },
    expansion: expansionOf(chains, hasAssets),
    label: first ? getAccountLabel(first) : undefined,
    tags: tags.length > 0 ? tags : undefined,
    type: 'group',
    value: addressBalances.reduce((total, balance) => total.plus(assetSum(balance.assets, context.isAssetIgnored)), Zero),
  };
}

/**
 * One row per xpub, summing the addresses derived from it.
 *
 * @remarks
 * The amount counts only children holding the xpub's own native asset; the value counts every child.
 */
function xpubGroups(accounts: Accounts, balances: Balances, ports: AccountGroupPorts): BlockchainAccountGroupWithBalance[] {
  return Object.values(accounts).flatMap(chainAccounts => chainAccounts
    .filter(account => account.groupHeader)
    .flatMap((header) => {
      const category = ports.accountType(header.chain);
      if (!category)
        return [];

      const children = chainAccounts.filter(account => !account.groupHeader && account.groupId === header.groupId);
      const total: Balance = { amount: Zero, value: Zero };
      for (const child of children) {
        const { balance } = getAccountBalance(child, balances[header.chain], ports.isAssetIgnored);
        if (header.nativeAsset === child.nativeAsset)
          total.amount = total.amount.plus(balance.amount);
        total.value = total.value.plus(balance.value);
      }

      return [{
        ...omit(header, ['chain', 'groupId', 'groupHeader']),
        ...total,
        category,
        chains: [header.chain],
        expansion: children.length > 0 ? 'accounts' : undefined,
        tags: header.tags ? deduplicateTags(header.tags) : undefined,
        type: 'group',
      } satisfies BlockchainAccountGroupWithBalance];
    }));
}

/** The top-level rows of the accounts table: one per address, then one per xpub. Validators have their own table. */
export function accountGroups(accounts: Accounts, balances: Balances, ports: AccountGroupPorts): BlockchainAccountGroupWithBalance[] {
  const chainAccounts = omit(accounts, [Blockchain.ETH2]);
  const chainBalances = omit(balances, [Blockchain.ETH2]);
  return [
    ...addressGroups(chainAccounts, chainBalances, ports),
    ...xpubGroups(chainAccounts, chainBalances, ports),
  ];
}
