import { Blockchain } from '@rotki/common/lib/blockchain';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;
const EthChains = [Blockchain.ETH, Blockchain.ETH2] as const;
const RestChains = [Blockchain.KSM, Blockchain.DOT, Blockchain.AVAX] as const;

export type BtcChains = typeof BtcChains[number];
export type EthChains = typeof EthChains[number];
export type RestChains = typeof RestChains[number];

export const isBtcChain = (chain: Blockchain): chain is BtcChains =>
  BtcChains.includes(chain as any);
export const isEthChain = (chain: Blockchain): chain is EthChains =>
  EthChains.includes(chain as any);
export const isRestChain = (chain: Blockchain): chain is RestChains =>
  RestChains.includes(chain as any);
