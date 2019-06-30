import { ActionTree } from 'vuex';
import { NotificationState } from '@/store/notifications/state';
import { RotkehlchenState } from '@/store';
import { service } from '@/services/rotkehlchen_service';
import { NotificationData, Severity } from '@/typing/types';
import { BalanceState } from '@/store/balances/state';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  consume({ commit, getters }): any {}
};
