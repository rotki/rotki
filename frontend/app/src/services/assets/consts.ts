import { EvmChain, EvmTokenKind } from '@rotki/common/lib/data';

export const RESOLVE_REMOTE = 'remote';
export const RESOLVE_LOCAL = 'local';

export const CONFLICT_RESOLUTION = [RESOLVE_REMOTE, RESOLVE_LOCAL] as const;
export const EVM_TOKEN = 'evm token';

export const evmChainsData = [
  {
    identifier: EvmChain.ETHEREUM,
    label: 'Ethereum'
  },
  {
    identifier: EvmChain.OPTIMISM,
    label: 'Optimism'
  },
  {
    identifier: EvmChain.BINANCE,
    label: 'Binance'
  },
  {
    identifier: EvmChain.GNOSIS,
    label: 'Gnosis'
  },
  {
    identifier: EvmChain.MATIC,
    label: 'Matic'
  },
  {
    identifier: EvmChain.FANTOM,
    label: 'Fantom'
  },
  {
    identifier: EvmChain.ARBITRUM,
    label: 'Arbitrum'
  },
  {
    identifier: EvmChain.AVALANCHE,
    label: 'Avalanche'
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
