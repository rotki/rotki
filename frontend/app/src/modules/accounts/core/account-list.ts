import type {
  BlockchainAccountBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { isEmpty } from 'es-toolkit/compat';
import { isFilterEnabled, sortBy, sortKeyOf } from '@/modules/accounts/account-common';
import { getAccountAddress, getChain, getGroupId } from '@/modules/accounts/account-utils';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { sum } from '@/modules/core/common/display/balances';

type GroupAccountsResolver = (groupId: string) => BlockchainAccountWithBalance[];

type LabelResolver = (account: BlockchainAccountBalance, chain?: string) => string | undefined;

interface AccountFilters {
  tags?: string[];
  addresses?: string[];
  chain?: string[];
  category?: string;
}

interface GroupRefinement {
  tags?: string[];
  chain?: string[];
  excluded: Record<string, string[]>;
  getAccounts?: GroupAccountsResolver;
}

interface AccountOrder {
  orderByAttributes: string[];
  ascending: boolean[];
  getLabel: LabelResolver;
}

/**
 * Reports whether an account satisfies every filter that is currently active.
 *
 * @remarks
 * An unset filter contributes `undefined` rather than `false`, so an account passes trivially when
 * nothing is filtered. Addresses inside the address filter are alternatives rather than joint
 * requirements, because an account carries exactly one address.
 */
function filterAccount<T extends BlockchainAccountBalance>(account: T, filters: AccountFilters): boolean {
  const chains = account.type === 'group' ? account.chains : [account.chain];
  const {
    addresses: addressFilter,
    category: categoryFilter,
    chain: chainFilter,
    tags: tagFilter,
  } = filters;

  function matchesAddress(): boolean | undefined {
    if (!addressFilter?.length)
      return undefined;

    const address = getAccountAddress(account).toLowerCase();
    return addressFilter.some(picked => picked.toLowerCase() === address);
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
    matchesAddress(),
    matchesChain(),
    matchesTags(),
    categoryFilter ? account.category === categoryFilter : undefined,
  ].filter(result => result !== undefined);

  return results.length === 0 || results.every(result => result);
}

function applyExclusionFilter<T extends BlockchainAccountBalance>(
  account: T,
  excluded: Record<string, string[]>,
  getGroupAccounts: GroupAccountsResolver,
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

/**
 * Second stage filtering for groups. Let's say that we have a group that has a tag `Public`
 * on an account that is on optimism. If I filter by `chain=optimism` and `tag=Public` only this
 * account will appear. If the group includes another account with `tag=Public` and a different one
 * with `chain=optimism` this will skipped (see return)
 *
 * @remarks
 * Only a tag or chain filter can match on different member accounts and so misrepresent a group;
 * the others apply to the group itself.
 *
 * @returns undefined when the group does not need refining, so the caller falls back to the plain
 * exclusion path, and null when no member survives and the group should be dropped.
 */
function refineGroup<T extends BlockchainAccountBalance>(account: T, refinement: GroupRefinement): T | null | undefined {
  const { chain, excluded, getAccounts, tags } = refinement;
  const hasGroupSensitiveFilter = isFilterEnabled(tags) || isFilterEnabled(chain);
  if (account.type !== 'group' || !hasGroupSensitiveFilter)
    return undefined;

  const groupAccounts = getAccounts?.(getGroupId(account));
  if (!groupAccounts)
    return undefined;

  const addressAppliesToTheGroupNotItsMembers = undefined;
  const matchesWithoutChains = groupAccounts.filter(item => filterAccount(item, {
    addresses: addressAppliesToTheGroupNotItsMembers,
    tags,
  }));

  const matches = matchesWithoutChains.filter(item => filterAccount(item, { chain }));
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

function getSortElement<T extends BlockchainAccountBalance>(key: keyof T, item: T, getLabel: LabelResolver): string | T[keyof T] {
  if (key === 'label')
    return getLabel(item, getChain(item)) ?? item[key] ?? getAccountAddress(item);

  return item[key];
}

/** Compares by each requested attribute in turn, so a tie on one falls through to the next. */
function compareAccounts<T extends BlockchainAccountBalance>(a: T, b: T, order: AccountOrder): number {
  const { ascending, getLabel, orderByAttributes } = order;
  for (const [i, attr] of orderByAttributes.entries()) {
    const key = sortKeyOf(a, attr);
    if (!key)
      continue;

    const result = sortBy(getSortElement(key, a, getLabel), getSortElement(key, b, getLabel), ascending[i]);
    if (result)
      return result;
  }
  return 0;
}

function nonNull<T extends BlockchainAccountBalance>(account: T | null): account is T {
  return account !== null;
}

export function sortAndFilterAccounts<T extends BlockchainAccountBalance>(
  accounts: T[],
  params: BlockchainAccountRequestPayload,
  resolvers: {
    getAccounts?: GroupAccountsResolver;
    getLabel: LabelResolver;
  },
): Collection<T> {
  const {
    getAccounts,
    getLabel,
  } = resolvers;
  const {
    addresses,
    ascending = [],
    category,
    chain,
    excluded = {},
    limit,
    offset,
    orderByAttributes = [],
    tags,
  } = params;

  const hasFilter = isFilterEnabled(tags)
    || isFilterEnabled(addresses)
    || isFilterEnabled(chain)
    || isFilterEnabled(category);

  const getGroupAccounts: GroupAccountsResolver = groupId => getAccounts?.(groupId) ?? [];

  const filtered = !hasFilter
    ? accounts.map(account => applyExclusionFilter(account, excluded, getGroupAccounts))
    : accounts
        .filter(account => filterAccount(account, { addresses, category, chain, tags }))
        .map((account) => {
          const refined = refineGroup(account, { chain, excluded, getAccounts, tags });
          return refined === undefined ? applyExclusionFilter(account, excluded, getGroupAccounts) : refined;
        })
        .filter(nonNull);

  const sorted = orderByAttributes.length === 0
    ? filtered
    : filtered.sort((a, b) => compareAccounts(a, b, { ascending, getLabel, orderByAttributes }));

  return {
    data: sorted.slice(offset, offset + limit),
    found: sorted.length,
    limit: -1,
    total: accounts.length,
    totalValue: sum(filtered),
  };
}
