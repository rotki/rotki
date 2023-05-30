import { Blockchain } from '@rotki/common/lib/blockchain';
import { EvmTokenKind } from '@rotki/common/lib/data';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;
const EthChains = [Blockchain.ETH, Blockchain.ETH2] as const;
const RestChains = [
  Blockchain.KSM,
  Blockchain.DOT,
  Blockchain.AVAX,
  Blockchain.OPTIMISM,
  Blockchain.POLYGON_POS
] as const;
const TokenChains = [Blockchain.ETH, Blockchain.OPTIMISM] as const;

export type BtcChains = (typeof BtcChains)[number];
export type EthChains = (typeof EthChains)[number];
export type RestChains = (typeof RestChains)[number];
export type TokenChains = (typeof TokenChains)[number];

export const isBtcChain = (chain: Blockchain): chain is BtcChains =>
  BtcChains.includes(chain as any);
export const isEthChain = (chain: Blockchain): chain is EthChains =>
  EthChains.includes(chain as any);
export const isRestChain = (chain: Blockchain): chain is RestChains =>
  RestChains.includes(chain as any);
export const isTokenChain = (chain: Blockchain): chain is TokenChains =>
  TokenChains.includes(chain as any);

export const isBlockchain = (chain: string): chain is Blockchain =>
  Object.values(Blockchain).includes(chain as any);

export const evmTokenKindsData = [
  {
    identifier: EvmTokenKind.ERC20,
    label: 'ERC20'
  },
  {
    identifier: EvmTokenKind.ERC721,
    label: 'ERC721'
  }
];
