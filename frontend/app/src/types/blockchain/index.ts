import { type BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Routes } from '@/router/routes';
import {
  L2_LOOPRING,
  type SupportedSubBlockchainProtocol
} from '@/types/protocols';
import { Section } from '@/types/status';
import { type ActionDataEntry } from '@/types/action';
import { type ChainSections } from '@/types/blockchain/accounts';

export const chainSection: ChainSections = {
  [Blockchain.BTC]: Section.BLOCKCHAIN_BTC,
  [Blockchain.BCH]: Section.BLOCKCHAIN_BCH,
  [Blockchain.ETH]: Section.BLOCKCHAIN_ETH,
  [Blockchain.ETH2]: Section.BLOCKCHAIN_ETH2,
  [Blockchain.KSM]: Section.BLOCKCHAIN_KSM,
  [Blockchain.DOT]: Section.BLOCKCHAIN_DOT,
  [Blockchain.AVAX]: Section.BLOCKCHAIN_AVAX,
  [Blockchain.OPTIMISM]: Section.BLOCKCHAIN_OPTIMISM,
  [Blockchain.POLYGON_POS]: Section.BLOCKCHAIN_POLYGON,
  [Blockchain.ARBITRUM_ONE]: Section.BLOCKCHAIN_ARBITRUM
};

export const samePriceAssets: Record<string, string[]> = {
  ETH: ['ETH2']
};

export const SupportedSubBlockchainProtocolData: ActionDataEntry[] = [
  {
    identifier: L2_LOOPRING,
    label: 'Loopring',
    icon: './assets/images/protocols/loopring.svg',
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
