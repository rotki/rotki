import type { BlockchainBalances, BlockchainTotals, BtcBalances } from '@/types/blockchain/balances';
import type {
  AccountExtraParams,
  AddressData,
  BasicBlockchainAccount,
  BitcoinAccounts,
  BitcoinXpubAccount,
  BlockchainAccount,
  BlockchainAccountData,
  BlockchainAccountWithBalance,
  ValidatorData,
  XpubData,
} from '@/types/blockchain/accounts';
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
