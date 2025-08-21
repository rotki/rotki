import { Blockchain } from '@rotki/common';

export interface ExplorerUrls {
  readonly address: string;
  readonly block: string;
  readonly transaction?: string;
  readonly token?: string;
}

export type Chains = Blockchain | 'ETC';

export type AssetExplorerUrls = {
  [key in Chains]: ExplorerUrls;
};

export const explorerUrls: AssetExplorerUrls = {
  [Blockchain.ARBITRUM_ONE]: {
    address: 'https://arbiscan.io/address/',
    block: 'https://arbiscan.io/block/',
    token: 'https://arbiscan.io/token/',
    transaction: 'https://arbiscan.io/tx/',
  },
  [Blockchain.AVAX]: {
    address: 'https://avascan.info/blockchain/c/address/',
    block: 'https://avascan.info/blockchain/c/block/',
    token: 'https://avascan.info/blockchain/c/token/',
    transaction: 'https://avascan.info/blockchain/c/tx/',
  },
  [Blockchain.BASE]: {
    address: 'https://basescan.org/address/',
    block: 'https://basescan.org/block/',
    token: 'https://basescan.org/token/',
    transaction: 'https://basescan.org/tx/',
  },
  [Blockchain.BCH]: {
    address: 'https://www.blockchain.com/explorer/addresses/bch/',
    block: 'https://www.blockchain.com/explorer/blocks/bch/',
    transaction: 'https://www.blockchain.com/explorer/transactions/bch/',
  },
  [Blockchain.BSC]: {
    address: 'https://bscscan.com/address/',
    block: 'https://bscscan.com/block/',
    token: 'https://bscscan.com/token/',
    transaction: 'https://bscscan.com/tx/',
  },
  [Blockchain.BTC]: {
    address: 'https://www.blockchain.com/explorer/addresses/btc/',
    block: 'https://www.blockchain.com/explorer/blocks/btc/',
    transaction: 'https://www.blockchain.com/explorer/transactions/btc/',
  },
  [Blockchain.DOT]: {
    address: 'https://polkadot.subscan.io/account/',
    block: 'https://polkadot.subscan.io/block',
  },
  [Blockchain.ETH]: {
    address: 'https://etherscan.io/address/',
    block: 'https://etherscan.io/block/',
    token: 'https://etherscan.io/token/',
    transaction: 'https://etherscan.io/tx/',
  },
  [Blockchain.ETH2]: {
    address: 'https://beaconcha.in/validator/',
    block: 'https://beaconcha.in/block/',
  },
  [Blockchain.GNOSIS]: {
    address: 'https://gnosisscan.io/address/',
    block: 'https://gnosisscan.io/block/',
    token: 'https://gnosisscan.io/token/',
    transaction: 'https://gnosisscan.io/tx/',
  },
  [Blockchain.KSM]: {
    address: 'https://kusama.subscan.io/account/',
    block: 'https://kusama.subscan.io/block',
  },
  [Blockchain.OPTIMISM]: {
    address: 'https://optimistic.etherscan.io/address/',
    block: 'https://optimistic.etherscan.io/block/',
    token: 'https://optimistic.etherscan.io/token/',
    transaction: 'https://optimistic.etherscan.io/tx/',
  },
  [Blockchain.POLYGON_POS]: {
    address: 'https://polygonscan.com/address/',
    block: 'https://polygonscan.com/block/',
    token: 'https://polygonscan.com/token/',
    transaction: 'https://polygonscan.com/tx/',
  },
  [Blockchain.SCROLL]: {
    address: 'https://scrollscan.com/address/',
    block: 'https://scrollscan.com/block/',
    token: 'https://scrollscan.com/token/',
    transaction: 'https://scrollscan.com/tx/',
  },
  [Blockchain.SOLANA]: {
    address: 'https://solscan.io/account/',
    block: 'solscan.io/block/',
  },
  [Blockchain.ZKSYNC_LITE]: {
    address: 'https://zkscan.io/explorer/accounts/',
    block: 'https://zkscan.io/explorer/blocks/',
    transaction: 'https://zkscan.io/explorer/transactions/',
  },
  ETC: {
    address: 'https://blockscout.com/etc/mainnet/address/',
    block: 'https://blockscout.com/etc/mainnet/block',
    token: 'https://blockscout.com/etc/mainnet/token/',
    transaction: 'https://blockscout.com/etc/mainnet/tx/',
  },
};

export function isChains(chain: string): chain is Chains {
  return Object.keys(explorerUrls).includes(chain);
}
