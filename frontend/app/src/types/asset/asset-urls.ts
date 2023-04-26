import { type Blockchain } from '@rotki/common/lib/blockchain';

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
  ETH: {
    address: 'https://etherscan.io/address/',
    transaction: 'https://etherscan.io/tx/',
    block: 'https://etherscan.io/block/'
  },
  ETH2: {
    address: 'https://beaconcha.in/validator/',
    block: 'https://beaconcha.in/block/'
  },
  BTC: {
    address: 'https://www.blockchain.com/explorer/addresses/btc/',
    transaction: 'https://www.blockchain.com/explorer/transactions/btc/',
    block: 'https://www.blockchain.com/explorer/blocks/btc/'
  },
  BCH: {
    address: 'https://www.blockchain.com/explorer/addresses/bch/',
    transaction: 'https://www.blockchain.com/explorer/transactions/bch/',
    block: 'https://www.blockchain.com/explorer/blocks/bch/'
  },
  ETC: {
    address: 'https://blockscout.com/etc/mainnet/address/',
    transaction: 'https://blockscout.com/etc/mainnet/tx/',
    block: 'https://blockscout.com/etc/mainnet/block'
  },
  KSM: {
    address: 'https://explorer.polkascan.io/kusama/account/',
    transaction: 'https://explorer.polkascan.io/kusama/transaction/',
    block: 'https://explorer.polkascan.io/kusama/block/'
  },
  AVAX: {
    address: 'https://snowtrace.io/address/',
    transaction: 'https://snowtrace.io/tx/',
    block: 'https://snowtrace.io/block/'
  },
  zksync: {
    address: 'https://zkscan.io/explorer/accounts/',
    transaction: 'https://zkscan.io/explorer/transactions/',
    block: 'https://zkscan.io/explorer/blocks/'
  },
  DOT: {
    address: 'https://explorer.polkascan.io/polkadot/account/',
    transaction: 'https://explorer.polkascan.io/polkadot/transaction/',
    block: 'https://explorer.polkascan.io/polkadot/block/'
  },
  OPTIMISM: {
    address: 'https://optimistic.etherscan.io/address/',
    transaction: 'https://optimistic.etherscan.io/tx/',
    block: 'https://optimistic.etherscan.io/block/'
  }
};
