import { XpubKeyType } from '@/types/blockchain/accounts';

export enum XpubPrefix {
  P2TR = 'p2tr',
  XPUB = 'xpub',
  YPUB = 'ypub',
  ZPUB = 'zpub',
}

export interface XpubType {
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
    label: XPUB_LABEL,
    value: XpubPrefix.XPUB,
  },
  {
    label: YPUB_LABEL,
    value: XpubPrefix.YPUB,
  },
  {
    label: ZPUB_LABEL,
    value: XpubPrefix.ZPUB,
  },
  {
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
