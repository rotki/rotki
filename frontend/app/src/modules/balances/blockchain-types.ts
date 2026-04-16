import type { BigNumber } from '@rotki/common';

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2'],
};

export interface BlockchainTotal {
  readonly chain: string;
  readonly value: BigNumber;
  readonly loading: boolean;
}

export const LOOPRING_CHAIN = 'loopring';
