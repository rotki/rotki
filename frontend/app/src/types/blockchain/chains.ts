import { Blockchain, TokenKind } from '@rotki/common';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;

export type BtcChains = (typeof BtcChains)[number];

export function isBtcChain(chain: string): chain is BtcChains {
  return BtcChains.includes(chain as any);
}

export function isBlockchain(chain: string): chain is Blockchain {
  return Object.values(Blockchain).includes(chain as any);
}

export interface EvmTokenData {
  identifier: TokenKind;
  label: string;
}

export const evmTokenKindsData: EvmTokenData[] = [
  {
    identifier: TokenKind.ERC20,
    label: 'ERC20',
  },
  {
    identifier: TokenKind.ERC721,
    label: 'ERC721',
  },
];
