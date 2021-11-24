export const L2_LOOPRING = 'LRC';
export const L2_PROTOCOLS = [L2_LOOPRING] as const;
export type SupportedL2Protocol = typeof L2_PROTOCOLS[number];
