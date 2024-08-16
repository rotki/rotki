type EtherscanKey = keyof typeof etherscanLinks;

export function isEtherscanKey(location: string): location is EtherscanKey {
  return location in etherscanLinks;
}
