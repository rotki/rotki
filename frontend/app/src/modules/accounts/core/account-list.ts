import type {
  BlockchainAccountBalance,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { camelCase } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { pipe } from 'plainfp';
import { filter, flatMap, unique } from 'plainfp/arrays';
import { fromArray, head, type NonEmptyArray } from 'plainfp/non-empty-array';
import { map as mapOption, match as matchOption, type Option, some } from 'plainfp/option';
import { and, isDefined, type Predicate } from 'plainfp/predicates';
import { isFilterEnabled, sortBy, sortKeyOf } from '@/modules/accounts/account-common';
import { type AccountGroupId, getAccountAddress, getChain, getGroupId } from '@/modules/accounts/account-utils';
import { sum } from '@/modules/core/common/display/balances';

type GroupAccountsResolver = (groupId: AccountGroupId) => BlockchainAccountWithBalance[];

type LabelResolver = (account: BlockchainAccountBalance, chain?: string) => string | undefined;

type AccountPredicate = Predicate<BlockchainAccountBalance>;

interface AccountFilters {
  tags?: string[];
  addresses?: string[];
  chain?: string[];
  category?: string;
}

interface RowShaping {
  tags?: string[];
  chain?: string[];
  excluded: Record<string, string[]>;
  getAccounts?: GroupAccountsResolver;
}

interface SortColumn {
  /** Whether the row has the attribute; a row without it defers to the next attribute. */
  readonly present: boolean;
  readonly value: unknown;
}

interface DecoratedRow<T> {
  readonly row: T;
  readonly columns: SortColumn[];
}

/** Narrows to a group while keeping the caller's row type, which a `type` check alone widens away. */
function isGroup<T extends BlockchainAccountBalance>(account: T): account is T & BlockchainAccountGroupWithBalance {
  return account.type === 'group';
}

function chainsOf(account: BlockchainAccountBalance): string[] {
  return account.type === 'group' ? account.chains : [account.chain];
}

/** Picked addresses are alternatives rather than joint requirements, since an account carries exactly one address. */
function byAddress(addresses: string[]): AccountPredicate {
  const picked = new Set(addresses.map(address => address.toLowerCase()));
  return account => picked.has(getAccountAddress(account).toLowerCase());
}

function byChain(chains: string[]): AccountPredicate {
  return account => chainsOf(account).some(chain => chains.includes(chain));
}

function byTags(tags: string[]): AccountPredicate {
  return account => tags.every(tag => account.tags?.includes(tag) ?? false);
}

function byCategory(category: string): AccountPredicate {
  return account => account.type === 'group' && account.category === category;
}

/** Holds when every active filter does, so an account passes trivially when nothing is filtered. */
function matchesFilters({ addresses, category, chain, tags }: AccountFilters): AccountPredicate {
  return and(...[
    addresses?.length ? byAddress(addresses) : undefined,
    chain?.length ? byChain(chain) : undefined,
    tags?.length ? byTags(tags) : undefined,
    category ? byCategory(category) : undefined,
  ].filter(isDefined));
}

function applyExclusion<G extends BlockchainAccountGroupWithBalance>(
  group: G,
  excluded: Record<string, string[]>,
  getAccounts?: GroupAccountsResolver,
): G {
  if (isEmpty(excluded) || group.chains.length === 1)
    return group;

  const groupId = getGroupId(group);
  const exclusion = excluded[groupId];
  if (!exclusion)
    return group;

  const selectedAccounts = (getAccounts?.(groupId) ?? []).filter(account => !exclusion.includes(account.chain));

  return {
    ...group,
    includedValue: sum(selectedAccounts),
  };
}

/** Rebuilds a group from the members that matched, keeping every chain it spans in `allChains`. */
function narrowGroup<G extends BlockchainAccountGroupWithBalance>(
  group: G,
  members: BlockchainAccountWithBalance[],
  matches: NonEmptyArray<BlockchainAccountWithBalance>,
  excluded: Record<string, string[]>,
): G {
  const chains = unique(matches.map(match => match.chain));
  const exclusion = excluded[getGroupId({ ...group, chains })];

  return {
    ...group,
    allChains: members.map(member => member.chain),
    chains,
    expansion: matches.length === 1 ? head(matches).expansion : 'accounts',
    includedValue: exclusion ? sum(matches.filter(match => !exclusion.includes(match.chain))) : undefined,
    tags: unique(matches.flatMap(match => match.tags ?? [])),
    value: sum(matches),
  };
}

/**
 * The row an account that passed the filters is shown as, or none when it should be dropped.
 *
 * @remarks
 * Only a tag or chain filter can match on different member accounts and so misrepresent a group,
 * since the others apply to the group itself. Under one of those a group is rebuilt from the
 * members that satisfy both on their own, and dropped when none does: a tag on the optimism
 * member and a chain filter for mainnet do not make the group match. Every other row keeps its
 * shape, with the chain exclusion applied.
 */
function shapeRow<T extends BlockchainAccountBalance>(account: T, shaping: RowShaping): Option<T> {
  if (!isGroup(account))
    return some(account);

  const { chain, excluded, getAccounts, tags } = shaping;
  const matchesOnMembers = isFilterEnabled(tags) || isFilterEnabled(chain);
  const members = matchesOnMembers ? getAccounts?.(getGroupId(account)) : undefined;
  if (!members)
    return some(applyExclusion(account, excluded, getAccounts));

  return pipe(
    members.filter(matchesFilters({ chain, tags })),
    fromArray,
    mapOption(matches => narrowGroup(account, members, matches, excluded)),
  );
}

function sortColumn<T extends BlockchainAccountBalance>(row: T, attribute: string, getLabel: LabelResolver): SortColumn {
  const key = sortKeyOf(row, attribute);
  const stored = key ? row[key] : undefined;
  const isLabel = camelCase(attribute) === 'label';

  return {
    present: key !== undefined,
    value: isLabel ? getLabel(row, getChain(row)) ?? stored ?? getAccountAddress(row) : stored,
  };
}

/** Compares by each requested attribute in turn, so a tie on one falls through to the next. */
function compareRows<T>(a: DecoratedRow<T>, b: DecoratedRow<T>, ascending: boolean[]): number {
  for (const [i, column] of a.columns.entries()) {
    if (!column.present)
      continue;

    const result = sortBy(column.value, b.columns[i].value, ascending[i]);
    if (result)
      return result;
  }
  return 0;
}

/** Resolves each row's sort values once up front, so a label lookup is not repeated per comparison. */
function sortRows<T extends BlockchainAccountBalance>(
  rows: T[],
  orderByAttributes: string[],
  ascending: boolean[],
  getLabel: LabelResolver,
): T[] {
  if (orderByAttributes.length === 0)
    return rows;

  return rows
    .map(row => ({ columns: orderByAttributes.map(attribute => sortColumn(row, attribute, getLabel)), row }))
    .sort((a, b) => compareRows(a, b, ascending))
    .map(({ row }) => row);
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

  const rows = pipe(
    accounts,
    filter<T>(matchesFilters({ addresses, category, chain, tags })),
    flatMap<T, T>(account => matchOption(shapeRow(account, { chain, excluded, getAccounts, tags }), {
      none: () => [],
      some: row => [row],
    })),
  );

  const sorted = sortRows(rows, orderByAttributes, ascending, getLabel);

  return {
    data: sorted.slice(offset, offset + limit),
    found: sorted.length,
    limit: -1,
    total: accounts.length,
    totalValue: sum(rows),
  };
}
