import { ChainSections } from '@/store/balances/types';
import { Section } from '@/store/const';

export const chainSection: ChainSections = {
  BTC: Section.BLOCKCHAIN_BTC,
  ETH: Section.BLOCKCHAIN_ETH,
  KSM: Section.BLOCKCHAIN_KSM
};

export const KRAKEN_ACCOUNT_TYPES = ['starter', 'intermediate', 'pro'] as const;
