import { blockscoutLinks, etherscanLinks } from '@shared/external-links';

type EtherscanKey = keyof typeof etherscanLinks;

type BlockscoutKey = keyof typeof blockscoutLinks;

export function isEtherscanKey(location: string): location is EtherscanKey {
  return location in etherscanLinks;
}

export function isBlockscoutKey(location: string): location is BlockscoutKey {
  return location in blockscoutLinks;
}
