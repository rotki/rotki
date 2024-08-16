import { camelCase, isEmpty } from 'lodash-es';
import { type MaybeRef, objectOmit } from '@vueuse/core';
import type {
  BlockchainAssetBalances,
  BlockchainBalances,
  BlockchainTotals,
  BtcBalances,
} from '@/types/blockchain/balances';
import type {
  AccountExtraParams,
  AddressData,
  BasicBlockchainAccount,
  BitcoinAccounts,
  BitcoinXpubAccount,
  BlockchainAccount,
  BlockchainAccountBalance,
  BlockchainAccountData,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
  Totals,
  ValidatorData,
  XpubData,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { Eth2ValidatorEntry } from '@rotki/common';
import type { AssetBalances } from '@/types/balances';

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
    matches.push({ name: 'tags', matches: account.tags?.some(tag => tagFilter.includes(tag)) ?? false });

  if (categoryFilter)
    matches.push({ name: 'category', matches: account.category === categoryFilter });

  return matches.length === 0 || matches.every(match => match.matches);
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
  } = params;

  const hasFilter = isFilterEnabled(tags)
    || isFilterEnabled(label)
    || isFilterEnabled(address)
    || isFilterEnabled(chain)
    || isFilterEnabled(category);

  const nonNull = <T extends BlockchainAccountBalance>(x: T | null): x is T => x !== null;

  const filtered = !hasFilter
    ? accounts
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

          const fullChains = matchesWithoutChains.map(item => item.chain).filter(uniqueStrings);

          return {
            ...account,
            usdValue: sum(matches),
            tags: matches.flatMap(match => match.tags ?? []).filter(uniqueStrings),
            chains: matches.map(match => match.chain).filter(uniqueStrings),
            fullChains,
            expansion: matches.length === 1 ? matches[0].expansion : 'accounts',
          };
        }
      }

      return account;
    }).filter(nonNull);

  const getSortElement = <T extends BlockchainAccountBalance>(key: keyof T, item: T) => {
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

export function createXpubAccount(data: BitcoinXpubAccount, extra: AccountExtraParams): BlockchainAccount<XpubData> {
  return {
    data: {
      type: 'xpub',
      xpub: data.xpub,
      derivationPath: data.derivationPath ?? undefined,
    },
    tags: data.tags ?? undefined,
    label: data.label ?? undefined,
    ...extra,
  };
}

export function createValidatorAccount(
  data: Eth2ValidatorEntry,
  extra: AccountExtraParams,
): BlockchainAccount<ValidatorData> {
  return {
    data: {
      type: 'validator',
      ...data,
    },
    ...extra,
  };
}

export function createAccount(data: BasicBlockchainAccount, extra: AccountExtraParams): BlockchainAccount<AddressData> {
  return {
    data: {
      type: 'address',
      address: data.address,
    },
    tags: data.tags ?? undefined,
    label: data.label ?? undefined,
    ...extra,
  };
}

function getDataId(group: { data: BlockchainAccountData }): string {
  if (group.data.type === 'address') {
    return group.data.address;
  }
  else if (group.data.type === 'validator') {
    return group.data.publicKey;
  }
  else {
    if (!group.data.derivationPath)
      return group.data.xpub;

    return `${group.data.xpub}#${group.data.derivationPath}`;
  }
}

export function getGroupId(group: { data: BlockchainAccountData; chains: string[] }): string {
  const main = getDataId(group);
  if (group.data.type === 'xpub')
    return `${main}#${getChain(group)}`;

  return main;
}

export function getAccountId(account: { data: BlockchainAccountData; chain: string }): string {
  return `${getDataId(account)}#${account.chain}`;
}

export function getAccountAddress(account: { data: BlockchainAccountData }): string {
  if (account.data.type === 'address')
    return account.data.address;
  else if (account.data.type === 'validator')
    return account.data.publicKey;
  else return account.data.xpub;
}

export function getAccountLabel(account: { data: BlockchainAccountData; label?: string }): string {
  if (account.label)
    return account.label;
  else if (account.data.type === 'address')
    return account.data.address;
  else if (account.data.type === 'validator')
    return account.data.index.toString();
  else if (account.data.type === 'xpub')
    return account.data.xpub;
  return '';
}

export function getValidatorData(account: BlockchainAccount): ValidatorData | undefined {
  return account.data.type === 'validator' ? account.data : undefined;
}

export function getChain(account: { chain: string } | { chains: string[] }): string | undefined {
  if ('chain' in account)
    return account.chain;
  else if ('chains' in account && account.chains.length === 1)
    return account.chains[0];
  return undefined;
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
  const chainBalances = Object.fromEntries(
    Object.entries(
      {
        ...perAccountData.standalone,
        ...perAccountData.xpubs?.map(x => x.addresses).reduce((previousValue, currentValue) => ({
          ...previousValue,
          ...currentValue,
        }), {}),
      },
    ).map(([address, value]) => [address, { assets: { [chain.toUpperCase()]: value },
    }]),
  );
  return {
    totals,
    perAccount: { [chain]: chainBalances },
  };
}

export function aggregateTotals(totals: Totals): AssetBalances {
  const balances: AssetBalances = {};
  for (const value of Object.values(totals)) {
    for (const asset of Object.keys(value))
      balances[asset] = !balances[asset] ? value[asset] : balanceSum(balances[asset], value[asset]);
  }

  return balances;
}

export function hasTokens(nativeAsset: string, assetBalances?: AssetBalances): boolean {
  if (!assetBalances || isEmpty(assetBalances))
    return false;

  return !isEmpty(objectOmit(assetBalances, [nativeAsset]));
}

export function getAccountBalance(account: BlockchainAccount, chainBalances: BlockchainAssetBalances) {
  const address = getAccountAddress(account);
  const accountBalances = chainBalances?.[address] ?? {};
  const assets = accountBalances?.assets;
  const nativeAsset = account.nativeAsset;
  const balance = assets
    ? {
        amount: assets[nativeAsset]?.amount ?? Zero,
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

export function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
) {
  const { balance, expansion } = getAccountBalance(account, chainBalances);
  const address = getAccountAddress(account);

  return {
    type: 'account',
    groupId: address,
    ...account,
    ...balance,
    expansion,
  } satisfies BlockchainAccountWithBalance;
}
