export interface AddressInteraction {
  chain: string;
  /** The exchange deposit address both accounts used, when that is what links them. */
  depositAddress?: string;
  depositExchange?: string;
  source: string;
  target: string;
  targetChain?: string;
  targetTxHash?: string;
  txHash: string;
}
