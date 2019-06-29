import { NotificationData } from '@/typing/types';

export const state: NotificationState = {
  data: []
};

export interface NotificationState {
  data: NotificationData[];
}
