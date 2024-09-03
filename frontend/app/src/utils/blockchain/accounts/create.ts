import type { Eth2ValidatorEntry } from '@rotki/common';
import type {
  AccountExtraParams,
  AddressData,
  BasicBlockchainAccount,
  BitcoinXpubAccount,
  BlockchainAccount,
  BlockchainAccountWithBalance,
  ValidatorData,
  XpubData,
} from '@/types/blockchain/accounts';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';

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

export function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
): BlockchainAccountWithBalance {
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
