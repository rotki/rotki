import { ApiTrade } from '@/services/types-api';
import { Trade } from '@/store/trades/types';
import { bigNumberify } from '@/utils/bignumbers';

export function convertTrades(trades: ApiTrade[]): Trade[] {
  const data: Trade[] = [];
  trades.map(trade => {
    data.push(convertTrade(trade));
  });
  return data;
}

export function convertTrade(trade: ApiTrade): Trade {
  return {
    tradeId: trade.trade_id as string,
    timestamp: trade.timestamp,
    location: trade.location,
    pair: trade.pair,
    tradeType: trade.trade_type,
    amount: bigNumberify(trade.amount),
    rate: bigNumberify(trade.rate),
    fee: bigNumberify(trade.fee),
    feeCurrency: trade.fee_currency,
    link: trade.link,
    notes: trade.notes
  };
}
