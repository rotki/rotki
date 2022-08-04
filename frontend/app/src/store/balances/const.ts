import { Routes } from '@/router/routes';
import { ChainSections } from '@/store/balances/types';
import { Section } from '@/store/const';
import { ActionDataEntry } from '@/store/types';
import { L2_LOOPRING } from '@/types/protocols';

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
    detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}#blockchain-balances-LRC`
  }
];
