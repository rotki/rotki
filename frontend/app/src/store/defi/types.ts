import { Balance, BigNumber } from '@rotki/common';
import { HasBalance } from '@rotki/common/lib';
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  AaveBorrowingRates,
  AaveHistoryEvents,
  AaveHistoryTotal
} from '@rotki/common/lib/defi/aave';
import { Collateral, CollateralizedLoan, DefiBalanceType } from '@/types/defi';
import { CompoundEventType } from '@/types/defi/compound';
import { EventType } from '@/types/defi/event-type';
import { MakerDAOLendingHistoryExtras } from '@/types/defi/maker';
import { OverviewDefiProtocol } from '@/types/defi/protocols';
import { YearnEventType } from '@/types/defi/yearn';

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

type LendingHistoryExtras = {
  readonly [DefiProtocol.AAVE]: {};
  readonly [DefiProtocol.MAKERDAO_VAULTS]: {};
  readonly [DefiProtocol.MAKERDAO_DSR]: MakerDAOLendingHistoryExtras;
  readonly [DefiProtocol.COMPOUND]: HistoryExtras<CompoundEventType>;
  readonly [DefiProtocol.YEARN_VAULTS]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.YEARN_VAULTS_V2]: HistoryExtras<YearnEventType>;
  readonly [DefiProtocol.UNISWAP]: {};
  readonly [DefiProtocol.LIQUITY]: {};
};

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

interface DefiProtocolInfo {
  readonly name: OverviewDefiProtocol;
}

interface DefiProtocolInfoWithIcon extends DefiProtocolInfo {
  readonly icon: string;
}

export interface TokenInfo {
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

export interface DefiProtocolSummary {
  readonly protocol: DefiProtocolInfoWithIcon;
  readonly balanceUsd?: BigNumber;
  readonly assets: DefiAsset[];
  readonly tokenInfo: TokenInfo | null;
  readonly deposits: boolean;
  readonly liabilities: boolean;
  readonly depositsUrl?: string;
  readonly liabilitiesUrl?: string;
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebtUsd: BigNumber;
  readonly totalLendingDepositUsd: BigNumber;
}

export interface DefiAsset extends HasBalance {
  readonly tokenAddress: string;
  readonly tokenName: string;
  readonly tokenSymbol: string;
}

interface DefiProtocolData {
  readonly protocol: DefiProtocolInfo;
  readonly balanceType: DefiBalanceType;
  readonly baseBalance: DefiAsset;
  readonly underlyingBalances: DefiAsset[];
}

export interface AllDefiProtocols {
  readonly [asset: string]: DefiProtocolData[];
}
