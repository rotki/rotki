import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { getAccountBalance } from '@/utils/blockchain/accounts/index';
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
      derivationPath: data.derivationPath ?? undefined,
      type: 'xpub',
      xpub: data.xpub,
    },
    label: data.label ?? undefined,
    tags: data.tags ?? undefined,
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
      address: data.address,
      type: 'address',
    },
    label: data.label ?? undefined,
    tags: data.tags ?? undefined,
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
    groupId: address,
    type: 'account',
    ...account,
    ...balance,
    expansion,
  } satisfies BlockchainAccountWithBalance;
}
