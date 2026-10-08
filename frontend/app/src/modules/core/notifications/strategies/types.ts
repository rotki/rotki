import type { Notification, NotificationData } from '@rotki/common';

export interface NotificationStrategyContext {
  readonly notifications: NotificationData[];
  readonly getNextId: () => number;
}

interface NotificationStrategyResult {
  readonly notifications: NotificationData[];
}

export interface NotificationStrategy {
  /**
   * Attempt to handle the incoming notification.
   * Return a result to commit and stop the chain, or `undefined` to pass through.
   */
  process: (
    payload: Notification,
    context: NotificationStrategyContext,
  ) => NotificationStrategyResult | undefined;
}
