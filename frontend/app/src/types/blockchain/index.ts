import type { BigNumber } from '@rotki/common';
import type { ActionDataEntry } from '@/types/action';
import { Routes } from '@/router/routes';
import { L2_LOOPRING, type SupportedSubBlockchainProtocol } from '@/types/protocols';

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2'],
};

export const SupportedSubBlockchainProtocolData: ActionDataEntry[] = [
  {
    detailPath: Routes.BALANCES_BLOCKCHAIN.toString(),
    identifier: L2_LOOPRING,
    image: './assets/images/protocols/loopring.svg',
    label: 'Loopring',
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
