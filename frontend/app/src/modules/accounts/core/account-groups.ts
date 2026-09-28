import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { AccountCategory } from '@/modules/core/api/types/chains';
import { type Balance, Blockchain, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import {
  getAccountAddress,
  getAccountLabel,
  getXpubGroupId,
  isAddressAccount,
  isXpubAccount,
} from '@/modules/accounts/account-utils';
import {
  AccountKind,
  type Accounts,
  type AddressGroupWithBalance,
  type Balances,
  type BlockchainAccount,
  type BlockchainAccountGroupWithBalance,
  type XpubAccount,
  type XpubGroupWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import { type AccountBalancePorts, getAccountBalance, hasTokens } from '@/modules/accounts/core/account-balance';
import { assetSum } from '@/modules/core/common/data/calculation';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { deduplicateTags } from '@/modules/tags/tag-utils';

export interface AccountGroupPorts extends AccountBalancePorts {
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
 * Only standalone addresses get a row; an address derived from an xpub is counted in the xpub's row
 * from {@link xpubGroups}. A lone account expands to its tokens, several expand to their per-chain
 * accounts. An address on a chain without a category is left out, since no accounts page could list it.
 */
function addressGroups(accounts: Accounts, balances: Balances, ports: AccountGroupPorts): AddressGroupWithBalance[] {
  const byAddress = accountsByAddress(accounts);
  const balancesOf = balancesByAddress(balances);
  const addresses = Object.values(accounts)
    .flatMap(chainAccounts => chainAccounts.filter(account => isAddressAccount(account) && !account.xpubParent))
    .map(account => getAccountAddress(account))
    .filter(uniqueStrings);

  return addresses.flatMap((address) => {
    const addressAccounts = byAddress.get(address) ?? [];
    const category = ports.accountType(addressAccounts[0].chain);
    if (!category)
      return [];

    return [addressGroup(address, addressAccounts, balancesOf.get(address) ?? [], { ...ports, category })];
  });
}

function addressGroup(
  address: string,
  addressAccounts: BlockchainAccount[],
  addressBalances: EthBalance[],
  context: AccountBalancePorts & { category: AccountCategory },
): AddressGroupWithBalance {
  const [first] = addressAccounts;
  const single = addressAccounts.length === 1 ? first : undefined;
  const chains = addressAccounts.map(account => account.chain);
  const tags = addressAccounts.flatMap(account => account.tags ?? []).filter(uniqueStrings);
  const hasAssets = single ? hasTokens(context.nativeAssetOf(single.chain), addressBalances[0]?.assets ?? {}) : false;

  return {
    address,
    category: context.category,
    chains,
    expansion: expansionOf(chains, hasAssets),
    kind: AccountKind.ADDRESS,
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
 * The amount counts the chain's native asset only; the value counts every asset the addresses hold.
 */
function xpubGroups(accounts: Accounts, balances: Balances, ports: AccountGroupPorts): XpubGroupWithBalance[] {
  return Object.values(accounts).flatMap(chainAccounts => chainAccounts
    .filter(isXpubAccount)
    .flatMap((xpub) => {
      const category = ports.accountType(xpub.chain);
      return category ? [xpubGroup(xpub, chainAccounts, balances, { ...ports, category })] : [];
    }));
}

function xpubGroup(
  xpub: XpubAccount,
  chainAccounts: BlockchainAccount[],
  balances: Balances,
  context: AccountBalancePorts & { category: AccountCategory },
): XpubGroupWithBalance {
  const groupId = getXpubGroupId(xpub, xpub.chain);
  const children = chainAccounts
    .filter(isAddressAccount)
    .filter(account => account.xpubParent && getXpubGroupId(account.xpubParent, account.chain) === groupId);

  const total: Balance = { amount: Zero, value: Zero };
  for (const child of children) {
    const { balance } = getAccountBalance(child, balances[xpub.chain] ?? {}, context);
    total.amount = total.amount.plus(balance.amount);
    total.value = total.value.plus(balance.value);
  }

  return {
    ...total,
    category: context.category,
    chains: [xpub.chain],
    derivationPath: xpub.derivationPath,
    expansion: children.length > 0 ? 'accounts' : undefined,
    kind: AccountKind.XPUB,
    label: xpub.label,
    nativeAsset: context.nativeAssetOf(xpub.chain),
    tags: xpub.tags ? deduplicateTags(xpub.tags) : undefined,
    type: 'group',
    xpub: xpub.xpub,
  };
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
