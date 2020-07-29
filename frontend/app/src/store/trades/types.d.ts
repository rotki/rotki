import { default as BigNumber } from 'bignumber.js';
import { TradeType } from '@/services/types-common';
import { Status } from '@/store/trades/status';

export interface TradesState {
  status: Status;
  allTrades: Trade[];
  externalTrades: Trade[];
}

export interface Trade {
  readonly tradeId: string;
  readonly timestamp: number;
  readonly location: string;
  readonly pair: string;
  readonly tradeType: TradeType;
  readonly amount: BigNumber;
  readonly rate: BigNumber;
  readonly fee: BigNumber;
  readonly feeCurrency: string;
  readonly link: string;
  readonly notes: string;
}
