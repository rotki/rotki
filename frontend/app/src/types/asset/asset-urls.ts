import { Blockchain } from '@rotki/common';

export interface ExplorerUrls {
  readonly address: string;
  readonly block: string;
  readonly transaction?: string;
}

export type Chains = Blockchain | 'ETC';

export type AssetExplorerUrls = {
  [key in Chains]: ExplorerUrls;
};

export const explorerUrls: AssetExplorerUrls = {
  [Blockchain.ARBITRUM_ONE]: {
    address: 'https://arbiscan.io/address/',
    block: 'https://arbiscan.io/block/',
    transaction: 'https://arbiscan.io/tx/',
  },
  [Blockchain.AVAX]: {
    address: 'https://avascan.info/blockchain/c/address/',
    block: 'https://avascan.info/blockchain/c/block/',
    transaction: 'https://avascan.info/blockchain/c/tx/',
  },
  [Blockchain.BASE]: {
    address: 'https://basescan.org/address/',
    block: 'https://basescan.org/block/',
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
    transaction: 'https://bscscan.com/tx/',
  },
  [Blockchain.BTC]: {
    address: 'https://www.blockchain.com/explorer/addresses/btc/',
    block: 'https://www.blockchain.com/explorer/blocks/btc/',
    transaction: 'https://www.blockchain.com/explorer/transactions/btc/',
  },
  [Blockchain.DOT]: {
    address: 'https://explorer.polkascan.io/polkadot/account/',
    block: 'https://explorer.polkascan.io/polkadot/block/',
    transaction: 'https://explorer.polkascan.io/polkadot/transaction/',
  },
  [Blockchain.ETH]: {
    address: 'https://etherscan.io/address/',
    block: 'https://etherscan.io/block/',
    transaction: 'https://etherscan.io/tx/',
  },
  [Blockchain.ETH2]: {
    address: 'https://beaconcha.in/validator/',
    block: 'https://beaconcha.in/block/',
  },
  [Blockchain.GNOSIS]: {
    address: 'https://gnosisscan.io/address/',
    block: 'https://gnosisscan.io/block/',
    transaction: 'https://gnosisscan.io/tx/',
  },
  [Blockchain.KSM]: {
    address: 'https://explorer.polkascan.io/kusama/account/',
    block: 'https://explorer.polkascan.io/kusama/block/',
    transaction: 'https://explorer.polkascan.io/kusama/transaction/',
  },
  [Blockchain.OPTIMISM]: {
    address: 'https://optimistic.etherscan.io/address/',
    block: 'https://optimistic.etherscan.io/block/',
    transaction: 'https://optimistic.etherscan.io/tx/',
  },
  [Blockchain.POLYGON_POS]: {
    address: 'https://polygonscan.com/address/',
    block: 'https://polygonscan.com/block/',
    transaction: 'https://polygonscan.com/tx/',
  },
  [Blockchain.SCROLL]: {
    address: 'https://scrollscan.com/address/',
    block: 'https://scrollscan.com/block/',
    transaction: 'https://scrollscan.com/tx/',
  },
  [Blockchain.ZKSYNC_LITE]: {
    address: 'https://zkscan.io/explorer/accounts/',
    block: 'https://zkscan.io/explorer/blocks/',
    transaction: 'https://zkscan.io/explorer/transactions/',
  },
  ETC: {
    address: 'https://blockscout.com/etc/mainnet/address/',
    block: 'https://blockscout.com/etc/mainnet/block',
    transaction: 'https://blockscout.com/etc/mainnet/tx/',
  },
};

export function isChains(chain: string): chain is Chains {
  return Object.keys(explorerUrls).includes(chain);
}
