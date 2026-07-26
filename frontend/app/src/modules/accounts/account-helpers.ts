import type {
  AddressData,
  Balances,
  BitcoinAccounts,
  BlockchainAccount,
  BlockchainAccountBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
  ValidatorData,
} from '@/modules/accounts/blockchain-accounts';
import type { AssetBalances } from '@/modules/balances/types/balances';
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/modules/balances/types/blockchain-balances';
import type { Collection } from '@/modules/core/common/collection';
import { type Balance, Zero } from '@rotki/common';
import { camelCase, omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { includes, isFilterEnabled, sortBy } from '@/modules/accounts/account-common';
import { getAccountAddress, getChain, getGroupId } from '@/modules/accounts/account-utils';
import { createAccount, createXpubAccount } from '@/modules/accounts/create-account';
import { assetSum, balanceSum } from '@/modules/core/common/data/calculation';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { sum } from '@/modules/core/common/display/balances';

interface AccountBalance {
  balance: Balance;
  expansion?: 'assets';
}

export function hasAccountAddress(data: BlockchainAccount): data is BlockchainAccount<AddressData> {
  return 'address' in data.data;
}

export function isAccountWithBalanceValidator(
  account: BlockchainAccountWithBalance,
): account is BlockchainAccountWithBalance<ValidatorData> {
  return 'publicKey' in account.data;
}

function filterAccount<T extends BlockchainAccountBalance>(
  account: T,
  filters: { tags?: string[]; label?: string; address?: string; chain?: string[]; category?: string },
  resolvers: { getLabel: (account: BlockchainAccountBalance, chain?: string) => string | undefined },
): boolean {
  const chains = account.type === 'group' ? account.chains : [account.chain];
  const { getLabel } = resolvers;
  const {
    address: addressFilter,
    category: categoryFilter,
    chain: chainFilter,
    label: labelFilter,
    tags: tagFilter,
  } = filters;

  // undefined means "this filter is not active", which is different from "active and did not match":
  // an account passes only when every active filter matches, and passes trivially when none are.
  function matchesLabel(): boolean | undefined {
    if (!labelFilter)
      return undefined;

    const resolvedLabel = getLabel(account, getChain(account))
      ?? account.label
      ?? getAccountAddress(account);

    return resolvedLabel ? includes(resolvedLabel, labelFilter) : undefined;
  }

  function matchesChain(): boolean | undefined {
    if (!chainFilter?.length)
      return undefined;

    return chains.some(chain => chainFilter.includes(chain));
  }

  function matchesTags(): boolean | undefined {
    if (!tagFilter?.length)
      return undefined;

    return tagFilter.every(tag => account.tags?.includes(tag) ?? false);
  }

  const results = [
    addressFilter ? includes(getAccountAddress(account), addressFilter) : undefined,
    matchesLabel(),
    matchesChain(),
    matchesTags(),
    categoryFilter ? account.category === categoryFilter : undefined,
  ].filter(result => result !== undefined);

  return results.length === 0 || results.every(result => result);
}

function applyExclusionFilter<T extends BlockchainAccountBalance>(
  account: T,
  excluded: Record<string, string[]>,
  getGroupAccounts: (groupId: string) => BlockchainAccountWithBalance[],
): T {
  if (isEmpty(excluded) || account.type !== 'group' || account.chains.length === 1)
    return account;

  const groupId = getGroupId(account);
  const exclusion = excluded[groupId];
  if (!exclusion)
    return account;

  const selectedAccounts = getGroupAccounts(groupId).filter(account => !exclusion.includes(account.chain));

  return {
    ...account,
    includedValue: sum(selectedAccounts),
  };
}

export function sortAndFilterAccounts<T extends BlockchainAccountBalance>(
  accounts: T[],
  params: BlockchainAccountRequestPayload,
  resolvers: {
    getAccounts?: (groupId: string) => BlockchainAccountWithBalance[];
    getLabel: (account: BlockchainAccountBalance, chain?: string) => string | undefined;
  },
): Collection<T> {
  const {
    getAccounts,
    getLabel,
  } = resolvers;
  const {
    address,
    ascending = [],
    category,
    chain,
    excluded = {},
    label,
    limit,
    offset,
    orderByAttributes = [],
    tags,
  } = params;

  const hasFilter = isFilterEnabled(tags)
    || isFilterEnabled(label)
    || isFilterEnabled(address)
    || isFilterEnabled(chain)
    || isFilterEnabled(category);

  const nonNull = <U extends BlockchainAccountBalance>(x: U | null): x is U => x !== null;

  /**
   * Only a tag or chain filter can match on different member accounts and so misrepresent a group;
   * the others apply to the group itself.
   */
  function hasGroupSensitiveFilter(): boolean {
    return isFilterEnabled(tags) || isFilterEnabled(chain);
  }

  /**
   * Second stage filtering for groups. Let's say that we have a group that has a tag `Public`
   * on an account that is on optimism. If I filter by `chain=optimism` and `tag=Public` only this
   * account will appear. If the group includes another account with `tag=Public` and a different one
   * with `chain=optimism` this will skipped (see return)
   *
   * Returns undefined when the group does not need refining, so the caller falls back to the plain
   * exclusion path, and null when no member survives and the group should be dropped.
   */
  function refineGroup<T extends BlockchainAccountBalance>(account: T): T | null | undefined {
    // The group check stays here so `account` narrows to the group variant for `data` and `chains`.
    if (account.type !== 'group' || !hasGroupSensitiveFilter())
      return undefined;

    const groupAccounts = getAccounts?.(getGroupId(account));
    if (!groupAccounts)
      return undefined;

    // Address and label apply to the group itself, so they are deliberately dropped here.
    const matchesWithoutChains = groupAccounts.filter(item => filterAccount(item, {
      address: undefined,
      label: undefined,
      tags,
    }, { getLabel }));

    const matches = matchesWithoutChains.filter(item => filterAccount(item, { chain }, { getLabel }));
    if (matches.length === 0)
      return null;

    const chains = matches.map(match => match.chain).filter(uniqueStrings);
    const groupId = getGroupId({ chains, data: account.data });
    const exclusion = excluded[groupId];

    return {
      ...account,
      allChains: groupAccounts.map(item => item.chain),
      chains,
      expansion: matches.length === 1 ? matches[0].expansion : 'accounts',
      includedValue: exclusion ? sum(matches.filter(match => !exclusion.includes(match.chain))) : undefined,
      tags: matches.flatMap(match => match.tags ?? []).filter(uniqueStrings),
      value: sum(matches),
    };
  }

  const filtered = !hasFilter
    ? accounts.map(account => applyExclusionFilter(account, excluded, groupId => getAccounts?.(groupId) ?? []))
    : accounts.filter(account => filterAccount(account, {
        address,
        category,
        chain,
        label,
        tags,
      }, { getLabel })).map((account) => {
        const refined = refineGroup(account);
        if (refined !== undefined)
          return refined;

        return applyExclusionFilter(account, excluded, groupId => getAccounts?.(groupId) ?? []);
      }).filter(nonNull);

  const getSortElement = <T extends BlockchainAccountBalance>(key: keyof T, item: T): string | T[keyof T] => {
    if (key === 'label')
      return getLabel(item, getChain(item)) ?? item[key] ?? getAccountAddress(item);

    return item[key];
  };

  const sorted = orderByAttributes.length === 0
    ? filtered
    : filtered.sort((a, b) => {
        for (const [i, attr] of orderByAttributes.entries()) {
          const key = camelCase(attr) as keyof T;
          const asc = ascending[i];

          const order = sortBy(getSortElement(key, a), getSortElement(key, b), asc);
          if (order)
            return order;
        }
        return 0;
      });

  return {
    data: sorted.slice(offset, offset + limit),
    found: sorted.length,
    limit: -1,
    total: accounts.length,
    totalValue: sum(filtered),
  };
}

export function convertBtcAccounts(
  getNativeAsset: (chain: string) => string,
  chain: string,
  accounts: BitcoinAccounts,
): BlockchainAccount[] {
  const chainInfo = {
    chain,
    nativeAsset: getNativeAsset(chain).toUpperCase() ?? chain.toUpperCase(),
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

export function convertBtcBalances(
  chain: string,
  totals: BlockchainTotals,
  perAccountData: BtcBalances,
): BlockchainBalances {
  const chainBalances: BlockchainAssetBalances = Object.fromEntries(Object.entries({
    ...perAccountData.standalone,
    ...perAccountData.xpubs?.map(x => x.addresses).reduce((previousValue, currentValue) => ({
      ...previousValue,
      ...currentValue,
    }), {}),
  }).map(([address, value]) => [address, {
    assets: { [chain.toUpperCase()]: { address: value } },
    liabilities: {},
  } satisfies EthBalance]));
  return {
    perAccount: { [chain]: chainBalances },
    totals,
  };
}

interface GeneratorFilters {
  chains?: string[];
  skipIdentifier?: (asset: string) => boolean;
  resolveIdentifier?: (id: string) => string;
}

const GENERATOR_FILTER_DEFAULTS: Required<GeneratorFilters> = {
  chains: [],
  resolveIdentifier: (id: string): string => id,
  skipIdentifier: (): boolean => false,
};

/** An empty chain list means every chain, rather than none. */
function includesChain(chains: string[], chain: string): boolean {
  return chains.length === 0 || chains.includes(chain);
}

function sumProtocolBalances(protocolBalances: Record<string, Balance>): Balance {
  return Object.values(protocolBalances).reduce<Balance>((sum, current) => ({
    amount: sum.amount.plus(current.amount),
    value: sum.value.plus(current.value),
  }), { amount: Zero, value: Zero });
}

function* iterateAssets(
  balances: Balances,
  key: keyof EthBalance,
  filters: GeneratorFilters,
): Generator<[string, Balance]> {
  // Spread rather than per-field defaults, each of which the complexity rule counts as a branch.
  const { chains, resolveIdentifier, skipIdentifier } = { ...GENERATOR_FILTER_DEFAULTS, ...filters };

  for (const chain of Object.keys(balances)) {
    if (!includesChain(chains, chain))
      continue;

    for (const account of Object.values(balances[chain])) {
      if (!account[key])
        continue;

      for (const [identifier, protocolBalances] of Object.entries(account[key])) {
        if (skipIdentifier(identifier))
          continue;

        yield [resolveIdentifier(identifier), sumProtocolBalances(protocolBalances)] as const;
      }
    }
  }
}

export function aggregateTotals(
  balances: Balances,
  key: keyof EthBalance = 'assets',
  filters: GeneratorFilters = {},
): AssetBalances {
  const aggregated: AssetBalances = {};

  for (const [identifier, balance] of iterateAssets(balances, key, filters)) {
    if (!aggregated[identifier])
      aggregated[identifier] = balance;
    else
      aggregated[identifier] = balanceSum(aggregated[identifier], balance);
  }
  return aggregated;
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
