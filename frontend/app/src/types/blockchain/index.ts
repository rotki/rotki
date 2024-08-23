import { Routes } from '@/router/routes';
import { L2_LOOPRING, type SupportedSubBlockchainProtocol } from '@/types/protocols';
import type { BigNumber } from '@rotki/common';
import type { ActionDataEntry } from '@/types/action';

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2'],
};

export const SupportedSubBlockchainProtocolData: ActionDataEntry[] = [
  {
    identifier: L2_LOOPRING,
    label: 'Loopring',
    image: './assets/images/protocols/loopring.svg',
    detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}`,
  },
];

export interface SubBlockchainTotal {
  readonly protocol: SupportedSubBlockchainProtocol;
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}

export interface BlockchainTotal {
  readonly chain: string;
  readonly children: SubBlockchainTotal[];
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}
