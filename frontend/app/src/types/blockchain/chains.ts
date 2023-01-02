import { Blockchain } from '@rotki/common/lib/blockchain';
import { EvmChain, EvmTokenKind } from '@rotki/common/lib/data';
import { type Nullable } from '@rotki/common';
import { type ActionDataEntry } from '@/store/types';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;
const EthChains = [Blockchain.ETH, Blockchain.ETH2] as const;
const RestChains = [
  Blockchain.KSM,
  Blockchain.DOT,
  Blockchain.AVAX,
  Blockchain.OPTIMISM
] as const;
const TokenChains = [Blockchain.ETH, Blockchain.OPTIMISM] as const;

export type BtcChains = typeof BtcChains[number];
export type EthChains = typeof EthChains[number];
export type RestChains = typeof RestChains[number];
export type TokenChains = typeof TokenChains[number];

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

export const evmChainsData: ActionDataEntry[] = [
  {
    identifier: EvmChain.ETHEREUM,
    label: 'Ethereum',
    image: './assets/images/modules/eth.svg'
  },
  {
    identifier: EvmChain.OPTIMISM,
    label: 'Optimism',
    image: './assets/images/chains/optimism.svg'
  },
  {
    identifier: EvmChain.BINANCE,
    label: 'Binance',
    image: './assets/images/chains/binance.svg'
  },
  {
    identifier: EvmChain.GNOSIS,
    label: 'Gnosis',
    image: './assets/images/chains/gnosis.svg'
  },
  {
    identifier: EvmChain.MATIC,
    label: 'Matic',
    image: './assets/images/chains/matic.svg'
  },
  {
    identifier: EvmChain.FANTOM,
    label: 'Fantom',
    image: './assets/images/chains/fantom.svg'
  },
  {
    identifier: EvmChain.ARBITRUM,
    label: 'Arbitrum',
    image: './assets/images/chains/arbitrum.svg'
  },
  {
    identifier: EvmChain.AVALANCHE,
    label: 'Avalanche',
    image: './assets/images/chains/avalanche.svg'
  },
  {
    identifier: EvmChain.CELO,
    label: 'Celo',
    image: './assets/images/chains/celo.svg'
  }
];

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

export const getChainData = (
  chain?: Nullable<EvmChain>
): ActionDataEntry | null => {
  if (!chain) return null;
  return evmChainsData.find(({ identifier }) => identifier === chain) || null;
};
