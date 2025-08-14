import type { MaybeRef } from '@vueuse/core';
import type { AssetBalances } from '@/types/balances';
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
import type {
  AssetProtocolBalances,
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
  EthBalance,
} from '@/types/blockchain/balances';
import type { Collection } from '@/types/collection';
import { type Balance, Zero } from '@rotki/common';
import { camelCase, omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { sum } from '@/utils/balances';
import { includes, isFilterEnabled, sortBy } from '@/utils/blockchain/accounts/common';
import { createAccount, createXpubAccount } from '@/utils/blockchain/accounts/create';
import { getAccountAddress, getChain, getGroupId } from '@/utils/blockchain/accounts/utils';
import { assetSum, balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

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
  resolvers: { getLabel: (address: string, chain?: string) => string | undefined },
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

  const matches: { name: keyof typeof filters; matches: boolean }[] = [];
  if (addressFilter)
    matches.push({ matches: includes(getAccountAddress(account), addressFilter), name: 'address' });

  if (labelFilter) {
    const resolvedLabel = getLabel(getAccountAddress(account), getChain(account))
      ?? account.label
      ?? getAccountAddress(account);
    if (resolvedLabel)
      matches.push({ matches: includes(resolvedLabel, labelFilter), name: 'label' });
  }

  if (chainFilter && chainFilter.length > 0)
    matches.push({ matches: chains.some(chain => chainFilter.includes(chain)), name: 'chain' });

  if (tagFilter && tagFilter.length > 0)
    matches.push({ matches: tagFilter.every(tag => account.tags?.includes(tag) ?? false), name: 'tags' });

  if (categoryFilter)
    matches.push({ matches: account.category === categoryFilter, name: 'category' });

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
    includedUsdValue: sum(selectedAccounts),
  };
}

export function sortAndFilterAccounts<T extends BlockchainAccountBalance>(
  accounts: T[],
  params: BlockchainAccountRequestPayload,
  resolvers: {
    getAccounts?: (groupId: string) => BlockchainAccountWithBalance[];
    getLabel: (address: string, chain?: string) => string | undefined;
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

  const nonNull = <T extends BlockchainAccountBalance>(x: T | null): x is T => x !== null;

  const filtered = !hasFilter
    ? accounts.map(account => applyExclusionFilter(account, excluded, groupId => getAccounts?.(groupId) ?? []))
    : accounts.filter(account => filterAccount(account, {
        address,
        category,
        chain,
        label,
        tags,
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
              address: undefined, // we only this to the group
              label: undefined, // we only this to the group
              tags,
            }, { getLabel }));

            const matches = matchesWithoutChains.filter(account => filterAccount(account, {
              chain,
            }, { getLabel }));

            if (matches.length === 0)
              return null;

            const chains = matches.map(match => match.chain).filter(uniqueStrings);
            const groupId = getGroupId({ chains, data: account.data });
            const exclusion = excluded[groupId];
            const usdValue = sum(matches);
            const includedUsdValue = exclusion ? sum(matches.filter(match => !exclusion.includes(match.chain))) : undefined;

            return {
              ...account,
              allChains: groupAccounts.map(item => item.chain),
              chains,
              expansion: matches.length === 1 ? matches[0].expansion : 'accounts',
              includedUsdValue,
              tags: matches.flatMap(match => match.tags ?? []).filter(uniqueStrings),
              usdValue,
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
    found: sorted.length,
    limit: -1,
    total: accounts.length,
    totalUsdValue: sum(filtered),
  };
}

export function convertBtcAccounts(
  getNativeAsset: (chain: MaybeRef<string>) => string,
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
  assetAssociationMap?: Record<string, string>;
}

export function* iterateAssets(
  balances: Balances,
  key: keyof EthBalance = 'assets',
  filters: GeneratorFilters = {},
): Generator<[string, Balance]> {
  const {
    assetAssociationMap = {},
    chains = [],
    skipIdentifier = (): boolean => false,
  } = filters;
  for (const chain of Object.keys(balances)) {
    const chainBalances = balances[chain];
    if (!(chains.length === 0 || chains.includes(chain))) {
      continue;
    }

    for (const account of Object.values(chainBalances)) {
      if (!account[key])
        continue;

      for (const [identifier, protocolBalances] of Object.entries(account[key])) {
        if (skipIdentifier(identifier))
          continue;

        const assetIdentifier = assetAssociationMap[identifier] ?? identifier;
        const balance = Object.values(protocolBalances).reduce((previousValue, currentValue) => ({
          amount: previousValue.amount.plus(currentValue.amount),
          usdValue: previousValue.usdValue.plus(currentValue.usdValue),
        }), {
          amount: Zero,
          usdValue: Zero,
        });
        yield [assetIdentifier, balance] as const;
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

export function getAccountBalance(account: BlockchainAccount, chainBalances: BlockchainAssetBalances): AccountBalance {
  const address = getAccountAddress(account);
  const accountBalances = chainBalances?.[address] ?? {};
  const assets = accountBalances?.assets;
  const nativeAsset = account.nativeAsset;
  const balance = assets
    ? {
        amount: assets[nativeAsset] && !isEmpty(assets[nativeAsset])
          ? Object.values(assets[nativeAsset]).reduce((previousValue, currentValue) => previousValue.plus(currentValue.amount), Zero)
          : Zero,
        usdValue: assetSum(accountBalances.assets),
      }
    : {
        amount: Zero,
        usdValue: Zero,
      };

  const expandable = hasTokens(nativeAsset, accountBalances.assets)
    || hasTokens(nativeAsset, accountBalances.liabilities);
  return { balance, expansion: expandable ? 'assets' as const : undefined };
}
