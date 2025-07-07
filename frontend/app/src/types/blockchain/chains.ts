import { Blockchain, EvmTokenKind, SolanaTokenKind } from '@rotki/common';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;

export type BtcChains = (typeof BtcChains)[number];

export function isBtcChain(chain: string): chain is BtcChains {
  return BtcChains.includes(chain as any);
}

export function isBlockchain(chain: string): chain is Blockchain {
  return Object.values(Blockchain).includes(chain as any);
}

export interface EvmTokenData {
  identifier: EvmTokenKind;
  label: string;
}

export const evmTokenKindsData: EvmTokenData[] = [
  {
    identifier: EvmTokenKind.ERC20,
    label: 'ERC20',
  },
  {
    identifier: EvmTokenKind.ERC721,
    label: 'ERC721',
  },
];

export interface SolanaTokenData {
  identifier: SolanaTokenKind;
  label: string;
}

export const solanaTokenKindsData: SolanaTokenData[] = [
  {
    identifier: SolanaTokenKind.SPL_TOKEN,
    label: 'SPL Token',
  },
  {
    identifier: SolanaTokenKind.SPL_NFT,
    label: 'SPL NFT',
  },
];
