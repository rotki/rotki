import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Routes } from '@/router/routes';
import { ChainSections } from '@/store/balances/types';
import { ActionDataEntry } from '@/store/types';
import { L2_LOOPRING, SupportedSubBlockchainProtocol } from '@/types/protocols';
import { Section } from '@/types/status';

export const chainSection: ChainSections = {
  BTC: Section.BLOCKCHAIN_BTC,
  BCH: Section.BLOCKCHAIN_BCH,
  ETH: Section.BLOCKCHAIN_ETH,
  ETH2: Section.BLOCKCHAIN_ETH2,
  KSM: Section.BLOCKCHAIN_KSM,
  DOT: Section.BLOCKCHAIN_DOT,
  AVAX: Section.BLOCKCHAIN_AVAX
};

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2']
};

export const SupportedSubBlockchainProtocolData: ActionDataEntry[] = [
  {
    identifier: L2_LOOPRING,
    label: 'Loopring',
    icon: '/assets/images/modules/loopring.svg',
    detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}#blockchain-balances-LRC`
  }
];

export interface SubBlockchainTotal {
  readonly protocol: SupportedSubBlockchainProtocol;
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}

export interface BlockchainTotal {
  readonly chain: Blockchain;
  readonly children: SubBlockchainTotal[];
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}
