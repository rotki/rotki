import { XpubKeyType, XpubPayload } from '@/store/balances/types';

export enum XpubPrefix {
  P2TR = 'p2tr',
  XPUB = 'xpub',
  YPUB = 'ypub',
  ZPUB = 'zpub'
}

export type XpubType = {
  readonly label: string;
  readonly value: XpubPrefix;
};

const P2TR_LABEL = 'P2TR';
const XPUB_LABEL = 'P2PKH';
const YPUB_LABEL = 'P2SH-P2WPKH';
const ZPUB_LABEL = 'WPKH';

export const getKeyType: (key: XpubPrefix) => XpubKeyType = key => {
  if (key === XpubPrefix.XPUB) {
    return XpubKeyType.XPUB;
  } else if (key === XpubPrefix.YPUB) {
    return XpubKeyType.YPUB;
  } else if (key === XpubPrefix.ZPUB) {
    return XpubKeyType.ZPUB;
  } else if (key === XpubPrefix.P2TR) {
    return XpubKeyType.P2TR;
  }
  throw new Error(`${key} is not acceptable`);
};

export const getPrefix: (type?: XpubKeyType) => XpubPrefix = type => {
  if (type === XpubKeyType.YPUB) {
    return XpubPrefix.YPUB;
  } else if (type === XpubKeyType.ZPUB) {
    return XpubPrefix.ZPUB;
  }
  return XpubPrefix.XPUB;
};

export const keyType: XpubType[] = [
  {
    label: XPUB_LABEL,
    value: XpubPrefix.XPUB
  },
  {
    label: YPUB_LABEL,
    value: XpubPrefix.YPUB
  },
  {
    label: ZPUB_LABEL,
    value: XpubPrefix.ZPUB
  },
  {
    label: P2TR_LABEL,
    value: XpubPrefix.P2TR
  }
];

export const isPrefixed = (value: string) => value.match(/([xzy]pub)(.*)/);

export const xpubToPayload = (xpub: string, path: string | null) => {
  const match = isPrefixed(xpub);
  let key = xpub;
  let prefix: XpubPrefix = XpubPrefix.XPUB;

  if (match) {
    key = match[0];
    prefix = match[1] as XpubPrefix;
  }

  return {
    xpub: key,
    xpubType: getKeyType(prefix),
    derivationPath: path
  } as XpubPayload;
};
