export const L2_LOOPRING = 'LRC';
export const SUPPORTED_SUB_BLOCKCHAIN_PROTOCOL = [L2_LOOPRING] as const;

export type SupportedSubBlockchainProtocol =
  (typeof SUPPORTED_SUB_BLOCKCHAIN_PROTOCOL)[number];
