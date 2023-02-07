import { type BigNumber } from '@rotki/common';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { Routes } from '@/router/routes';
import {
  L2_LOOPRING,
  type SupportedSubBlockchainProtocol
} from '@/types/protocols';
import { Section } from '@/types/status';
import { type ActionDataEntry } from '@/types/action';
import { type ChainSections } from '@/types/blockchain/accounts';

export const chainSection: ChainSections = {
  BTC: Section.BLOCKCHAIN_BTC,
  BCH: Section.BLOCKCHAIN_BCH,
  ETH: Section.BLOCKCHAIN_ETH,
  ETH2: Section.BLOCKCHAIN_ETH2,
  KSM: Section.BLOCKCHAIN_KSM,
  DOT: Section.BLOCKCHAIN_DOT,
  AVAX: Section.BLOCKCHAIN_AVAX,
  OPTIMISM: Section.BLOCKCHAIN_OPTIMISM
};

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2']
};

export const SupportedSubBlockchainProtocolData: ActionDataEntry[] = [
  {
    identifier: L2_LOOPRING,
    label: 'Loopring',
    icon: './assets/images/modules/loopring.svg',
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
