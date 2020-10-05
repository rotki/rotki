export type ExplorerUrls = {
  readonly address: string;
  readonly transaction: string;
};

export type AssetExplorerUrls = {
  [key in 'ETH' | 'BTC' | 'ETC']: ExplorerUrls;
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
  }
};
