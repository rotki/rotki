import type { AaveBorrowingRates, AaveHistoryTotal, Balance, BigNumber } from '@rotki/common';
import type { Collateral, CollateralizedLoan } from '@/types/defi/index';
import type { DefiProtocol } from '@/types/modules';

export interface LoanSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}

export interface AaveLoan extends AaveBorrowingRates, CollateralizedLoan<Collateral[]> {
  readonly totalLost: AaveHistoryTotal;
  readonly liquidationEarned: AaveHistoryTotal;
}

export interface DefiBalance extends BaseDefiBalance {
  readonly address: string;
  readonly protocol: DefiProtocol;
}

export interface BaseDefiBalance extends Balance {
  readonly effectiveInterestRate: string;
  readonly asset: string;
}
