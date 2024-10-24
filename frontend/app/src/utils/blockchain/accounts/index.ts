import { camelCase, isEmpty } from 'lodash-es';
import { type MaybeRef, objectOmit } from '@vueuse/core';
import type {
  Balance,
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/types/blockchain/balances';
import type {
  AddressData,
  Balances,
  BitcoinAccounts,
  BlockchainAccount,
  BlockchainAccountBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
  ValidatorData,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { AssetBalances } from '@/types/balances';
import type { Ref } from 'vue';

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
  resolvers: { getLabel: (address: string, chain?: string) => string | null },
): boolean {
  const chains = account.type === 'group' ? account.chains : [account.chain];
  const { getLabel } = resolvers;
  const {
    tags: tagFilter,
    address: addressFilter,
    chain: chainFilter,
    label: labelFilter,
    category: categoryFilter,
  } = filters;

  const matches: { name: keyof typeof filters; matches: boolean }[] = [];
  if (addressFilter)
    matches.push({ name: 'address', matches: includes(getAccountAddress(account), addressFilter) });

  if (labelFilter) {
    const resolvedLabel = getLabel(getAccountAddress(account), getChain(account))
      ?? account.label
      ?? getAccountAddress(account);
    if (resolvedLabel)
      matches.push({ name: 'label', matches: includes(resolvedLabel, labelFilter) });
  }

  if (chainFilter && chainFilter.length > 0)
    matches.push({ name: 'chain', matches: chains.some(chain => chainFilter.includes(chain)) });

  if (tagFilter && tagFilter.length > 0)
    matches.push({ name: 'tags', matches: tagFilter.every(tag => account.tags?.includes(tag) ?? false) });

  if (categoryFilter)
    matches.push({ name: 'category', matches: account.category === categoryFilter });

  return matches.length === 0 || matches.every(match => match.matches);
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
    getLabel: (address: string, chain?: string) => string | null;
  },
): Collection<T> {
  const {
    getAccounts,
    getLabel,
  } = resolvers;
  const {
    offset,
    limit,
    orderByAttributes = [],
    ascending = [],
    tags,
    label,
    address,
    chain,
    category,
    excluded = {},
  } = params;

  const hasFilter = isFilterEnabled(tags)
    || isFilterEnabled(label)
    || isFilterEnabled(address)
    || isFilterEnabled(chain)
    || isFilterEnabled(category);

  const nonNull = <T extends BlockchainAccountBalance>(x: T | null): x is T => x !== null;

  const filtered = !hasFilter
    ? accounts.map(account => applyExclusionFilter(account, excluded, groupId => getAccounts?.(groupId) ?? []))
    : accounts.filter(account => filterAccount(account, {
      tags,
      label,
      address,
      chain,
      category,
    }, { getLabel })).map((account) => {
      /**
       * Second stage filtering for groups. Let's say that we have a group that has a tag `Public`
       * on an account that is on optimism. If I filter by `chain=optimism` and `tag=Public` only this
       * account will appear. If the group includes another account with `tag=Public` and a different one
       * with `chain=optimism` this will skipped (see return)
       */
      if (account.type === 'group' && ((tags && tags.length > 0) || (chain && chain.length > 0))) {
        const groupAccounts = getAccounts?.(getGroupId(account));
        if (groupAccounts) {
          const matchesWithoutChains = groupAccounts.filter(account => filterAccount(account, {
            tags,
            label: undefined, // we only this to the group
            address: undefined, // we only this to the group
          }, { getLabel }));

          const matches = matchesWithoutChains.filter(account => filterAccount(account, {
            chain,
          }, { getLabel }));

          if (matches.length === 0)
            return null;

          const chains = matches.map(match => match.chain).filter(uniqueStrings);
          const groupId = getGroupId({ data: account.data, chains });
          const exclusion = excluded[groupId];
          const usdValue = sum(matches);
          const includedUsdValue = exclusion ? sum(matches.filter(match => !exclusion.includes(match.chain))) : undefined;

          return {
            ...account,
            usdValue,
            includedUsdValue,
            tags: matches.flatMap(match => match.tags ?? []).filter(uniqueStrings),
            chains,
            expansion: matches.length === 1 ? matches[0].expansion : 'accounts',
          };
        }
      }

      return applyExclusionFilter(account, excluded, groupId => getAccounts?.(groupId) ?? []);
    }).filter(nonNull);

  const getSortElement = <T extends BlockchainAccountBalance>(key: keyof T, item: T): string | T[keyof T] => {
    if (key === 'label')
      return getLabel(getAccountAddress(item), getChain(item)) ?? item[key] ?? getAccountAddress(item);

    return item[key];
  };

  const sorted = orderByAttributes.length <= 0
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
    limit: -1,
    total: accounts.length,
    found: sorted.length,
    totalUsdValue: sum(filtered),
  };
}

export function convertBtcAccounts(
  getNativeAsset: (chain: MaybeRef<string>) => string,
  chain: string,
  accounts: BitcoinAccounts,
): BlockchainAccount[] {
  const chainInfo = {
    nativeAsset: getNativeAsset(chain).toUpperCase() ?? chain.toUpperCase(),
    chain,
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
    assets: { [chain.toUpperCase()]: value },
    liabilities: {},
  } satisfies EthBalance]));
  return {
    totals,
    perAccount: { [chain]: chainBalances },
  };
}

export function* iterateAssets(balances: Balances, key: keyof EthBalance = 'assets'): Generator<[string, Balance]> {
  for (const chainBalances of Object.values(balances)) {
    for (const account of Object.values(chainBalances)) {
      if (!account[key])
        continue;

      for (const [identifier, balance] of Object.entries(account[key]))
        yield [identifier, balance] as const;
    }
  }
}

export function aggregateTotals(balances: MaybeRef<Balances>, key: keyof EthBalance = 'assets'): Readonly<Ref<AssetBalances>> {
  return computed<AssetBalances>(() => {
    const aggregated: AssetBalances = {};

    for (const [identifier, balance] of iterateAssets(get(balances), key)) {
      if (!aggregated[identifier])
        aggregated[identifier] = balance;
      else
        aggregated[identifier] = balanceSum(aggregated[identifier], balance);
    }

    return aggregated;
  });
}

export function hasTokens(nativeAsset: string, assetBalances?: AssetBalances): boolean {
  if (!assetBalances || isEmpty(assetBalances))
    return false;

  return !isEmpty(objectOmit(assetBalances, [nativeAsset]));
}

export function getAccountBalance(account: BlockchainAccount, chainBalances: BlockchainAssetBalances): AccountBalance {
  const address = getAccountAddress(account);
  const accountBalances = chainBalances?.[address] ?? {};
  const assets = accountBalances?.assets;
  const nativeAsset = account.nativeAsset;
  const balance = assets
    ? {
        amount: assets[nativeAsset]?.amount ?? Zero,
        value: assetSum(accountBalances.assets),
      }
    : {
        amount: Zero,
        value: Zero,
      };

  const expandable = hasTokens(nativeAsset, accountBalances.assets)
    || hasTokens(nativeAsset, accountBalances.liabilities);
  return { balance, expansion: expandable ? 'assets' as const : undefined };
}
