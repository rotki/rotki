import { default as BigNumber } from 'bignumber.js';
import { MakerDAOVault, MakerDAOVaultDetails } from '@/services/types-model';

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetails);

export interface MakerDAOVaultSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}
