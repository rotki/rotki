import { externalLinks } from '@/data/external-links';

type EtherscanKey = keyof typeof externalLinks.etherscan;

export function isEtherscanKey(location: string): location is EtherscanKey {
  return location in externalLinks.etherscan;
}
