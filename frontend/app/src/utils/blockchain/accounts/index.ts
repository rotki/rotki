import { camelCase } from 'lodash-es';
import { sum } from '@/utils/balances';
import type { BlockchainBalances, BlockchainTotals, BtcBalances } from '@/types/blockchain/balances';
import type {
  AccountExtraParams,
  AddressData,
  BasicBlockchainAccount,
  BitcoinAccounts,
  BitcoinXpubAccount,
  BlockchainAccount,
  BlockchainAccountData,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
  ValidatorData,
  XpubData,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';
import type { MaybeRef } from '@vueuse/core';

export function hasAccountAddress(data: BlockchainAccount): data is BlockchainAccount<AddressData> {
  return 'address' in data.data;
}

export function isAccountValidator(account: BlockchainAccount): account is BlockchainAccount<ValidatorData> {
  return 'publicKey' in account.data;
}

export function hasAccountWithBalanceAddress(
  data: BlockchainAccountWithBalance,
): data is BlockchainAccountWithBalance<AddressData> {
  return 'address' in data.data;
}

export function isAccountWithBalanceValidator(
  account: BlockchainAccountWithBalance,
): account is BlockchainAccountWithBalance<ValidatorData> {
  return 'publicKey' in account.data;
}

export function isAccountWithBalanceXpub(
  account: BlockchainAccountWithBalance,
): account is BlockchainAccountWithBalance<XpubData> {
  return 'xpub' in account.data;
}

const sortOptions: Intl.CollatorOptions = { sensitivity: 'accent', usage: 'sort' };

function sortBy(a: any, b: any, asc: boolean): number {
  const [aValue, bValue] = asc ? [a, b] : [b, a];

  if (!isNaN(aValue) && !isNaN(bValue))
    return Number(aValue) - Number(bValue);

  return `${aValue}`.localeCompare(
      `${bValue}`,
      undefined,
      sortOptions,
  );
}

function isFilterEnabled(filter?: string[] | string): boolean {
  return Array.isArray(filter) ? filter.length > 0 : !!filter;
}

function filterAccount<T extends BlockchainAccountGroupWithBalance | BlockchainAccountWithBalance>(
  account: T,
  filters: {
    tags?: string[];
    label?: string;
    address?: string;
    chain?: string;
  },
): boolean {
  const chains = 'chains' in account ? account.chains : [account.chain];
  const matches = [
    !!filters.address && getAccountAddress(account).toLocaleLowerCase().includes(filters.address.toLocaleLowerCase()),
    !!filters.label && !!account.label && account.label.toLocaleLowerCase().includes(filters.label.toLocaleLowerCase()),
    !!filters.chain && chains.some(chain => chain.toLocaleLowerCase() === filters.chain?.toLocaleLowerCase()),
    !!filters.tags && !!account.tags && account.tags.some(tag => filters.tags?.includes(tag)),
  ];

  return matches.some(match => match);
}

export function sortAndFilterAccounts<T extends BlockchainAccountGroupWithBalance | BlockchainAccountWithBalance>(
  accounts: T[],
  params: BlockchainAccountRequestPayload,
): Collection<T> {
  const {
    offset,
    limit,
    orderByAttributes = [],
    ascending = [],
    tags,
    label,
    address,
    chain,
  } = params;

  const hasFilter = isFilterEnabled(tags)
    || isFilterEnabled(label)
    || isFilterEnabled(address)
    || isFilterEnabled(chain);

  const filtered = !hasFilter
    ? accounts
    : accounts.filter(account => filterAccount(account, {
      tags,
      label,
      address,
      chain,
    }));

  const sorted = orderByAttributes.length <= 0
    ? filtered
    : filtered.sort((a, b) => {
      for (const [i, attr] of orderByAttributes.entries()) {
        const key = camelCase(attr) as keyof T;
        const asc = ascending[i];
        const order = sortBy(a[key], b[key], asc);
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

export function createXpubAccount(
  data: BitcoinXpubAccount,
  extra: AccountExtraParams,
): BlockchainAccount<XpubData> {
  return {
    data: {
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
    data,
    ...extra,
  };
}

export function createAccount(
  data: BasicBlockchainAccount,
  extra: AccountExtraParams,
): BlockchainAccount<AddressData> {
  return {
    data: { address: data.address },
    tags: data.tags ?? undefined,
    label: data.label ?? undefined,
    ...extra,
  };
}

function getDataId(group: { data: BlockchainAccountData }): string {
  if ('address' in group.data) {
    return group.data.address;
  }
  else if ('publicKey' in group.data) {
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
  if ('xpub' in group.data)
    return `${main}#${getChain(group)}`;

  return main;
}

export function getAccountId(account: { data: BlockchainAccountData; chain: string }): string {
  return `${getDataId(account)}#${account.chain}`;
}

export function getAccountAddress(account: { data: BlockchainAccountData }): string {
  if ('address' in account.data)
    return account.data.address;
  else if ('publicKey' in account.data)
    return account.data.publicKey;
  else
    return account.data.xpub;
}

export function getAccountLabel(account: { data: BlockchainAccountData; label?: string }): string {
  if (account.label)
    return account.label;
  else if ('address' in account.data)
    return account.data.address;
  else if ('index' in account.data)
    return account.data.index.toString();
  else if ('xpub' in account.data)
    return account.data.xpub;
  return '';
}

export function getValidatorData(account: BlockchainAccount): ValidatorData | undefined {
  return 'index' in account.data ? account.data : undefined;
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

  const fromXpub = accounts.xpubs.flatMap(((xpub) => {
    const extras = {
      groupId: xpub.derivationPath ? `${xpub.xpub}#${xpub.derivationPath}#${chain}` : `${xpub.xpub}#${chain}`,
      ...chainInfo,
    };
    const group = createXpubAccount(xpub, { ...extras, groupHeader: true });
    return [
      group,
      ...(xpub.addresses ? xpub.addresses.map(account => createAccount(account, extras)) : []),
    ];
  }));

  const standalone = accounts.standalone.map(account => createAccount(account, chainInfo));

  return [...fromXpub, ...standalone];
}

export function convertBtcBalances(chain: string, totals: BlockchainTotals, perAccountData: BtcBalances): BlockchainBalances {
  const chainBalances = Object.fromEntries(
    Object.entries(
      {
        ...perAccountData.standalone,
        ...perAccountData.xpubs?.map(x => x.addresses).reduce((previousValue, currentValue) => ({
          ...previousValue,
          ...currentValue,
        }), {}),
      },
    ).map(([address, value]) => [address, {
      assets: {
        [chain.toUpperCase()]: value,
      },
    }]),
  );
  return {
    totals,
    perAccount: {
      [chain]: chainBalances,
    },
  };
}
