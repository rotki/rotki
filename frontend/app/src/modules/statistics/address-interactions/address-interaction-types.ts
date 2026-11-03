export interface AddressInteraction {
  chain: string;
  source: string;
  target: string;
  targetChain?: string;
  targetTxHash?: string;
  txHash: string;
}
