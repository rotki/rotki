import { Trade } from '@/services/trades/types';
import { Status } from '@/store/const';

export interface TradesState {
  status: Status;
  trades: Trade[];
}
