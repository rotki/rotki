import { type Trade, TradeType } from '@/types/history/trade';
import { bigNumberify } from '@rotki/common';
import dayjs from 'dayjs';

export function createNewTrade(): Trade {
  return {
    amount: bigNumberify(''),
    baseAsset: '',
    fee: null,
    feeCurrency: null,
    link: '',
    location: 'external',
    notes: '',
    quoteAsset: '',
    rate: bigNumberify(''),
    timestamp: dayjs().unix(),
    tradeId: '',
    tradeType: TradeType.BUY,
  };
}
