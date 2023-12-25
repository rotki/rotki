import { type BigNumber, type HasBalance } from '@rotki/common';
import {
  type AaveBorrowingRates,
  type AaveHistoryTotal
} from '@rotki/common/lib/defi/aave';
import { type Collateral, type CollateralizedLoan } from '@/types/defi';
import { type Module } from '@/types/modules';

export interface LoanSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}

export interface AaveLoan
  extends AaveBorrowingRates,
    CollateralizedLoan<Collateral[]> {
  readonly totalLost: AaveHistoryTotal;
  readonly liquidationEarned: AaveHistoryTotal;
}

export interface DefiBalance extends BaseDefiBalance {
  readonly address: string;
  readonly protocol: Module;
}

export interface BaseDefiBalance extends HasBalance {
  readonly effectiveInterestRate: string;
  readonly asset: string;
}
