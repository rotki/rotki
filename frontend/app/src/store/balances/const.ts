import { ChainSections } from '@/store/balances/types';
import { Section } from '@/store/const';

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
