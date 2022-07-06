export const L2_LOOPRING = 'LRC';
export const UNISWAP_V3_LP = 'UNISWAP_V3_LP';
export const SUPPORTED_SUB_BLOCKCHAIN_PROTOCOL = [
  L2_LOOPRING,
  UNISWAP_V3_LP
] as const;

export type SupportedSubBlockchainProtocol =
  typeof SUPPORTED_SUB_BLOCKCHAIN_PROTOCOL[number];
