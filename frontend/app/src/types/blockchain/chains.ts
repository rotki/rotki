import { Blockchain } from '@rotki/common/lib/blockchain';
import { EvmTokenKind } from '@rotki/common/lib/data';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;
const EthChains = [Blockchain.ETH, Blockchain.ETH2] as const;
const RestChains = [
  Blockchain.KSM,
  Blockchain.DOT,
  Blockchain.AVAX,
  Blockchain.OPTIMISM,
  Blockchain.POLYGON_POS,
  Blockchain.ARBITRUM_ONE,
  Blockchain.BASE,
  Blockchain.GNOSIS,
  Blockchain.SCROLL,
] as const;

export type BtcChains = (typeof BtcChains)[number];

export type EthChains = (typeof EthChains)[number];

export type RestChains = (typeof RestChains)[number];

export function isBtcChain(chain: Blockchain): chain is BtcChains {
  return BtcChains.includes(chain as any);
}

export function isEthChain(chain: Blockchain): chain is EthChains {
  return EthChains.includes(chain as any);
}

export function isRestChain(chain: Blockchain): chain is RestChains {
  return RestChains.includes(chain as any);
}

export function isBlockchain(chain: string): chain is Blockchain {
  return Object.values(Blockchain).includes(chain as any);
}

export const evmTokenKindsData = [
  {
    identifier: EvmTokenKind.ERC20,
    label: 'ERC20',
  },
  {
    identifier: EvmTokenKind.ERC721,
    label: 'ERC721',
  },
];
