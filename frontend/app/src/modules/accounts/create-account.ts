import type { Eth2ValidatorEntry } from '@rotki/common';
import {
  AccountKind,
  type AddressAccount,
  type BasicBlockchainAccount,
  type BitcoinXpubAccount,
  type ValidatorAccount,
  type XpubAccount,
  type XpubKey,
} from '@/modules/accounts/blockchain-accounts';

export function createXpubAccount(data: BitcoinXpubAccount, chain: string): XpubAccount {
  return {
    chain,
    derivationPath: data.derivationPath ?? undefined,
    kind: AccountKind.XPUB,
    label: data.label ?? undefined,
    tags: data.tags ?? undefined,
    xpub: data.xpub,
  };
}

export function createValidatorAccount(data: Eth2ValidatorEntry, chain: string): ValidatorAccount {
  return {
    ...data,
    chain,
    kind: AccountKind.VALIDATOR,
  };
}

/**
 * @param data - the account as the backend lists it
 * @param chain - the chain it is tracked on
 * @param xpubParent - the xpub the address was derived from, for an address that is not standalone
 */
export function createAccount(data: BasicBlockchainAccount, chain: string, xpubParent?: XpubKey): AddressAccount {
  return {
    address: data.address,
    chain,
    kind: AccountKind.ADDRESS,
    label: data.label ?? undefined,
    tags: data.tags ?? undefined,
    ...(xpubParent ? { xpubParent } : {}),
  };
}
