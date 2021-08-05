import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { DexTrades } from '@/store/defi/types';

export interface SushiswapState {
  readonly balances: XswapBalances;
  readonly events: XswapEvents;
  readonly trades: DexTrades;
}
