import { Blockchain } from '@rotki/common/lib/blockchain';

export interface ExplorerUrls {
  readonly address: string;
  readonly block: string;
  readonly transaction?: string;
}

export type Chains = Blockchain | 'ETC' | 'zksync';

export type AssetExplorerUrls = {
  [key in Chains]: ExplorerUrls;
};

export const explorerUrls: AssetExplorerUrls = {
  [Blockchain.ETH]: {
    address: 'https://etherscan.io/address/',
    transaction: 'https://etherscan.io/tx/',
    block: 'https://etherscan.io/block/'
  },
  [Blockchain.ETH2]: {
    address: 'https://beaconcha.in/validator/',
    block: 'https://beaconcha.in/block/'
  },
  [Blockchain.BTC]: {
    address: 'https://www.blockchain.com/explorer/addresses/btc/',
    transaction: 'https://www.blockchain.com/explorer/transactions/btc/',
    block: 'https://www.blockchain.com/explorer/blocks/btc/'
  },
  [Blockchain.BCH]: {
    address: 'https://www.blockchain.com/explorer/addresses/bch/',
    transaction: 'https://www.blockchain.com/explorer/transactions/bch/',
    block: 'https://www.blockchain.com/explorer/blocks/bch/'
  },
  ETC: {
    address: 'https://blockscout.com/etc/mainnet/address/',
    transaction: 'https://blockscout.com/etc/mainnet/tx/',
    block: 'https://blockscout.com/etc/mainnet/block'
  },
  [Blockchain.KSM]: {
    address: 'https://explorer.polkascan.io/kusama/account/',
    transaction: 'https://explorer.polkascan.io/kusama/transaction/',
    block: 'https://explorer.polkascan.io/kusama/block/'
  },
  [Blockchain.AVAX]: {
    address: 'https://snowtrace.io/address/',
    transaction: 'https://snowtrace.io/tx/',
    block: 'https://snowtrace.io/block/'
  },
  zksync: {
    address: 'https://zkscan.io/explorer/accounts/',
    transaction: 'https://zkscan.io/explorer/transactions/',
    block: 'https://zkscan.io/explorer/blocks/'
  },
  [Blockchain.DOT]: {
    address: 'https://explorer.polkascan.io/polkadot/account/',
    transaction: 'https://explorer.polkascan.io/polkadot/transaction/',
    block: 'https://explorer.polkascan.io/polkadot/block/'
  },
  [Blockchain.OPTIMISM]: {
    address: 'https://optimistic.etherscan.io/address/',
    transaction: 'https://optimistic.etherscan.io/tx/',
    block: 'https://optimistic.etherscan.io/block/'
  },
  [Blockchain.POLYGON_POS]: {
    address: 'https://polygonscan.com/address/',
    transaction: 'https://polygonscan.com/tx/',
    block: 'https://polygonscan.com/block/'
  },
  [Blockchain.ARBITRUM_ONE]: {
    address: 'https://arbiscan.io/address/',
    transaction: 'https://arbiscan.io/tx/',
    block: 'https://arbiscan.io/block/'
  },
  [Blockchain.BASE]: {
    address: 'https://basescan.org/address/',
    transaction: 'https://basescan.org/tx/',
    block: 'https://basescan.org/block/'
  },
  [Blockchain.GNOSIS]: {
    address: 'https://gnosisscan.io/address/',
    transaction: 'https://gnosisscan.io/tx/',
    block: 'https://gnosisscan.io/block/'
  }
};
