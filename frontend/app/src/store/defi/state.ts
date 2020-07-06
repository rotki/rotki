import {
  AaveBalances,
  AaveHistory,
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  MakerDAOVaultDetails
} from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

export interface DefiState {
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
  makerDAOVaults: MakerDAOVault[];
  makerDAOVaultDetails: MakerDAOVaultDetails[];
  aaveBalances: AaveBalances;
  aaveHistory: AaveHistory;
}

export const defaultState = (): DefiState => ({
  dsrHistory: {},
  dsrBalances: {
    currentDSR: Zero,
    balances: {}
  },
  makerDAOVaults: [],
  makerDAOVaultDetails: [],
  aaveBalances: {},
  aaveHistory: {}
});

export const state: DefiState = defaultState();
