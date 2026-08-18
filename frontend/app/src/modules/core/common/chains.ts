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

/**
 * The canonical, snake_case chain id, for keying or comparing chains that arrive from producers
 * spelling them differently: `polygon_pos` in the app, `POLYGON_POS` over the websocket (the
 * `SupportedBlockchain` value), `polygonPos` from anything that has been through the camelCase
 * response transformer.
 *
 * Splits only on a lower-to-upper boundary, so an id that is already snake_case or upper snake is
 * left intact and merely lower-cased.
 */
export function toChainKey(chain: string): string {
  return chain.replace(/([a-z\d])([A-Z])/gu, '$1_$2').toLowerCase();
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
