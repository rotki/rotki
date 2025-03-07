import type {
  AccountExtraParams,
  AddressData,
  BasicBlockchainAccount,
  BitcoinXpubAccount,
  BlockchainAccount,
  ValidatorData,
  XpubData,
} from '@/types/blockchain/accounts';
import type { Eth2ValidatorEntry } from '@rotki/common';

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
