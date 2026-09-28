import { type Brand, make } from 'plainfp/brand';
import {
  type AccountIdentity,
  AccountKind,
  type AddressAccount,
  type AddressIdentity,
  type ValidatorAccount,
  type ValidatorIdentity,
  type XpubIdentity,
  type XpubKey,
} from '@/modules/accounts/blockchain-accounts';

/**
 * The key of an accounts-table group row: an address, a validator public key, or an xpub on a chain.
 *
 * @remarks
 * Keys the chain exclusions and the `expanded` ids a URL carries, so its format is kept stable.
 */
export type AccountGroupId = Brand<string, 'AccountGroupId'>;

/** The key of one account on one chain. */
export type AccountId = Brand<string, 'AccountId'>;

type KindHandlers<T extends AccountIdentity, R> = {
  readonly [K in AccountKind]: (item: T & { readonly kind: K }) => R;
};

/**
 * Runs the handler for the item's kind. Every kind needs a handler, so adding one fails to compile
 * until each call site decides what it means there.
 *
 * @throws Error for an item whose `kind` is none of the known ones, which only untyped data can carry.
 */
export function matchKind<T extends AccountIdentity, R>(item: T, handlers: KindHandlers<T, R>): R {
  if (isAddressAccount(item))
    return handlers.address(item);
  if (isXpubAccount(item))
    return handlers.xpub(item);
  if (isValidatorAccount(item))
    return handlers.validator(item);
  throw new Error(`Unknown account kind: ${String(Reflect.get(item, 'kind'))}`);
}

export function isAddressAccount<T extends AccountIdentity>(account: T): account is T & AddressIdentity {
  return account.kind === AccountKind.ADDRESS;
}

export function isValidatorAccount<T extends AccountIdentity>(account: T): account is T & ValidatorIdentity {
  return account.kind === AccountKind.VALIDATOR;
}

export function isXpubAccount<T extends AccountIdentity>(account: T): account is T & XpubIdentity {
  return account.kind === AccountKind.XPUB;
}

export function getXpubId(key: XpubKey): string {
  if (!key.derivationPath)
    return key.xpub;

  return `${key.xpub}#${key.derivationPath}`;
}

/** The group of an xpub and every address derived from it on that chain. */
export function getXpubGroupId(key: XpubKey, chain: string): AccountGroupId {
  return make<string, 'AccountGroupId'>(`${getXpubId(key)}#${chain}`);
}

function getIdentityId(identity: AccountIdentity): string {
  return matchKind(identity, {
    address: ({ address }) => address,
    validator: ({ publicKey }) => publicKey,
    xpub: key => getXpubId(key),
  });
}

export function getGroupId(group: AccountIdentity & { chains: string[] }): AccountGroupId {
  if (isXpubAccount(group))
    return getXpubGroupId(group, getChain(group) ?? '');

  return make<string, 'AccountGroupId'>(getIdentityId(group));
}

/** The group an account belongs to: its xpub's when derived from one, its own otherwise. */
export function getAccountGroupId(account: AddressAccount | ValidatorAccount): AccountGroupId {
  if (isAddressAccount(account) && account.xpubParent)
    return getXpubGroupId(account.xpubParent, account.chain);

  return make<string, 'AccountGroupId'>(getIdentityId(account));
}

export function getAccountId(account: AccountIdentity & { chain: string }): AccountId {
  return make<string, 'AccountId'>(`${getIdentityId(account)}#${account.chain}`);
}

export function getAccountAddress(account: AccountIdentity): string {
  return matchKind(account, {
    address: ({ address }) => address,
    validator: ({ publicKey }) => publicKey,
    xpub: ({ xpub }) => xpub,
  });
}

export function getAccountLabel(account: AccountIdentity & { label?: string }): string {
  if (account.label)
    return account.label;

  return matchKind(account, {
    address: ({ address }) => address,
    validator: ({ index }) => index.toString(),
    xpub: ({ xpub }) => xpub,
  });
}

export function getChain(account: { chain: string } | { chains: string[] }): string | undefined {
  if ('chain' in account)
    return account.chain;
  else if ('chains' in account && account.chains.length > 0)
    return account.chains[0];
  return undefined;
}
