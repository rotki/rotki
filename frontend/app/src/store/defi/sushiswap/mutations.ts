import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { MutationTree } from 'vuex';
import { defaultState } from '@/store/defi/state';
import { SushiswapMutations } from '@/store/defi/sushiswap/mutation-types';
import { SushiswapState } from '@/store/defi/sushiswap/types';
import { DexTrades } from '@/store/defi/types';
import { Writeable } from '@/types';

export const mutations: MutationTree<SushiswapState> = {
  [SushiswapMutations.SET_BALANCES](
    state: Writeable<SushiswapState>,
    balances: XswapBalances
  ) {
    state.balances = balances;
  },
  [SushiswapMutations.SET_TRADES](
    state: Writeable<SushiswapState>,
    trades: DexTrades
  ) {
    state.trades = trades;
  },
  [SushiswapMutations.SET_EVENTS](
    state: Writeable<SushiswapState>,
    events: XswapEvents
  ) {
    state.events = events;
  },
  [SushiswapMutations.RESET](state: Writeable<SushiswapState>) {
    Object.assign(state, defaultState());
  }
};
