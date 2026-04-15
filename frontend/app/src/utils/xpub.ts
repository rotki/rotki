import { isValidBchAddress, isValidBtcAddress } from '@rotki/common';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';

export enum XpubPrefix {
  P2TR = 'p2tr',
  XPUB = 'xpub',
  YPUB = 'ypub',
  ZPUB = 'zpub',
}

export interface XpubType {
  readonly humanLabel: string;
  readonly label: string;
  readonly value: XpubPrefix;
}

const P2TR_LABEL = 'P2TR';
const XPUB_LABEL = 'P2PKH';
const YPUB_LABEL = 'P2SH-P2WPKH';
const ZPUB_LABEL = 'WPKH';

export const getKeyType: (key: XpubPrefix) => XpubKeyType = (key) => {
  if (key === XpubPrefix.XPUB)
    return XpubKeyType.XPUB;
  else if (key === XpubPrefix.YPUB)
    return XpubKeyType.YPUB;
  else if (key === XpubPrefix.ZPUB)
    return XpubKeyType.ZPUB;
  else if (key === XpubPrefix.P2TR)
    return XpubKeyType.P2TR;

  throw new Error(`${key as any} is invalid`);
};

export const getPrefix: (type?: XpubKeyType) => XpubPrefix = (type) => {
  if (type === XpubKeyType.YPUB)
    return XpubPrefix.YPUB;
  else if (type === XpubKeyType.ZPUB)
    return XpubPrefix.ZPUB;

  return XpubPrefix.XPUB;
};

export const keyType: XpubType[] = [
  {
    humanLabel: 'Legacy',
    label: XPUB_LABEL,
    value: XpubPrefix.XPUB,
  },
  {
    humanLabel: 'SegWit',
    label: YPUB_LABEL,
    value: XpubPrefix.YPUB,
  },
  {
    humanLabel: 'Native SegWit',
    label: ZPUB_LABEL,
    value: XpubPrefix.ZPUB,
  },
  {
    humanLabel: 'Taproot',
    label: P2TR_LABEL,
    value: XpubPrefix.P2TR,
  },
];

export function isPrefixed(value: string): RegExpMatchArray | null {
  return value.match(/([x-z]pub)(.*)/);
}

export function guessPrefix(key: string): XpubPrefix {
  const match = isPrefixed(key);
  if (!match) {
    throw new Error('Invalid key, key should be prefixed with xpub, ypub or zpub');
  }
  const prefix = match?.[1] ?? XpubPrefix.XPUB;
  return prefix as XpubPrefix;
}

/**
 * Returns true for plain BTC/BCH addresses (P2PKH, P2SH, bech32, Taproot, CashAddr).
 */
export function isBtcAddress(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed)
    return false;

  return isValidBtcAddress(trimmed) || isValidBchAddress(trimmed);
}

export type DetectionResult = XpubPrefix | 'address' | 'ambiguous' | null;

/**
 * Detects the xpub type from the key prefix.
 * Returns 'address' for plain BTC addresses, 'ambiguous' for xpub prefix
 * (shared by P2PKH and P2TR), or the specific XpubPrefix for ypub/zpub.
 */
export function detectXpubType(value: string): DetectionResult {
  const trimmed = value.trim();
  if (!trimmed)
    return null;

  if (isBtcAddress(trimmed))
    return 'address';

  if (trimmed.startsWith('ypub'))
    return XpubPrefix.YPUB;

  if (trimmed.startsWith('zpub'))
    return XpubPrefix.ZPUB;

  if (trimmed.startsWith('xpub'))
    return 'ambiguous';

  return null;
}
