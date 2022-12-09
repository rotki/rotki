import { type Balance, type BigNumber, type HasBalance } from '@rotki/common';
import { type DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  type AaveBorrowingRates,
  type AaveHistoryEvents,
  type AaveHistoryTotal
} from '@rotki/common/lib/defi/aave';
import { type Collateral, type CollateralizedLoan } from '@/types/defi';
import { type CompoundEventType } from '@/types/defi/compound';
import { type EventType } from '@/types/defi/event-type';
import { type MakerDAOLendingHistoryExtras } from '@/types/defi/maker';
import { type YearnEventType } from '@/types/defi/yearn';

export interface LoanSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}

export interface AaveLoan
  extends AaveBorrowingRates,
    CollateralizedLoan<Collateral<string>[]> {
  readonly events: AaveHistoryEvents[];
  readonly totalLost: AaveHistoryTotal;
  readonly liquidationEarned: AaveHistoryTotal;
}

export interface DefiBalance extends BaseDefiBalance {
  readonly address: string;
  readonly protocol: DefiProtocol;
}

export interface BaseDefiBalance extends HasBalance {
  readonly effectiveInterestRate: string;
  readonly asset: string;
}

interface HistoryExtras<T> {
  readonly eventType: T;
  readonly asset: string;
  readonly value: Balance;
  readonly toAsset?: string;
  readonly toValue: Balance;
  readonly realizedPnl?: Balance;
}

interface LendingHistoryExtras {
  readonly [DefiProtocol.AAVE]: {};
  readonly [DefiProtocol.MAKERDAO_VAULTS]: {};
  readonly [DefiProtocol.MAKERDAO_DSR]: MakerDAOLendingHistoryExtras;
  readonly [DefiProtocol.COMPOUND]: HistoryExtras<CompoundEventType>;
  readonly [DefiProtocol.YEARN_VAULTS]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.YEARN_VAULTS_V2]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.UNISWAP]: {};
  readonly [DefiProtocol.LIQUITY]: {};
}

export interface DefiLendingHistory<T extends DefiProtocol> {
  id: string;
  eventType: EventType;
  protocol: T;
  address: string;
  asset: string;
  atoken?: string;
  value: Balance;
  extras: LendingHistoryExtras[T];
  blockNumber: number;
  timestamp: number;
  txHash: string;
}
