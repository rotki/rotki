import { UniswapBalances } from '@/services/defi/types/uniswap';
import { DexTrades, UniswapEvents } from '@/store/defi/types';

export interface SushiswapState {
  readonly balances: UniswapBalances;
  readonly events: UniswapEvents;
  readonly trades: DexTrades;
}
