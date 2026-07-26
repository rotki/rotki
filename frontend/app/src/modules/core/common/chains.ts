import { Blockchain, EvmTokenKind, SolanaTokenKind } from '@rotki/common';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';

const BtcChains = [Blockchain.BTC, Blockchain.BCH] as const;

export type BtcChains = (typeof BtcChains)[number];

const btcChains = new Set<string>(BtcChains);
const isBlockchainValue = isOfEnum(Blockchain);

export function isBtcChain(chain: string): chain is BtcChains {
  return btcChains.has(chain);
}

export function isBlockchain(chain: string): chain is Blockchain {
  return isBlockchainValue(chain);
}

interface EvmTokenData {
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

interface SolanaTokenData {
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
