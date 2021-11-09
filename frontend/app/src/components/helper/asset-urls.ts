import { Blockchain } from '@rotki/common/lib/blockchain';

export type ExplorerUrls = {
  readonly address: string;
  readonly transaction: string;
};

type Chains = Blockchain | 'ETC' | 'zksync';

export type AssetExplorerUrls = {
  [key in Chains]: ExplorerUrls;
};

export const explorerUrls: AssetExplorerUrls = {
  ETH: {
    address: 'https://etherscan.io/address/',
    transaction: 'https://etherscan.io/tx/'
  },
  BTC: {
    address: 'https://blockstream.info/address/',
    transaction: 'https://blockstream.info/tx/'
  },
  ETC: {
    address: 'https://blockscout.com/etc/mainnet/address/',
    transaction: 'https://blockscout.com/etc/mainnet/tx/'
  },
  KSM: {
    address: 'https://polkascan.io/kusama/account/',
    transaction: 'https://polkascan.io/kusama/transaction/'
  },
  AVAX: {
    address: 'https://cchain.explorer.avax.network/address/',
    transaction: 'https://cchain.explorer.avax.network/tx/'
  },
  zksync: {
    address: 'https://zkscan.io/explorer/accounts/',
    transaction: 'https://zkscan.io/explorer/transactions/'
  },
  DOT: {
    address: 'https://polkascan.io/polkadot/account/',
    transaction: 'https://polkascan.io/polkadot/transaction/'
  }
};
