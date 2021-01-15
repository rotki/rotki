import { ChainSections } from '@/store/balances/types';
import { Section } from '@/store/const';

export const chainSection: ChainSections = {
  BTC: Section.BLOCKCHAIN_BTC,
  ETH: Section.BLOCKCHAIN_ETH,
  KSM: Section.BLOCKCHAIN_KSM
};
