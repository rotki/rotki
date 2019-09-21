import { NotificationData } from '@/typing/types';

export interface NotificationState {
  data: NotificationData[];
}

export const defaultState = (): NotificationState => ({
  data: []
});

export const state: NotificationState = defaultState();
