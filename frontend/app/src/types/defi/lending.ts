import type { Balance, BigNumber } from '@rotki/common';
import type {
  AaveBorrowingRates,
  AaveHistoryTotal,
} from '@rotki/common/lib/defi/aave';
import type { Collateral, CollateralizedLoan } from '@/types/defi';
import type { DefiProtocol } from '@/types/modules';

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
  readonly protocol: DefiProtocol;
}

export interface BaseDefiBalance extends Balance {
  readonly effectiveInterestRate: string;
  readonly asset: string;
}
