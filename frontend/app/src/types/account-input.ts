export const METAMASK_IMPORT = 'metamask_import';
export const MANUAL_ADD = 'manual_add';
export const XPUB_ADD = 'xpub_add';

export const ETH_INPUT = [MANUAL_ADD, METAMASK_IMPORT] as const;
export const BTC_INPUT = [MANUAL_ADD, XPUB_ADD] as const;
type EthInput = typeof ETH_INPUT[number];
type BtcInput = typeof BTC_INPUT[number];
export type AccountInput = EthInput | BtcInput;
